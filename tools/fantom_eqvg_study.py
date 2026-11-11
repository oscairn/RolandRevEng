"""Fantom EqVg/control correspondence with bounded, memory-isolated Thumb execution."""
import hashlib
import math
import struct

from core1_wait_study import IMAGE_SHA256
from eqfa_study import PI,CLAMP_FACTOR
from line_shaping_study import _finite,_float32

RATE=48000
ACTIVE_TYPES=(9,13,14,16)
GENERATE,STABLE,LIVE,OUTPUT=0x610732e0,0x6107332e,0x0112b7ac,0x0112b580
MANAGER,DRIVER,WAIT,IRQ=0x011350cc,0x0113047c,0x0113061c,0x0112f438
INTERPOLATE=0x01132bd2
FLAGS,GATES=0x200847f8,0x2008480c
SCRATCH,STACK,RETURN=0x21000000,0x2101f000,0x30000000


def checked_args(kind,cutoff,gain,q):
    if type(kind)is not int or not 0<=kind<=16:raise ValueError('Expected EqType0..16')
    cutoff,gain,q=map(_finite,(cutoff,gain,q))
    if (cutoff<0 or(cutoff and cutoff/RATE<float.fromhex('0x1p-1022'))or abs(gain)>96
            or(kind in ACTIVE_TYPES and cutoff>=RATE*.5*CLAMP_FACTOR)):
        raise ValueError('Outside checked Fantom math domain; assertion paths excluded')
    return cutoff,gain,min(max(q,.25),128.)


def coefficients(kind,cutoff,gain=0.,q=1.):
    """Independent scalar reference: double operations, then five binary32 stores."""
    cutoff,gain,q=checked_args(kind,cutoff,gain,q)
    if kind not in ACTIVE_TYPES or cutoff==0:return (0.,0.,1.,0.,0.)
    angle=(cutoff/RATE)*PI;s=math.sin(angle);c=math.cos(angle)
    linear=math.pow(10.,gain/20.)if kind in (9,16)else 1.
    if kind in (9,16):
        if kind==9 and gain<0:q=linear*q
        q=((angle*q)*c)/s
    root=math.sqrt((s*c)/q+1.)
    g=(s*2.)/root;b=-c/(q*root)
    if kind==13:raw=(g,b,1.,((g*.25)*g)-((g*.5)*b+1.),b*.5)
    elif kind==14:raw=(g,b,0.,((g*.5)*b+1.)-((g*.25)*g),0.)
    elif kind==9:raw=(g,b,1.,0.,((linear-1.)*b)*-.5)
    else:raw=(g,b,0.,0.,(linear*b)*-.5)
    return tuple(map(_float32,raw))


def stored_coefficients(raw,subtract_one=True):
    if not isinstance(raw,(list,tuple))or len(raw)!=5 or type(subtract_one)is not bool:
        raise ValueError('Expected five coefficients and an explicit offset flag')
    g,b,c,d,e=map(_float32,raw)
    return (_float32(g-1.)if subtract_one else g,b,c,d,e)


def interpolation_stable(old_g,old_b,new_g,new_b):
    g0,b0,g1,b1=(abs(_float32(v))for v in (old_g,old_b,new_g,new_b))
    delta=_float32(g1-g0);change=_float32(b0-b1)
    if delta==0 or change==0:return True
    slope=_float32(change/delta);den=_float32(_float32(slope*2.)-1.)
    negative_c=_float32(-b0-_float32(slope*g0))
    if den==0:return True
    vertex=_float32(-negative_c/den)
    square=_float32(negative_c*negative_c);quotient=_float32(square/den)
    outside=_float32(_float32(vertex-g0)*_float32(vertex-g1))
    margin=_float32(4.-quotient)
    return outside>=0 or margin>0


def update_plan(current,raw,*,envelope=True,subtract_one=True,output=False):
    if any(type(v)is not bool for v in (envelope,subtract_one,output)):
        raise ValueError('Expected explicit update/offset/path booleans')
    if not isinstance(current,(list,tuple))or len(current)!=2:raise ValueError('Expected current a/b')
    a0,b0=map(_float32,current);g,b,c,d,e=map(_float32,raw)
    safe=interpolation_stable(_float32(a0+(1. if subtract_one else 0.)),b0,g,b)if envelope else True
    order=(1,0,2,4,3)if envelope and abs(b0)>abs(b)else(0,1,2,4,3)
    values=stored_coefficients((g,b,c,d,e),subtract_one)
    if output and envelope:
        groups=[order[:1],order[1:]]if not safe else[order]
        return [dict(manager_slot=0x7c,coefficients=list(group),values=[values[i]for i in group],
            count=len(group),amount=100)for group in groups]
    return [dict(manager_slot=0x64 if output else 0xb8 if envelope else 0xc0,
        coefficient=i,value=values[i],selector=10 if envelope else None,
        wait=not output and envelope and not safe and n==0)for n,i in enumerate(order)]


def literal_operations(current,targets,amount):
    if (not isinstance(current,(list,tuple))or not isinstance(targets,(list,tuple))
            or len(current)!=len(targets)or len(current)>127 or type(amount)is not int
            or not -256<=amount<=256):raise ValueError('Expected equal lists0..127 and amount within +/-256')
    current=list(map(_float32,current));targets=list(map(_float32,targets))
    delta=[_float32(b-a)for a,b in zip(current,targets,strict=True)]
    result=[];steps=max(abs(amount),1)
    for k in range(1,steps):
        ratio=_float32(_float32(k)/_float32(steps))
        result.extend(('write',i,_float32(a+_float32(d*ratio)))for i,(a,d)in enumerate(zip(current,delta,strict=True))if d)
        result.append(('wait',1,True))
    result.extend(('write',i,v)for i,v in enumerate(targets))
    return result


def control_request(flags,target,selector=10,wait=True,event_ref=2):
    if (type(flags)is not int or not 0<=flags<=0xffffffff or type(selector)is not int or not 0<=selector<16
            or type(wait)is not bool or type(event_ref)is not int or not 0<=event_ref<=8):
        raise ValueError('Invalid CORE1 control fields')
    return dict(flags=flags&~2 if wait else flags,
        control=(event_ref<<28)|(int(wait)<<24)|(selector<<20)|0x08000000,target=_float32(target))


def report(core):
    from dramio_owner_study import expect
    from kernel_abi import read
    if hashlib.sha256(core.data).hexdigest()!=IMAGE_SHA256:raise ValueError('Expected pinned Fantom CORE1 payload')
    for pc,mnemonic,operand in (
        (GENERATE,'cmp','r0, #9'),(0x610732e4,'cmp','r0, #0xd'),(0x610732e8,'cmp','r0, #0xe'),
        (0x610732ec,'cmp','r0, #0x10'),(0x0112b80a,'bl','#0x1134ec0'),
        (0x01134ec0,'movw','ip, #0x32e1'),(0x01134ec4,'movt','ip, #0x6107'),
        (0x6107336a,'vnmls.f32','s1, s3, s5'),(0x6107336e,'vmls.f32','s0, s3, s4'),
        (0x0112b858,'bl','#0x1134eb6'),(0x011304e4,'bic','r5, r5, #2'),
        (0x011304e8,'str','r5, [r4, #8]'),(0x01130504,'str','r1, [r0, #8]'),
        (0x01133980,'ldrb','r0, [r5, #3]'),(0x01133990,'strb','r0, [r5, #3]'),
        (0x011339bc,'bl','#0x113061c'),(0x011339c2,'strb','r0, [r5, #3]'),
        (0x61049ed0,'eor','r3, r0, #1'),(0x6104a1a4,'movs','r3, #0'),
        (0x01132cea,'vmla.f32','s16, s0, s17')):
        expect(core,pc,mnemonic,operand)
    constants={a:struct.unpack('<d',read(core,a,8))[0]for a in (0x61070958,0x61070960,0x61073160,0x61073170,0x61073190)}
    if tuple(constants.values())!=(48000.,PI,48000*.5*CLAMP_FACTOR,.25,128.):raise ValueError('Fantom EqVg constants changed')
    descriptors=[]
    for address,slots in ((0x610e5c1c,(10,11,12,14,13)),(0x610e5c34,(15,16,17,19,18))):
        if read(core,address,1)!=b'\x01':raise ValueError('Fantom g-1 descriptor flag changed')
        pointers=struct.unpack('<5I',read(core,address+4,20))
        if tuple(core.u32(p+12)for p in pointers)!=slots:raise ValueError('Fantom live order changed')
        descriptors.append(dict(address=address,raw_field_slots=slots))
    output=[]
    manager_slots={0x64:0x011327e7,0x70:0x01132abf,0x7c:0x01132bd3,
        0xb8:0x011350cd,0xbc:0x0113391f,0xc0:0x01135133,0xc8:0x0113509f}
    if any(core.u32(0x6117647c+slot)!=target for slot,target in manager_slots.items()):
        raise ValueError('Fantom manager vtable changed')
    for index,pointer in enumerate(struct.unpack('<5I',read(core,0x610e5c50,20))):
        table=core.u32(pointer+8);count=read(core,pointer+12,1)[0]
        if count not in (2,4):raise ValueError('Unexpected output group count')
        records=[dict(absolute=a,relative=r,width=w)for a,r,w in struct.iter_unpack('<III',read(core,table,12*count))]
        if any(r['width']!=3 for r in records):raise ValueError('Output literal width changed')
        output.append(dict(raw_field=index,symbol=pointer,records=records))
    if [[r['relative']for r in row['records']]for row in output]!=[
        [0x4ea,0x4ed,0x536,0x539],[0x506,0x509],[0x526,0x529],[0x512,0x515],[0x558,0x55b]]:
        raise ValueError('Output raw-field correspondence changed')
    return dict(payload_sha256=IMAGE_SHA256,generator=GENERATE,active_types=ACTIVE_TYPES,
        unsupported_type_fallback=[0.,0.,1.,0.,0.],fixed_rate=RATE,q_clamp=[.25,128.],
        live_descriptors=descriptors,output_groups=output,constants=constants,
        manager_slots=manager_slots,
        stability_precision='binary32 VFP non-fused multiply/subtract',
        generator_precision='original software binary64 arithmetic and transcendentals; five binary32 stores',
        envelope_flag=FLAGS,envelope_owner_gate=GATES+3,literal_owner_gate=GATES,
        real_caller_exclusion_proved=False,hardware_execution_verified=False)


class ThumbOracle:
    """Only fixed selected entries; code is data to Unicorn, with no host/device pointers."""
    ENTRIES=(GENERATE,STABLE,LIVE,OUTPUT,MANAGER,DRIVER,WAIT,IRQ,INTERPOLATE)
    def __init__(self,core):
        self.core=core;self.checked=report(core)
        import unicorn as uc
        from unicorn import arm_const as arm
        from core1_wait_study import expand_initial_data
        if uc.__version__!='2.1.4':raise ValueError('Use pinned Unicorn2.1.4 for these checks')
        self.uc=uc;self.arm=arm;self.cpu=uc.Uc(uc.UC_ARCH_ARM,uc.UC_MODE_THUMB|uc.UC_MODE_MCLASS)
        u=self.cpu;u.ctl_set_cpu_model(arm.UC_CPU_ARM_CORTEX_M7)
        for base,data in ((0x01100000,core.data[:core.eram_offset]),(0x61000000,core.data[core.eram_offset:])):
            u.mem_map(base,(len(data)+4095)&~4095,uc.UC_PROT_READ|uc.UC_PROT_EXEC);u.mem_write(base,data)
        ram_permissions=uc.UC_PROT_READ|uc.UC_PROT_WRITE
        u.mem_map(0x20080000,0x30000,ram_permissions);u.mem_map(SCRATCH,0x20000,ram_permissions)
        u.mem_map(0x414a0000,0x8000,ram_permissions)
        for record in core.scatter():
            if record['destination']==0x2008008c:
                data,_=expand_initial_data(core.data[core.offset(record['source']):],record['length'])
                u.mem_write(record['destination'],data)
        u.mem_map(RETURN,0x1000,uc.UC_PROT_READ|uc.UC_PROT_EXEC)
        for slot in (0x64,0x70,0x7c,0xb8,0xc0,0xc8):u.mem_write(RETURN+0x100+slot,bytes.fromhex('7047'))
        u.reg_write(arm.UC_ARM_REG_C1_C0_2,0x00f00000);u.reg_write(arm.UC_ARM_REG_FPEXC,0x40000000)
        self.base_context=u.context_save();self.failure=None
        self.mode=None;self.calls=[];self.writes=[];self.instructions=0;self.complete=False;self.polls=0
        u.hook_add(uc.UC_HOOK_CODE,self._code);u.hook_add(uc.UC_HOOK_MEM_WRITE,self._write)
        u.hook_add(uc.UC_HOOK_MEM_INVALID,self._invalid)

    def _invalid(self,u,access,address,size,value,_):
        self.failure=f'Unmapped/protected emulated access {address:#x} at PC {u.reg_read(self.arm.UC_ARM_REG_PC):#x}'
        return False

    def _write(self,u,access,address,size,value,_):
        if not any(start<=address and address+size<=end for start,end in
            ((0x20080000,0x200b0000),(SCRATCH,SCRATCH+0x20000),(0x414a0000,0x414a8000))):
            raise ValueError(f'Write outside isolated emulated memory: {address:#x}')
        self.writes.append((self.pc,address,size,value))

    def _f(self,index):return struct.unpack('<f',struct.pack('<I',self.cpu.reg_read(self.arm.UC_ARM_REG_S0+index)))[0]

    def _word(self,address):return struct.unpack('<I',self.cpu.mem_read(address,4))[0]

    def _code(self,u,address,size,_):
        self.pc=address
        self.instructions+=1
        if address in (0x610018a6,0x01134ef2):raise ValueError('Excluded firmware assertion reached')
        if address==0x01130620 and self.mode=='manager':
            self.polls+=1
            if self.polls>=3 and not self._word(FLAGS)&2:u.emu_stop();return
        if self.mode=='interpolation'and address in (0x0112ff4e,0x011271b8):
            r1=u.reg_read(self.arm.UC_ARM_REG_R1);r2=u.reg_read(self.arm.UC_ARM_REG_R2)
            if address==0x011271b8:
                if (r1,r2)!=(1,1):raise ValueError('Unexpected sample-wait request')
                self.calls.append(('wait',r1,bool(r2)))
            else:
                if r1 not in self.literal_fields or r2!=3:raise ValueError('Unexpected virtual literal field')
                index,relative=self.literal_fields[r1];value=self._f(0)
                self.calls.append(('write',index,relative,r2,value));self.literal_current[index]=value
            u.reg_write(self.arm.UC_ARM_REG_PC,u.reg_read(self.arm.UC_ARM_REG_LR));return
        if RETURN+0x100<=address<RETURN+0x200:
            slot=address-RETURN-0x100;r1=u.reg_read(self.arm.UC_ARM_REG_R1)
            if slot in (0x70,0xc8):
                if self.mode=='interpolation':
                    if r1 not in self.literal_symbols:raise ValueError('Unexpected literal read symbol')
                    value=self.literal_current[self.literal_symbols[r1]]
                else:
                    if r1 not in (1,2):raise ValueError('Unexpected recorded current-value symbol')
                    value=self.current[r1-1]
                u.reg_write(self.arm.UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',value))[0])
            elif slot==0x7c:
                r2=u.reg_read(self.arm.UC_ARM_REG_R2);count=u.reg_read(self.arm.UC_ARM_REG_R3)
                if count not in (1,4,5):raise ValueError('Unexpected output batch size')
                indices=[self._word(r1+4*i)-1 for i in range(count)]
                values=list(struct.unpack('<'+'f'*count,u.mem_read(r2,4*count)))
                self.calls.append(dict(manager_slot=slot,coefficients=indices,values=values,count=count,
                    amount=self._word(u.reg_read(self.arm.UC_ARM_REG_SP))))
            elif slot in (0x64,0xb8,0xc0):
                if not 1<=r1<=5:raise ValueError('Unexpected coefficient symbol')
                self.calls.append(dict(manager_slot=slot,coefficient=r1-1,value=self._f(0),
                    selector=u.reg_read(self.arm.UC_ARM_REG_R2)if slot==0xb8 else None,
                    wait=bool(u.reg_read(self.arm.UC_ARM_REG_R3))if slot==0xb8 else False))
            else:raise ValueError('Unexpected emulated callback slot')

    def _run(self,entry,*,registers=(),singles=(),doubles=(),stack=b'',mode=None,pending=False):
        if entry not in self.ENTRIES:
            raise ValueError('Unadmitted firmware entry')
        u=self.cpu;a=self.arm;self.mode=mode;self.polls=0;self.instructions=0;self.calls=[];self.writes=[]
        u.context_restore(self.base_context);self.failure=None
        # Clear translated state: repeat calls otherwise fail near Thumb IT blocks here.
        u.ctl_flush_tb()
        u.reg_write(a.UC_ARM_REG_SP,STACK);u.reg_write(a.UC_ARM_REG_LR,RETURN|1);u.reg_write(a.UC_ARM_REG_FPSCR,0)
        for i,value in enumerate(registers):u.reg_write(a.UC_ARM_REG_R0+i,value)
        for i,value in enumerate(singles):u.reg_write(a.UC_ARM_REG_S0+i,struct.unpack('<I',struct.pack('<f',value))[0])
        for i,value in enumerate(doubles):u.reg_write(a.UC_ARM_REG_D0+i,struct.unpack('<Q',struct.pack('<d',value))[0])
        if stack:u.mem_write(STACK,stack)
        try:u.emu_start(entry|1,RETURN,count=250000)
        except self.uc.UcError as error:
            raise ValueError(self.failure or f'CPU emulation failed at {u.reg_read(a.UC_ARM_REG_PC):#x}: {error}')from error
        returned=u.reg_read(a.UC_ARM_REG_PC)==RETURN
        if not returned and not(pending and u.reg_read(a.UC_ARM_REG_PC)==0x01130620):
            raise ValueError(f'Selected Thumb entry did not return: {u.reg_read(a.UC_ARM_REG_PC):#x}')
        return returned

    def generate(self,kind,cutoff,gain=0.,q=1.):
        checked_args(kind,cutoff,gain,q)
        self._run(GENERATE,registers=(kind,SCRATCH),doubles=(cutoff,gain,q))
        return struct.unpack('<5f',self.cpu.mem_read(SCRATCH,20))

    def stable(self,*values):
        if len(values)!=4:raise ValueError('Expected four stability inputs')
        values=tuple(map(_float32,values))
        interpolation_stable(*values)
        self._run(STABLE,singles=values)
        return bool(self.cpu.reg_read(self.arm.UC_ARM_REG_R0))

    def setter(self,kind,cutoff,gain=0.,q=1.,*,current=(0.,0.),envelope=True,output=False,subtract_one=True):
        cutoff,gain,q=map(_float32,(cutoff,gain,q));checked_args(kind,cutoff,gain,q)
        if any(type(v)is not bool for v in (envelope,output,subtract_one))or len(current)!=2:
            raise ValueError('Invalid setter fixture arguments')
        self.current=tuple(map(_float32,current));u=self.cpu
        descriptor,manager,table=SCRATCH+0x100,SCRATCH+0x200,SCRATCH+0x400
        u.mem_write(SCRATCH,struct.pack('<I',descriptor))
        u.mem_write(descriptor,struct.pack('<6I',int(subtract_one),1,2,3,4,5))
        u.mem_write(manager,struct.pack('<I',table))
        for slot in (0x64,0x70,0x7c,0xb8,0xc0,0xc8):
            u.mem_write(table+slot,struct.pack('<I',RETURN+0x100+slot+1))
        self._run(OUTPUT if output else LIVE,registers=(SCRATCH,manager,kind,int(envelope)),singles=(cutoff,gain,q))
        return self.calls.copy()

    def interpolate(self,current,targets,amount,indices=(0,1,2,3,4)):
        if (not isinstance(current,(list,tuple))or len(current)!=5 or not isinstance(indices,(list,tuple))
                or any(type(i)is not int or not 0<=i<5 for i in indices)or len(set(indices))!=len(indices)):
            raise ValueError('Expected five baseline values and distinct raw output-field indices')
        literal_operations([current[i]for i in indices],targets,amount)
        # shortcut: negative-amount Thumb execution faults here; admit it after the fixture/engine cause is resolved.
        if amount<0:raise ValueError('Negative amount modeled statically only: unresolved Unicorn IT-path fault')
        self.literal_current=list(map(_float32,current));self.literal_symbols={};self.literal_fields={}
        groups=self.checked['output_groups']
        for i,group in enumerate(groups):
            self.literal_symbols[group['symbol']]=i
            for record in group['records']:self.literal_fields[record['absolute']]=(i,record['relative'])
        u=self.cpu;manager,table,context,outer=SCRATCH+0x200,SCRATCH+0x400,SCRATCH+0x600,SCRATCH+0x800
        symbols,values=SCRATCH+0xa00,SCRATCH+0xb00
        u.mem_write(manager,struct.pack('<3I',table,outer,context));u.mem_write(context,bytes(0x48))
        u.mem_write(outer+4,struct.pack('<I',SCRATCH+0xc00))
        u.mem_write(table+0x70,struct.pack('<I',RETURN+0x170+1))
        if indices:u.mem_write(symbols,struct.pack('<'+'I'*len(indices),*(groups[i]['symbol']for i in indices)))
        if targets:u.mem_write(values,struct.pack('<'+'f'*len(targets),*targets))
        u.mem_write(GATES,b'\0')
        self._run(INTERPOLATE,registers=(manager,symbols,values,len(indices)),stack=struct.pack('<i',amount),mode='interpolation')
        if u.mem_read(GATES,1)!=b'\0':raise ValueError('Program ownership marker not released')
        return dict(operations=self.calls.copy(),current=self.literal_current.copy(),
            ownership_marker_values=[value for pc,address,size,value in self.writes if address==GATES])

    def manager_write(self,flags,target,selector=10,wait=True,*,complete=True):
        expected=control_request(flags,target,selector,wait)
        if type(complete)is not bool:raise ValueError('Expected explicit synthetic completion boolean')
        u=self.cpu;manager,table,context,segment=SCRATCH+0x200,SCRATCH+0x400,SCRATCH+0x600,SCRATCH+0x800
        u.mem_write(manager,struct.pack('<3I',table,0,context));u.mem_write(context,bytes(0x48))
        u.mem_write(context+0x18,struct.pack('<IB',segment,1));u.mem_write(segment,struct.pack('<II',0,2048))
        u.mem_write(table+0xbc,struct.pack('<I',0x0113391f))
        u.mem_write(FLAGS,struct.pack('<I',flags));u.mem_write(GATES+3,b'\0')
        returned=self._run(MANAGER,registers=(manager,0x610e5d64,selector,int(wait)),
            singles=(expected['target'],),mode='manager',pending=True)
        writes=self.writes.copy();polls=self.polls
        if not returned and complete:
            caller=u.context_save()
            self._run(IRQ)
            writes.extend(self.writes);u.context_restore(caller)
            self.mode='manager';self.polls=0;self.writes=[]
            u.emu_start(u.reg_read(self.arm.UC_ARM_REG_PC)|1,RETURN,count=250000)
            returned=u.reg_read(self.arm.UC_ARM_REG_PC)==RETURN;writes.extend(self.writes)
            if not returned:raise ValueError('Synthetic completion did not release original wait')
        record=u.mem_read(0x414a0000+10*16,16)
        if wait:
            addresses=[address for pc,address,size,value in writes]
            if not addresses.index(FLAGS)<addresses.index(0x414a00a8)<addresses.index(0x414a00ac):
                raise ValueError('Completion clear/control/target write order changed')
        return dict(returned=returned,flags=self._word(FLAGS),control=struct.unpack_from('<I',record,8)[0],
            target=struct.unpack_from('<f',record,12)[0],owner_gate=u.mem_read(GATES+3,1)[0],
            poll_visits_before_delivery=polls,
            shared_flag_values=[value for pc,address,size,value in writes if address==FLAGS],
            owner_gate_values=[value for pc,address,size,value in writes if address==GATES+3])


def selfcheck(core):
    import random
    oracle=ThumbOracle(core);result=dict(oracle.checked);fields=0
    for kind in range(17):
        for cutoff in (0.,20.,1000.,19000.):
            for gain in (-12.,0.,9.):
                for q in (.1,.707,128.,256.):
                    actual=oracle.generate(kind,cutoff,gain,q);wanted=coefficients(kind,cutoff,gain,q)
                    if struct.pack('<5f',*actual)!=struct.pack('<5f',*wanted):
                        raise ValueError(f'Fantom coefficient mismatch: {kind,cutoff,gain,q}')
                    fields+=5
    rng=random.Random(0x7332)
    for _ in range(100):
        args=(rng.choice(ACTIVE_TYPES),rng.uniform(10.,23700.),rng.uniform(-24.,24.),rng.uniform(.1,160.))
        if struct.pack('<5f',*oracle.generate(*args))!=struct.pack('<5f',*coefficients(*args)):
            raise ValueError(f'Irregular coefficient mismatch: {args}')
    for _ in range(2000):
        values=[rng.uniform(-4.,4.)for _ in range(4)]
        if oracle.stable(*values)!=interpolation_stable(*values):raise ValueError('Fantom stability mismatch')
    setters=0
    for output in (False,True):
        for envelope in (False,True):
            for subtract_one in (False,True):
                for kind in (0,9,10,13,14,16):
                    current=stored_coefficients(coefficients(13,20,q=.25),subtract_one)[:2]
                    args=dict(current=current,envelope=envelope,output=output,subtract_one=subtract_one)
                    actual=oracle.setter(kind,19000.,q=128.,**args)
                    wanted=update_plan(current,coefficients(kind,19000.,q=128.),
                        envelope=envelope,output=output,subtract_one=subtract_one)
                    if actual!=wanted:raise ValueError('Fantom setter request mismatch')
                    setters+=1
    controls=0
    for flags in range(4):
        for selector in (0,10,15):
            for wait in (False,True):
                for complete in (False,True):
                    actual=oracle.manager_write(flags,.123,selector,wait,complete=complete)
                    wanted=control_request(flags,.123,selector,wait)
                    returned=not wait or complete
                    if (actual['returned']!=returned or actual['flags']!=wanted['flags']
                            or actual['control']!=wanted['control']or actual['target']!=wanted['target']
                            or actual['owner_gate']!=int(not returned)
                            or actual['owner_gate_values']!=([1,0]if wait and complete else[1]if wait else[])
                            or actual['shared_flag_values']!=(
                                [flags&~2,(flags&~2)|2,flags&~2]if wait and complete else[flags&~2]if wait else[])):
                        raise ValueError('Fantom completion protocol mismatch')
                    controls+=1
    literals=0;physical_writes=0;waits=0
    current=[.123,-0.,.25,-.456,.9];targets=[.9,-0.,-.25,.456,.1]
    for indices in ((),(1,),(0,2,4,3),(0,1,2,3,4)):
        for amount in (0,1,2,3,100):
            selected=[targets[i]for i in indices]
            actual=oracle.interpolate(current,selected,amount,indices);wanted=[]
            for op in literal_operations([current[i]for i in indices],selected,amount):
                if op[0]=='wait':wanted.append(op)
                else:
                    _,i,value=op;raw=indices[i]
                    wanted.extend(('write',raw,r['relative'],r['width'],value)
                        for r in oracle.checked['output_groups'][raw]['records'])
            def trace(operations):
                return [op[:-1]+(struct.pack('<f',op[-1]),)if op[0]=='write'else op for op in operations]
            if trace(actual['operations'])!=trace(wanted)or actual['ownership_marker_values']!=[1,0]:
                raise ValueError('Fantom literal interpolation trace mismatch')
            literals+=1;physical_writes+=sum(op[0]=='write'for op in wanted);waits+=sum(op[0]=='wait'for op in wanted)
    result.update(regular_coefficient_fields_compared=fields,irregular_coefficient_fields_compared=500,
        stability_cases_compared=2000,setter_cases_compared=setters,control_cases_compared=controls,
        literal_cases_compared=literals,literal_physical_writes_compared=physical_writes,
        literal_sample_wait_requests_compared=waits,negative_amount_execution_verified=False,
        irq_delivery='explicit original callback in private CPU context; hardware controller not run',
        literal_primitives='recording callbacks; codec and sample wait body not executed',
        os_or_firmware_startup_executed=False)
    return result


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--execute-thumb',action='store_true')
    args=parser.parse_args();core=Core1(args.image)
    print(json.dumps(selfcheck(core)if args.execute_thumb else report(core),indent=2))

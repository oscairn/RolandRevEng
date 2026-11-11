"""Owned native coefficient-manager/wait processing, without OS threads or hardware."""
from contextlib import contextmanager
import hashlib
import math
import struct

from eqfa_study import _adr
from fdrv_parameter_study import envelope_state,envelope_step
from line_shaping_study import NATIVE_SHA256,_finite,_float32

REGIONS={
    'literal':(0xfbd60,0xfbfcc),'resolve':(0xfc0ac,0xfc420),
    'manager_env':(0xfcbb4,0xfcce0),'core_env':(0x16c468,0x16c594),
    'core_immediate':(0x16c5b0,0x16c64c),'core_isr':(0x16c684,0x16c694),
    'core_wait':(0x16c694,0x16c6dc),'ctrl':(0x3460cc,0x3460e8),
    'env_isr':(0x34611c,0x3461c0),'env_sync':(0x3461c0,0x346254),
    'env_step':(0x3463d8,0x346518),'breakpoint':(0x346734,0x346a48),
    'send_sync4':(0x347174,0x3472e0),'wait_samples':(0x2a5938,0x2a59c8),
    'wait_step':(0x2a5bc4,0x2a5c30),'set_flag':(0x36454c,0x3645c8),
    'wait_flag':(0x3645d8,0x36465c),'current':(0x364800,0x36482c),
    'dispatch_isr':(0x1662c8,0x166308),
}
ACTIVE,ACTIVE_COUNT,PENDING,PENDING_COUNT=0x90438,0x90648,0x90a50,0x90c60
OWNERS=0x6c038


def literal_operations(current,targets,amount):
    """Ordered manager operations; a wait request does not imply elapsed audio time."""
    if (not isinstance(current,(list,tuple))or not isinstance(targets,(list,tuple))
            or len(current)!=len(targets)or len(current)>127
            or type(amount)is not int or not -4096<=amount<=4096):
        raise ValueError('Expected equal coefficient lists of length0..127 and amount within +/-4096')
    current=list(map(_finite,current));targets=list(map(_finite,targets))
    delta=[_finite(b-a)for a,b in zip(current,targets,strict=True)]
    steps=max(abs(amount),1);operations=[]
    for step in range(1,steps):
        ratio=step/steps
        operations.extend(('write',i,_finite(math.fma(d,ratio,a)))
            for i,(a,d)in enumerate(zip(current,delta,strict=True))if d!=0.)
        operations.append(('wait',1,True))
    operations.extend(('write',i,value)for i,value in enumerate(targets))
    return operations


class ManagerModel:
    """Independent scalar/event model for the admitted DSP4 fixture paths."""
    def __init__(self,initial,*,literal_initial=(),current=True,enabled=True,flag=3):
        _settings(initial,current,enabled,flag)
        self.states=[(v,0.,0,v)for v in map(_float32,initial)]
        self.active=set();self.pending=set();self.flag=flag;self.current=current;self.enabled=enabled
        self.clock=0;self.counter=0;self.signals=0;self.interrupts=[];self.waits=[]
        literal_operations(literal_initial,literal_initial,0)
        self.literals=list(map(_finite,literal_initial));self.operations=[]

    def set_flag(self):
        if self.flag==3:self.flag=4
        elif self.flag==5:self.flag=3;self.signals+=1

    def step(self):
        self.clock+=1
        for slot in sorted(self.active.copy()):
            state=self.states[slot];next_state=envelope_step(state)
            done=not state[1]or abs(_float32(state[3]-state[0]))<=abs(state[1])
            if done:
                self.active.remove(slot);self.pending.add(slot)
                if next_state[2]&0x01000000 and not next_state[2]&0x02000000:
                    next_state=(*next_state[:2],next_state[2]|0x02000000,next_state[3])
                    self.interrupts.append((self.clock,slot));self.set_flag()
            self.states[slot]=next_state
        if self.counter>0:
            self.counter-=1
            if self.counter==0:self.set_flag()

    def wait_flag(self):
        if self.flag==4:self.flag=3;return
        if self.flag!=3:return
        self.flag=5
        for _ in range(5000):
            self.step()
            if self.flag!=5:return
        raise ValueError('Owned wait model exceeded its progress budget')

    def wait_samples(self,count,wait=True):
        if type(count)is not int or not 0<=count<=4096 or type(wait)is not bool:
            raise ValueError('Expected sample count0..4096 and explicit wait boolean')
        self.waits.append((self.clock,count,wait))
        if not count or not self.enabled or not self.current:return
        self.counter=count+1
        if wait:self.wait_flag()

    def write_env(self,slot,target,selector=10,wait=False):
        _write_args(self.states,slot,target,selector,wait)
        old=self.states[slot]
        if wait and not self.current:
            value=_float32(target);self.states[slot]=(value,old[1],0,value)
            return
        value,increment,control,target=envelope_state(old[0],target,selector)
        control=(control&0x33ffffff)|0x84000000|(int(wait)<<24)
        self.states[slot]=(value,increment,control,target)
        self.active.add(slot);self.pending.discard(slot)
        if wait:self.wait_flag()

    def interpolate(self,indices,targets,amount):
        _indices(indices,len(self.literals))
        operations=literal_operations([self.literals[i]for i in indices],targets,amount)
        for op in operations:
            if op[0]=='write':op=(op[0],indices[op[1]],op[2])
            self.operations.append((self.clock,*op))
            if op[0]=='write':self.literals[op[1]]=op[2]
            else:self.wait_samples(op[1],op[2])

    def snapshot(self):
        return dict(states=self.states.copy(),active=sorted(self.active),pending=sorted(self.pending),
            flag=self.flag,clock=self.clock,counter=self.counter,signals=self.signals,
            interrupts=self.interrupts.copy(),waits=self.waits.copy(),literals=self.literals.copy(),
            operations=self.operations.copy())


def _settings(initial,current,enabled,flag):
    if not isinstance(initial,(list,tuple))or not 1<=len(initial)<=1024:
        raise ValueError('Expected1..1024 initial live values')
    tuple(map(_float32,initial))
    if type(current)is not bool or type(enabled)is not bool or type(flag)is not int or flag not in (3,4):
        raise ValueError('Expected explicit context/enabled booleans and task state3/4')


def _indices(indices,count):
    if (not isinstance(indices,(list,tuple))or any(type(i)is not int or not 0<=i<count for i in indices)
            or len(set(indices))!=len(indices)):
        raise ValueError('Expected distinct valid literal indices')


def _write_args(states,slot,target,selector,wait):
    if type(slot)is not int or not 0<=slot<len(states)or type(wait)is not bool:
        raise ValueError('Invalid live slot/wait argument')
    envelope_state(states[slot][0],target,selector)


def report():
    import lib
    from fdrv_parameter_study import imported_stub
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    exports=lib.load_exports()
    table=exports['vtable for CSimDspMgr']+16
    for slot,target in ((0xf8,0xfbd60),(0x178,0xfcbb4),(0x188,0xfcce0),(0x198,0xfcdc0)):
        if struct.unpack_from('<Q',lib.Z,table+slot)[0]!=target:raise ValueError('Manager virtual method changed')
    md=lib.md();instructions={i.address:i for a,b in REGIONS.values()for i in md.disasm(lib.Z[a:b],a)}
    for pc,shape in (
        (0xfbe38,(('cmp','w4, #0'),('cneg','w8, w4, mi'),('csinc','w20, w8, wzr, ne'))),
        (0xfbf14,(('ldr','d1, [x28]'),('fmadd','d0, d0, d9, d1'))),
        (0x2a598c,(('add','w8, w21, #1'),('str','w8, [x19, #8]'))),
        (0x2a5be4,(('ldr','w8, [x19, #8]'),('subs','w8, w8, #1'))),
        (0xfcc58,(('cbz','w19, #0xfcccc'),)),
        (0x16c4a4,(('tbnz','w0, #0, #0x16c4d8'),('cbz','w21, #0x16c4d8')))):
        require_instructions(instructions,pc,shape)
    imports={a:imported_stub(lib.Z,a)for a in (0x6d8e0c,0x6d8e24,0x6d8d58,0x6d8ea8)}
    if tuple(imports.values())!=('_pthread_mutex_lock','_pthread_mutex_unlock','_pthread_cond_signal','_pthread_self'):
        raise ValueError('Unexpected task primitive imports')
    return dict(native_sha256=NATIVE_SHA256,regions=REGIONS,manager_vtable=table,primitive_imports=imports,
        amount_policy='max(abs(signed amount),1); bounded research domain +/-4096',
        unit='interpolation update count; intermediate waits request one CDSPWait sample',
        literal_precision='binary64 manager values; physical literal conversion is not executed',
        primitive_boundary='controlled mutex/unique-lock helpers, condition-wait helper and thread identity',
        os_primitives_executed=False,hardware_timing_verified=False)


@contextmanager
def _owned_functions(callbacks):
    import lib
    from native_callback_fixture import executable_mapping
    report();blob=bytearray();offsets={}
    for name,(a,b)in REGIONS.items():
        blob.extend(bytes(-len(blob)%8));offsets[name]=len(blob);blob.extend(lib.Z[a:b])
    pages={}
    for page in (0x769000,0x839000):
        blob.extend(bytes(-len(blob)%16));pages[page]=len(blob);blob.extend(lib.Z[page:page+4096])
    blob.extend(bytes(-len(blob)%8));guard=len(blob);blob.extend(struct.pack('<Q',0x3141592653589793))
    destinations={a:offsets[n]for n,(a,b)in REGIONS.items()}
    for target,pointer in callbacks.items():
        destinations[target]=len(blob);blob.extend(struct.pack('<IIQ',0x58000050,0xd61f0200,pointer))
    trap=len(blob);blob.extend(struct.pack('<II',0xd4200000,0xd65f03c0))
    # Owners are fixed to DSP4; DSP2/3 interrupt dispatch and assertion paths are excluded.
    destinations.update({a:trap for a in (0xaa144,0x6d8710,0xd046c,0xd04a8)})
    md=lib.md();md.detail=True
    for name,(a,b)in REGIONS.items():
        instructions=list(md.disasm(lib.Z[a:b],a))
        if [i.address for i in instructions]!=list(range(a,b,4)):raise ValueError('Incomplete manager body')
        for index,ins in enumerate(instructions):
            offset=offsets[name]+ins.address-a
            if ins.mnemonic in ('b','bl'):
                target=ins.operands[0].imm
                if a<=target<b:continue
                if target not in destinations:raise ValueError(f'Unbound manager dependency {target:#x}')
                word=0x94000000 if ins.mnemonic=='bl'else 0x14000000
                blob[offset:offset+4]=struct.pack('<I',word|(((destinations[target]-offset)//4)&0x3ffffff))
            elif ins.mnemonic=='adrp':
                page=ins.operands[1].imm;register=int(ins.op_str.split(',')[0][1:])
                if page in pages:blob[offset:offset+4]=_adr(register,pages[page]-offset)
                elif page==0x9c8000:
                    if instructions[index+1].op_str!=f'x{register}, [x{register}, #0x480]':
                        raise ValueError('Unexpected manager stack guard')
                    blob[offset:offset+8]=_adr(register,guard-offset)+bytes.fromhex('1f2003d5')
                elif page not in (0x8b8000,0x8b2000):raise ValueError('Unexpected manager global dependency')
            elif ins.mnemonic.startswith('b.')or ins.mnemonic in ('cbz','cbnz','tbz','tbnz'):
                if not a<=ins.operands[-1].imm<b:raise ValueError('Conditional branch leaves owned manager body')
    with executable_mapping(bytes(blob))as address:
        yield {name:address+offset for name,offset in offsets.items()}


class _NativeManager:
    def __init__(self,initial,literal_initial,current,enabled,flag):
        import ctypes
        self.ctypes=ctypes;self.buffers=[];self.callbacks=[];self.errors=[];self.functions={}
        self.clock=0;self.signals=0;self.interrupts=[];self.waits=[];self.operations=[]
        self.literals=list(map(_finite,literal_initial));self.count=len(initial)
        def buffer(size):
            value=ctypes.create_string_buffer(size);self.buffers.append(value);return value
        self.envset=buffer(0x91000);self.global_obj=buffer(0x120);self.handle=buffer(0xb8)
        self.core=buffer(0x238);self.core_table=buffer(0x70);self.env_table=buffer(8)
        self.task=buffer(0x140);self.wait=buffer(0x28);self.wait_system=buffer(0x28)
        self.manager=buffer(0x30);self.manager_table=buffer(0x1a0);self.context=buffer(0x90)
        self.segments=buffer(12);self.outer=buffer(0x10);self.descriptor=buffer(0x28)
        self.facade=buffer(0x30);self.dispatch=buffer(8);self.impl=buffer(0x20);self.mutex=buffer(0x40)
        def pointer(source,offset,target,extra=0):struct.pack_into('<Q',source,offset,ctypes.addressof(target)+extra)
        for source,offset,target,extra in (
            (self.handle,0,self.global_obj,0),(self.handle,0xb0,self.mutex,0),
            (self.global_obj,0x68,self.task,0),(self.global_obj,0x88,self.envset,0),
            (self.global_obj,0x118,self.facade,0),(self.facade,0x28,self.dispatch,0),
            (self.dispatch,0,self.impl,0),(self.impl,0x10,self.core,0),
            (self.core,0,self.core_table,0),(self.core,0x220,self.handle,0),
            (self.core,0x30,self.envset,OWNERS),(self.wait,0,self.wait_system,0),
            (self.wait_system,0x20,self.handle,0),(self.manager,0,self.manager_table,0),
            (self.manager,8,self.outer,0),(self.outer,8,self.wait,0),
            (self.manager,0x10,self.context,0),(self.manager,0x18,self.core,0),
            (self.manager,0x28,self.core,0),(self.context,0x30,self.segments,0)):
            pointer(source,offset,target,extra)
        struct.pack_into('<i',self.context,0,4);struct.pack_into('<b',self.context,0x38,1)
        struct.pack_into('<3I',self.segments,0,0,len(initial),1)
        struct.pack_into('<4I4B',self.descriptor,0,0,0,1,0,6,0,1,0)
        struct.pack_into('<I',self.task,8,flag);struct.pack_into('<Q',self.task,0x138,1 if current else 2)
        struct.pack_into('<B',self.wait,0xc,int(enabled))
        self.records=[]
        for i,value in enumerate(map(_float32,initial)):
            record=buffer(16);struct.pack_into('<ffIf',record,0,value,0.,0,value);self.records.append(record)
            base=OWNERS+0x48*i
            pointer(self.envset,base,self.env_table);pointer(self.envset,base+0x18,self.global_obj)
            pointer(self.envset,base+0x20,record);struct.pack_into('<II',self.envset,base+0x38,4,i)
        self.primitive_callbacks={}
        def callback(target,restype,arguments,function):
            invoke=ctypes.CFUNCTYPE(restype,*arguments)(function);self.callbacks.append(invoke)
            self.primitive_callbacks[target]=ctypes.cast(invoke,ctypes.c_void_p).value
            return invoke
        def locked(out,mutex):
            ctypes.c_void_p.from_address(out).value=mutex
            return out
        def unique_lock(out):ctypes.c_uint8.from_address(out+8).value=1
        def signal(_):self.signals+=1;return 0
        def condition_wait(_mutex,_lock):
            try:
                for _ in range(5000):
                    self.step()
                    if self.flag!=5:return
                self.errors.append('Owned condition wait exceeded progress budget')
            except Exception as error:
                self.errors.append(f'Owned condition callback failed: {error}')
            struct.pack_into('<I',self.task,8,3)
        def wait_request(pointer,count,wait):
            if pointer!=ctypes.addressof(self.wait):self.errors.append('Unexpected wait object')
            self.waits.append((self.clock,count,bool(wait)))
            self.functions['wait_samples'](pointer,count,wait)
        def read_literal(_manager,symbol):
            if not 1<=symbol<=len(self.literals):self.errors.append('Unexpected literal read');return 0.
            return self.literals[symbol-1]
        def write_literal(_manager,symbol,value):
            if not 1<=symbol<=len(self.literals):self.errors.append('Unexpected literal write');return
            self.operations.append((self.clock,'write',symbol-1,value));self.literals[symbol-1]=value
        def record_wait(pointer,count,wait):
            self.operations.append((self.clock,'wait',count,bool(wait)));wait_request(pointer,count,wait)
        callback(0x16d470,ctypes.c_void_p,(ctypes.c_void_p,ctypes.c_void_p),locked)
        callback(0x364e60,None,(ctypes.c_void_p,),unique_lock)
        callback(0x364674,None,(ctypes.c_void_p,ctypes.c_void_p),condition_wait)
        callback(0x6d8e0c,ctypes.c_int,(ctypes.c_void_p,),lambda _:0)
        callback(0x6d8e24,ctypes.c_int,(ctypes.c_void_p,),lambda _:0)
        callback(0x6d8d58,ctypes.c_int,(ctypes.c_void_p,),signal)
        callback(0x6d8ea8,ctypes.c_uint64,(),lambda:1)
        self._wait_request=wait_request
        callback(0x2a5938,None,(ctypes.c_void_p,ctypes.c_int,ctypes.c_bool),record_wait)
        read=ctypes.CFUNCTYPE(ctypes.c_double,ctypes.c_void_p,ctypes.c_void_p)(read_literal)
        write=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_double)(write_literal)
        def interrupt(pointer,slot):
            if pointer!=ctypes.addressof(self.core)or not 0<=slot<self.count:
                self.errors.append('Unexpected envelope interrupt');return
            self.interrupts.append((self.clock,slot));self.functions['core_isr'](pointer,slot)
        isr=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_int)(interrupt)
        self.callbacks.extend((read,write,isr))
        for slot,function in ((0xe0,read),(0xc8,write)):
            struct.pack_into('<Q',self.manager_table,slot,ctypes.cast(function,ctypes.c_void_p).value)
        struct.pack_into('<Q',self.core_table,0x68,ctypes.cast(isr,ctypes.c_void_p).value)

    def bind(self,addresses):
        c=self.ctypes
        signatures={
            'manager_env':(None,(c.c_void_p,c.c_void_p,c.c_int,c.c_int,c.c_bool,c.c_double)),
            'literal':(None,(c.c_void_p,c.POINTER(c.c_void_p),c.POINTER(c.c_double),c.c_int,c.c_int)),
            'wait_samples':(None,(c.c_void_p,c.c_int,c.c_bool)),
            'core_env':(None,(c.c_void_p,c.c_int,c.c_int,c.c_bool,c.c_double)),
            'core_immediate':(None,(c.c_void_p,c.c_int,c.c_double)),
            'core_isr':(None,(c.c_void_p,c.c_int)),
        }
        for name in ('send_sync4','wait_step','set_flag'):
            signatures[name]=(None,(c.c_void_p,))
        self.functions={name:c.CFUNCTYPE(restype,*args)(addresses[name])for name,(restype,args)in signatures.items()}
        for slot,name in ((0x48,'core_env'),(0x50,'core_immediate'),(0x60,'core_wait')):
            struct.pack_into('<Q',self.core_table,slot,addresses[name])
        struct.pack_into('<Q',self.env_table,0,addresses['env_step'])

    @property
    def flag(self):return struct.unpack_from('<I',self.task,8)[0]

    def _states(self):return [struct.unpack_from('<ffIf',r)for r in self.records]

    def _check(self):
        if self.errors:raise ValueError('; '.join(self.errors))

    def step(self):
        self.clock+=1
        self.functions['send_sync4'](self.ctypes.addressof(self.envset))
        self.functions['wait_step'](self.ctypes.addressof(self.wait))
        self._check()

    def wait_samples(self,count,wait=True):
        if type(count)is not int or not 0<=count<=4096 or type(wait)is not bool:
            raise ValueError('Expected sample count0..4096 and explicit wait boolean')
        self._wait_request(self.ctypes.addressof(self.wait),count,wait);self._check()

    def write_env(self,slot,target,selector=10,wait=False):
        _write_args(self._states(),slot,target,selector,wait)
        self.functions['manager_env'](self.ctypes.addressof(self.manager),self.ctypes.addressof(self.descriptor),
            slot,selector,wait,float(target));self._check()

    def interpolate(self,indices,targets,amount):
        _indices(indices,len(self.literals));literal_operations([self.literals[i]for i in indices],targets,amount)
        c=self.ctypes;symbols=(c.c_void_p*len(indices))(*(i+1 for i in indices))
        values=(c.c_double*len(targets))(*targets)
        self.functions['literal'](c.addressof(self.manager),symbols,values,len(indices),amount);self._check()

    def snapshot(self):
        def slots(offset):
            return [i for i in range(self.count)if struct.unpack_from('<Q',self.envset,offset+8*(i//64))[0]>>(i%64)&1]
        active=slots(ACTIVE);pending=slots(PENDING)
        if (struct.unpack_from('<I',self.envset,ACTIVE_COUNT)[0]!=len(active)
                or struct.unpack_from('<I',self.envset,PENDING_COUNT)[0]!=len(pending)):
            raise ValueError('Native bitmap/count mismatch')
        if any(struct.unpack_from('<I',self.envset,OWNERS+0x48*i+0x40)[0]!=int(i in active)
                for i in range(self.count)):
            raise ValueError('Native owner sync flag disagrees with active bitmap')
        return dict(states=self._states(),active=active,pending=pending,flag=self.flag,clock=self.clock,
            counter=struct.unpack_from('<i',self.wait,8)[0],signals=self.signals,
            interrupts=self.interrupts.copy(),waits=self.waits.copy(),literals=self.literals.copy(),
            operations=self.operations.copy())


@contextmanager
def native_manager(initial,*,literal_initial=(),current=True,enabled=True,flag=3):
    _settings(initial,current,enabled,flag);literal_operations(literal_initial,literal_initial,0)
    fixture=_NativeManager(initial,literal_initial,current,enabled,flag)
    with _owned_functions(fixture.primitive_callbacks)as addresses:
        fixture.bind(addresses)
        yield fixture


def _canonical(value):
    if isinstance(value,float):return ('float',value.hex())
    if isinstance(value,dict):return tuple((k,_canonical(v))for k,v in sorted(value.items()))
    if isinstance(value,(list,tuple)):return tuple(map(_canonical,value))
    return value


def compare_snapshots(model,native):
    if _canonical(model.snapshot())!=_canonical(native.snapshot()):
        raise ValueError(f'Manager states differ at modeled/native ticks {model.clock}/{native.clock}')


def compare_action(model,native,action):
    """Compare every wait-driven tick as well as the final manager/event state."""
    traces=[[],[]];old_steps=[model.step,native.step]
    def traced(index):
        def step():
            old_steps[index]()
            state=(model,native)[index].snapshot()
            traces[index].append(hashlib.sha256(repr(_canonical(state)).encode()).digest())
        return step
    model.step=traced(0);native.step=traced(1)
    try:
        action(model);action(native)
    finally:model.step,native.step=old_steps
    if traces[0]!=traces[1]:raise ValueError('Manager wait-driven state trajectory differs')
    compare_snapshots(model,native)
    return len(traces[0])


def selfcheck(ticks=12000):
    if type(ticks)is not int or not 1<=ticks<=100000:raise ValueError('Expected1..100000 explicit sync ticks')
    result=report();cases=0;wait_ticks=0
    for current in (True,False):
        for enabled in (True,False):
            for flag in (3,4):
                for amount in (-5,0,1,2,100):
                    args=dict(literal_initial=[.1,-0.,.2],current=current,enabled=enabled,flag=flag)
                    model=ManagerModel([0.,0.],**args)
                    with native_manager([0.,0.],**args)as native:
                        wait_ticks+=compare_action(model,native,lambda x:x.interpolate([0,1,2],[.9,-0.,.2],amount))
                    cases+=1
    initial=[(i*7%11-5)/10 for i in range(20)]
    model=ManagerModel(initial);writes=0
    with native_manager(initial)as native:
        for tick in range(ticks):
            if tick%127==0:
                slot=(tick//127*7)%20;target=.9*math.sin(tick/73);selector=(tick//127)%16
                model.write_env(slot,target,selector);native.write_env(slot,target,selector)
                compare_snapshots(model,native);writes+=1
            model.step();native.step();compare_snapshots(model,native)
    result.update(literal_context_cases=cases,literal_wait_driven_ticks_compared=wait_ticks,
        explicit_live_sync_ticks=ticks,live_writes=writes,live_record_fields_compared=ticks*20*4,
        owned_native_regions=len(REGIONS),task_and_bitmap_state_compared=True,
        cadence='one original DSP4 envelope-bank scan and one CDSPWait counter update per explicit fixture tick')
    return result


def eqvg_check(output=False,*,flag=3):
    """Connect original EqVg setter calls to the original manager/wait fixture."""
    from eqvg_study import coefficients,stored_coefficients,update_plan
    from eqvg_setter_study import native_function_setter
    old=stored_coefficients(coefficients(13,20,q=.25));new=coefficients(13,19000,q=128.)
    initial=[0.]*20
    for slot,value in zip((10,11,12,14,13),old,strict=True):initial[slot]=_float32(value)
    args=dict(literal_initial=old,flag=flag)
    model=ManagerModel(initial,**args);ticks=0;minimum=float('inf');requests=0
    with native_manager(initial,**args)as native:
        def margin():
            nonlocal minimum
            state=native.snapshot()
            a,b=state['literals'][:2]if output else[v[0]for v in state['states'][10:12]]
            g=1.+a;minimum=min(minimum,-g*b,4.+2*g*b-g*g)
        previous=native.step
        def step():previous();margin()
        native.step=step;margin()
        current=old[:2]if output else tuple(v[0]for v in model.states[10:12])
        plan=update_plan(current,new)
        if output:
            groups=[plan[:1],plan[1:]]if plan[0]['wait']else[plan]
            expected=[dict(manager_slot=0xf8,coefficients=[r['coefficient']+1 for r in group],
                values=[r['value']for r in group],count=len(group),time_selector=100)for group in groups]
        else:expected=plan
        def dispatch(call):
            nonlocal requests,ticks
            if requests>=len(expected)or _canonical(call)!=_canonical(expected[requests]):
                raise ValueError('Original EqVg request differs from independent plan')
            wanted=expected[requests];requests+=1
            if output:
                def action(manager):
                    record=wanted if manager is model else call
                    manager.interpolate([i-1 for i in record['coefficients']],record['values'],record['time_selector'])
            else:
                def action(manager):
                    record=wanted if manager is model else call
                    slot=(10,11,12,14,13)[record['coefficient']]
                    manager.write_env(slot,record['value'],record['time_selector'],record['wait'])
            ticks+=compare_action(model,native,action);margin()
        with native_function_setter(output,dispatch=dispatch)as setter:
            setter(13,19000,q=128.,current=current,envelope=True)
        if requests!=len(expected):raise ValueError('Original EqVg setter omitted a manager request')
        while model.active:
            model.step();native.step();compare_snapshots(model,native)
        margin();final=native.snapshot()
    return dict(output=output,initial_task_flag=flag,manager_requests=requests,
        wait_driven_ticks_compared=ticks,total_fixture_ticks=final['clock'],signals=final['signals'],
        literal_wait_requests=len(final['waits']),minimum_jury_margin=minimum,
        endpoint_plan_requested_wait=plan[0]['wait'],original_setter_manager_connected=True)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--ticks',type=int,default=12000);args=parser.parse_args()
    result=selfcheck(args.ticks)if args.execute_native else report()
    if args.execute_native:
        result['eqvg_protocol_cases']=[eqvg_check(output,flag=flag)for output in (False,True)for flag in (3,4)]
    print(json.dumps(result,indent=2))

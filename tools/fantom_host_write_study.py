"""Original host scalar-edit wrappers through storage, callbacks and routed messages."""
import struct

from fantom_host_family_study import (FamilyOracle,HostImage,report as family_report,
    descriptor,notification_bytes,PLACEMENTS,CFF,RAM,OBJECT,HEAP,SERIALIZE,SINK)

CONSTRUCT,WRITE,FINALIZE=0xc1c6f0,0xc1c810,0xc1c728
WRAPPERS=(0x478d60,0x478dd8)
CONTEXT=RAM+0xa000
NOTIFY_FLAG=0x4db0438
PARAMETERS=(3504,3505,4917,4918)


def clamped_value(value, minimum, maximum):
    if type(value) is not int:
        raise ValueError('int required')
    if value < -2147483648 or value > 2147483647:
        raise ValueError('signed32 required')
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def checked(placement,parameter,value,gate,canary):
    if (type(placement)is not int or not 0<=placement<3
            or type(parameter)is not int or parameter not in PARAMETERS
            or type(gate)is not int or gate not in (0,0x80)
            or type(canary)is not int or not 0<=canary<=255):
        raise ValueError('Expected a checked placement/live1 parameter, gate0/128 and canary byte')
    clamped_value(value,-20000,20000)


def report(image,core):
    import capstone
    result=family_report(image,core)
    md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
    anchors={0x478d8c:('bl','#0xc1c6f0'),0x478da0:('orr','w3, w3, #2'),
        0x478da8:('bl','#0xc1c810'),0x478db0:('bl','#0xc1c728'),
        0x478e04:('bl','#0xc1c6f0'),0x478e20:('bl','#0xc1c810'),
        0xc1b0d0:('b.gt','#0xc1b15c'),0xc1b0dc:('b.gt','#0xc1b15c'),
        0xc1b15c:('str','w1, [sp, #0x5c]'),0xc1b170:('strh','w4, [x3, x2]'),
        0xc1c840:('bl','#0xc1b028'),0xc1c774:('bl','#0xc1b2c0'),
        0xc1c77c:('ldrb','w0, [x0, #0x438]'),0xc1b4c0:('mov','w5, #2'),
        0xc08284:('bl','#0xbe2998'),0xc082e4:('bl','#0xbe4270')}
    for pc,expected in anchors.items():
        rows=list(md.disasm(image.read(pc,4),pc))
        if len(rows)!=1 or(rows[0].mnemonic,rows[0].op_str)!=expected:
            raise ValueError(f'Host write anchor changed at {pc:#x}')
    result.update(host_scalar_write=WRITE,host_transaction_constructor=CONSTRUCT,
        host_transaction_finalizer=FINALIZE,original_edit_wrappers=list(WRAPPERS),
        host_writer_clamps_to_descriptor_bounds=True,checked_live1_identical_values_still_written=True,
        optional_notify_flag_address=NOTIFY_FLAG,optional_notify_flag_live_value_proved=False)
    return result


class WriteOracle(FamilyOracle):
    def __init__(self,image,core):
        source=report(image,core);super().__init__(image,core);self.checked.update(source)
        import unicorn
        u=self.cpu;u.mem_map(0x478000,0x1000);u.mem_write(0x478000,image.read(0x478000,0x1000))
        u.mem_protect(0x478000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        u.mem_map(0xbfe000,0x1000);u.mem_write(0xbfe000,image.read(0xbfe000,0x1000))
        u.mem_protect(0xbfe000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        u.mem_map(0x4db0000,0x1000);self.active=False
        u.hook_add(unicorn.UC_HOOK_MEM_WRITE,self._write)

    def _write(self,u,access,address,size,value,_):
        if self.active and any(address<base+84 and base<address+size for _,_,base,_ in PLACEMENTS):
            # Unicorn reports STRH's full source register; only its low halfword is stored.
            if (address,size,value&65535)!=(self.target,2,self.expected_value&65535):
                raise ValueError(f'Unexpected host store: observed={(hex(address),size,value)}, expected={(hex(self.target),2,self.expected_value&65535)}, input={(self.parameter,self.value)}, pc={u.reg_read(self.arm.UC_ARM64_REG_PC):#x}')
            self.stores+=1

    def _code(self,u,pc,size,_):
        a=self.arm;r=lambda i:u.reg_read(getattr(a,f'UC_ARM64_REG_X{i}'))
        if 0x478000<=pc<0x479000:return
        if pc in (0xbe4620,0xbfe640):
            expected_object=0x412efe8 if pc==0xbe4620 else 0x424bb20
            native=bytes(u.mem_read(r(1),24));route=10 if pc==0xbe4620 else 4
            if r(0)!=expected_object or native[0]>>1!=1 or native[2]!=route:
                raise ValueError('Unexpected local parameter notification route')
            self.outputs.append((native,b''));self.local_routes.append(route)
            u.reg_write(a.UC_ARM64_REG_X0,0);u.reg_write(a.UC_ARM64_REG_PC,r(30));return
        if pc==CONSTRUCT:
            self.transaction=r(0)
            if (r(1),r(2),r(3),r(4))!=(CFF,self.family,0,self.context):
                raise ValueError('Original edit wrapper bound an unexpected transaction')
        elif pc==WRITE:
            if (r(0),r(1),r(2)&0xffffffff)!=(self.transaction,self.parameter,self.value&0xffffffff):
                raise ValueError('Original edit wrapper changed the requested scalar')
            if bytes(u.mem_read(r(0)+3,1))!=b'\x0a':raise ValueError('Original wrapper did not enable block sending')
        elif pc==FINALIZE:
            self.dirty=struct.unpack('<HH',u.mem_read(r(0)+0x12,4))
            if r(0)!=self.transaction or self.dirty!=(self.parameter,self.parameter)or bytes(u.mem_read(r(0)+0x19,1))!=b'\1':
                raise ValueError('Original write did not mark the exact requested dirty ID')
        elif pc==0xc08250:
            self.notify_args.append(tuple(r(i)&0xffffffff for i in range(6)))
        super()._code(u,pc,size,_)
        if pc==0xbe26a8:self.outputs.append(self.queued[-1])

    def edit(self,placement,parameter,value,gate=0,canary=0x5a):
        checked(placement,parameter,value,gate,canary)
        self.family,self.context,address,_=PLACEMENTS[placement]
        u=self.cpu;self.parameter=parameter;self.value=value
        _,minimum,maximum,offset,width=descriptor(self.image,parameter)
        if width!=2:raise ValueError('Expected the checked halfword descriptor')
        self.target=address+offset;self.expected_value=clamped_value(value,minimum,maximum)
        before={}
        for _,_,base,_ in PLACEMENTS:
            store=bytearray(84)
            for i in range(48):
                default,_,_,off,n=descriptor(self.image,3486+i)
                store[off:off+n]=(default&((1<<(8*n))-1)).to_bytes(n,'little')
            store[0]=85;struct.pack_into('<HH',store,20,1,1000)
            u.mem_write(base,bytes(store));before[base]=store
        expected=before[address].copy();struct.pack_into('<H',expected,offset,self.expected_value&65535)
        unchanged=expected==before[address]
        u.mem_write(CONTEXT,bytes(8)+bytes((self.context,)))
        u.mem_write(NOTIFY_FLAG,bytes((gate,)))
        u.mem_write(RAM+0x10000,bytes((canary,))*0xf000)
        self.outputs=[];self.local_routes=[];self.notify_args=[];self.queued=[];self.locks=[]
        self.allocations=[];self.chunks=[];self.refcalls=self.frees=self.stores=0;self.length=2
        self.active=True
        try:self._run(WRAPPERS[int(self.family==7)],CONTEXT,value&0xffffffff,parameter)
        finally:self.active=False
        for base,original in before.items():
            wanted=expected if base==address else original
            if bytes(u.mem_read(base,84))!=wanted:raise ValueError('Original edit changed an unrequested store byte')
        converted={4917:3504,4918:3505}.get(parameter,parameter)
        wanted_args=[(self.family,0,self.context,parameter,parameter,0)]
        if gate:wanted_args.append((self.family,0,self.context,converted,converted,2))
        if (self.stores!=1 or self.notify_args!=wanted_args
                or self.local_routes!=([10,4]if gate else[10])or len(self.queued)!=2
                or self.locks!=['lock','lock','unlock']or self.allocations or self.frees
                or struct.unpack('<I',u.mem_read(0x424cc08,4))[0]!=0):
            raise ValueError(f'Original transaction events differ: notifications={self.notify_args}, locks={self.locks}')
        wires=[]
        for native,payload in self.outputs:
            u.mem_write(OBJECT,native)
            if payload:u.mem_write(HEAP,struct.pack('<II',1,len(payload))+payload)
            self.chunks=[];self._run(SERIALIZE,SINK,OBJECT);wires.append(b''.join(self.chunks))
        from bmc_ipc import frames
        decoded=[next(frames(wire))for wire in wires]
        kinds=[r['kind']for r in decoded]
        if kinds!=([1,7,8,1]if gate else[1,7,8]):raise ValueError('Original edit output ordering differs')
        first,block,notification=decoded[:3]
        initial=notification_bytes(self.family,0,self.context,parameter,parameter).hex()
        if (first['payload']!=initial or first['destination']!=10
                or notification['payload']!=initial
                or block['block']!=dict(u16=0,byte2=self.context,byte3=offset,data=expected[offset:offset+2].hex())):
            raise ValueError('Original write-to-message bytes differ from independent layout')
        if gate and decoded[3]['payload']!=notification_bytes(self.family,0,self.context,converted,converted).hex():
            raise ValueError('Original optional local notification did not use converted IDs')
        return dict(stored_value=self.expected_value,store_unchanged=unchanged,messages=len(wires),
            local_messages=len(self.local_routes),bmc_messages=len(self.queued),physical_store_writes=self.stores)


def selfcheck(image,core):
    oracle=WriteOracle(image,core);cases=messages=unchanged=0;samples=[]
    for placement in range(3):
        for parameter in PARAMETERS:
            _,lo,hi,offset,_=descriptor(image,parameter);previous=1 if offset==20 else 1000
            values=sorted({-2147483648,lo-1,lo,previous,hi,hi+1,65535,65537,2147483647})
            for value in values:
                for gate in (0,0x80):
                    for canary in (0,0x5a,255):
                        row=oracle.edit(placement,parameter,value,gate,canary)
                        cases+=1;messages+=row['messages'];unchanged+=row['store_unchanged']
                        if placement==0 and gate==0 and canary==0x5a and value==65537:
                            samples.append(dict(parameter=parameter,input=value,stored=row['stored_value']))
    return dict(oracle.checked,original_host_scalar_edit_cases=cases,serialized_edit_messages=messages,
        identical_store_edits_still_written_and_notified=unchanged,clamp_examples=samples,
        original_wrapper_writer_destructor_callback_route_executed=True,
        output_queues_mutex_effects_and_global_flag_seeded=True,host_to_core1_translation_proved=False)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('host');parser.add_argument('core1')
    parser.add_argument('--execute-arm64',action='store_true');args=parser.parse_args()
    image=HostImage(Path(args.host).read_bytes());core=Core1(args.core1)
    print(json.dumps(selfcheck(image,core)if args.execute_arm64 else report(image,core),indent=2))

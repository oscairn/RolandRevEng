"""Pinned MFX mute-counter query and its original Fantom FDRV caller."""
import hashlib
import struct

from core1_wait_study import IMAGE_SHA256
from fantom_eqvg_study import ThumbOracle,SCRATCH,RETURN,LIVE,coefficients,stored_coefficients,update_plan
from line_shaping_study import _float32

GET_INTERFACE,QUERY,FILTER=0x01135188,0x61081de2,0x61049e86
MUTE_ON,MUTE_OFF=0x6102bfae,0x6102c064
GATE,SKIP=0x61029296,0x61029332
SYSTEM,INTERFACE,MANAGERS=0x2009bbf8,0x2009bc20,0x200a0d14
VTABLE=0x6117c494
FDRV_VTABLE=0x61176adc


def checked(counter,index):
    if type(counter)is not int or not 0<=counter<=0x7ffffffe:
        raise ValueError('Expected a checked nonnegative signed32 mute count below overflow')
    if type(index)is not int or not 0<=index<4:raise ValueError('Expected MFX slot0..3')


def envelope_enabled(counter):
    checked(counter,0)
    return counter==0


def mute_transition(counter,enabled,index=0,wait=False):
    checked(counter,index)
    if type(enabled)is not bool or type(wait)is not bool:raise ValueError('Expected explicit mute/wait booleans')
    if enabled:
        return (counter+1,[])if counter else(1,[('gate',index,True),('skip',index,wait)])
    return (counter-1,[])if counter>1 else(0,[('skip',index,True),('gate',index,False)])


def report(core):
    from dramio_owner_study import expect
    from core1_rtti import trace
    if hashlib.sha256(core.data).hexdigest()!=IMAGE_SHA256:raise ValueError('Expected pinned Fantom CORE1 payload')
    r=trace(core,'N7CFSPSys12CMyDSPSysMfxE')['candidates']
    if len(r)!=1 or r[0]['vtable']+8!=VTABLE or core.u32(VTABLE+4)!=QUERY|1:
        raise ValueError('MFX system interface RTTI/query changed')
    if core.u32(0x61176480)!=GET_INTERFACE|1:raise ValueError('Manager interface getter changed')
    fdrv=trace(core,'11CFspMfxFDRV')['candidates']
    if len(fdrv)!=1 or fdrv[0]['vtable']+8!=FDRV_VTABLE or core.u32(FDRV_VTABLE+0x10)!=FILTER|1:
        raise ValueError('Original FDRV owner/callback changed')
    for pc,mnemonic,operand in (
        (GET_INTERFACE,'ldr','r0, [r0, #0x10]'),(QUERY,'add.w','r0, r0, r1, lsl #2'),
        (QUERY+4,'ldr','r0, [r0, #0x14]'),(QUERY+8,'it','ne'),(QUERY+10,'movs','r0, #1'),
        (0x6102a52e,'add.w','r2, r0, #0x28'),(0x6102a53e,'strd','r4, ip, [r2]'),
        (0x6102a548,'str','r1, [r0, #0x3c]'),(0x6102a54e,'str','r1, [r0, #0x40]'),
        (0x6102a554,'str','r1, [r0, #0x44]'),(0x6102a560,'str','r1, [r0, #0x48]'),
        (0x6102c998,'add.w','r0, r5, r5, lsl #2'),(0x6102c99c,'adds.w','r0, sb, r0, lsl #2'),
        (0x6102c9b2,'add.w','r3, r6, #0x28'),(0x6102c9ba,'str','r3, [r0, #0x10]'),
        (0x6102c9da,'mov','r1, r5'),(0x61049e42,'str','r1, [r0, #8]'),
        (0x61049e46,'strd','r3, r2, [r0], #0xc'),
        (0x61049eb6,'blx','r1'),(0x61049eba,'ldr','r1, [r4, #8]'),
        (0x61049ebe,'blx','r2'),(0x61049ed0,'eor','r3, r0, #1'),
        (0x6102bfc6,'adds','r0, r0, #1'),(0x6102bfce,'str','r0, [r1, #0x14]'),
        (0x6102bfd6,'bl','#0x61029296'),(0x6102bfe4,'b.w','#0x61029332'),
        (0x6102c07a,'subs','r0, r0, #1'),(0x6102c082,'str','r0, [r1, #0x14]'),
        (0x6102c08a,'bl','#0x61029332'),(0x6102c098,'b.w','#0x61029296'),
        (0x011271bc,'ldr','r4, [pc, #0xd4]'),(0x011271cc,'bl','#0x1103762'),
        (0x01127202,'bl','#0x1103772'),(0x0112720c,'ldrb','r0, [r4]'),
        (0x0112f43c,'orr','r1, r1, #2'),(0x0112f448,'orr','r1, r1, #1')):
        expect(core,pc,mnemonic,operand)
    constants={0x6102a78c:VTABLE,0x6102cc44:MANAGERS,0x6102cc74:SYSTEM,
        0x01127294:0x200845b4,0x01127298:0x011271ad}
    if any(core.u32(a)!=v for a,v in constants.items()):raise ValueError('Interface or timer constants changed')
    return dict(payload_sha256=IMAGE_SHA256,interface_rtti=r[0],manager_getter=GET_INTERFACE,
        manager_array=MANAGERS,manager_stride=20,manager_count=4,system=SYSTEM,interface=INTERFACE,
        fdrv_vtable=FDRV_VTABLE,fdrv_constructor=0x61049e40,
        query=QUERY,counter_offsets=[0x14+4*i for i in range(4)],
        counter_addresses=[INTERFACE+0x14+4*i for i in range(4)],
        predicate='per-slot mute nesting count !=0; FDRV enables envelope when count==0',
        mute_on=MUTE_ON,mute_off=MUTE_OFF,source_task_identity_query=False,
        sample_wait_flag=0x200845b4,clear_completion_word=0x200847f8,clear_completion_mask=1,
        envelope_completion_mask=2,actual_task_exclusion_proved=False,hardware_timing_verified=False)


class ModeOracle(ThumbOracle):
    ENTRIES=(*ThumbOracle.ENTRIES,QUERY,FILTER,MUTE_ON,MUTE_OFF)

    def __init__(self,core):
        checked_source=report(core)
        super().__init__(core)
        self.checked.update(checked_source)

    def _code(self,u,address,size,_):
        if self.mode=='mute'and address in (GATE,SKIP):
            self.pc=address
            if u.reg_read(self.arm.UC_ARM_REG_R0)!=INTERFACE:raise ValueError('Unexpected mute helper owner')
            if u.reg_read(self.arm.UC_ARM_REG_R1)>=4 or u.reg_read(self.arm.UC_ARM_REG_R2)not in (0,1):
                raise ValueError('Unexpected mute helper index/Boolean')
            self.calls.append(('gate'if address==GATE else'skip',
                u.reg_read(self.arm.UC_ARM_REG_R1),bool(u.reg_read(self.arm.UC_ARM_REG_R2))))
            u.reg_write(self.arm.UC_ARM_REG_PC,u.reg_read(self.arm.UC_ARM_REG_LR));return
        if self.mode=='fdrv'and address==LIVE:
            self.envelope=bool(u.reg_read(self.arm.UC_ARM_REG_R3))
        if self.mode=='fdrv'and RETURN+0x100<=address<RETURN+0x200:
            self.pc=address;slot=address-RETURN-0x100
            symbol=u.reg_read(self.arm.UC_ARM_REG_R1)
            if symbol not in self.symbols:raise ValueError('Unexpected original coefficient symbol')
            raw=self.symbols[symbol]
            if slot==0xc8:
                if raw not in (0,1):raise ValueError('Unexpected current read')
                u.reg_write(self.arm.UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',self.current[raw]))[0])
            elif slot in (0xb8,0xc0):
                self.calls.append(dict(manager_slot=slot,coefficient=raw,value=self._f(0),
                    selector=u.reg_read(self.arm.UC_ARM_REG_R2)if slot==0xb8 else None,
                    wait=bool(u.reg_read(self.arm.UC_ARM_REG_R3))if slot==0xb8 else False))
            else:raise ValueError('Unexpected FDRV manager recording slot')
            return
        super()._code(u,address,size,_)

    def state(self,counter,index):
        checked(counter,index)
        self.cpu.mem_write(INTERFACE,struct.pack('<I',VTABLE))
        self.cpu.mem_write(INTERFACE+0x14,bytes(16))
        self.cpu.mem_write(INTERFACE+0x14+4*index,struct.pack('<I',counter))

    def query(self,counter,index=0):
        self.state(counter,index);self._run(QUERY,registers=(INTERFACE,index))
        return bool(self.cpu.reg_read(self.arm.UC_ARM_REG_R0))

    def mute(self,counter,enabled,index=0,wait=False):
        mute_transition(counter,enabled,index,wait);self.state(counter,index)
        self._run(MUTE_ON if enabled else MUTE_OFF,registers=(INTERFACE,index,int(wait)),mode='mute')
        return self._word(INTERFACE+0x14+4*index),self.calls.copy()

    def fdrv(self,counter,index=0,filter_index=0):
        checked(counter,index)
        if type(filter_index)is not int or filter_index not in (0,1):raise ValueError('Expected live filter0/1')
        self.state(counter,index);self.current=stored_coefficients(coefficients(13,20,q=.25))[:2]
        u=self.cpu;effect,table=SCRATCH+0x1000,SCRATCH+0x1200;manager=MANAGERS+20*index
        u.mem_write(manager,struct.pack('<5I',table,0,0,0,INTERFACE))
        u.mem_write(table+4,struct.pack('<I',GET_INTERFACE|1))
        for slot in (0xb8,0xc0,0xc8):u.mem_write(table+slot,struct.pack('<I',RETURN+0x100+slot+1))
        u.mem_write(effect,struct.pack('<5I',FDRV_VTABLE,manager,index,0x610e5c1c,0x610e5c34))
        descriptor=(0x610e5c1c,0x610e5c34)[filter_index]
        self.symbols={self.core.u32(descriptor+4+4*i):i for i in range(5)};self.envelope=None
        self._run(FILTER,registers=(effect,filter_index,13),singles=(19000.,0.,128.),mode='fdrv')
        expected=update_plan(self.current,coefficients(13,19000.,q=128.),envelope=envelope_enabled(counter))
        if self.envelope!=envelope_enabled(counter)or self.calls!=expected:raise ValueError('FDRV query/setter plan differs')
        return dict(envelope=self.envelope,writes=self.calls.copy())


def selfcheck(core):
    oracle=ModeOracle(core);result=report(core);queries=mutes=callers=0
    for index in range(4):
        for count in (0,1,2,127,65535):
            if oracle.query(count,index)!=(count!=0):raise ValueError('Mute query mismatch')
            queries+=1
            for enabled in (False,True):
                for wait in (False,True):
                    if oracle.mute(count,enabled,index,wait)!=mute_transition(count,enabled,index,wait):
                        raise ValueError('Mute counter/helper order mismatch')
                    mutes+=1
            for which in (0,1):oracle.fdrv(count,index,which);callers+=1
    result.update(query_cases=queries,mute_transition_cases=mutes,original_fdrv_caller_cases=callers,
        mute_helpers='recorded original call arguments/order; hardware gate/clear bodies excluded',
        caller_fixture='original getter/query/FDRV/piece/math; coefficient reads/writes recorded')
    return result


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--execute-thumb',action='store_true')
    args=parser.parse_args();core=Core1(args.image)
    print(json.dumps(selfcheck(core)if args.execute_thumb else report(core),indent=2))

"""Pinned unchanged-algorithm Fantom parameter dispatch into the live EqVg setter."""
import struct

from fantom_envelope_mode_study import (ModeOracle,report as mode_report,checked,
    INTERFACE,MANAGERS,FDRV_VTABLE,FILTER)
from fantom_eqvg_study import SCRATCH,RETURN,coefficients,stored_coefficients,update_plan
from eqfa_ui_study import vg_events
from line_shaping_study import _float32

UPDATE,APPLY,SLOPE=0x011290ee,0x61032e90,0x61049f6e
PARAM_VTABLE,OUTER_VTABLE=0x61176e20,0x6117b3d8


def inputs(values,changed,counter,index):
    checked(counter,index)
    if (not isinstance(values,dict)or set(values)!={2,3}
            or any(type(v)is not int for v in values.values())
            or not 0<=values[2]<=2 or not 0<=values[3]<=23000
            or not isinstance(changed,(list,tuple,set))
            or any(type(i)is not int or i not in (2,3)for i in changed)):
        raise ValueError('Expected checked live1 mode/cutoff fields2/3 and their logical changed set')
    return vg_events(values,changed)


def report(core):
    from dramio_owner_study import expect
    from kernel_abi import read
    from core1_rtti import trace
    result=mode_report(core)
    r=trace(core,'11CMfxFDRVPrm')['candidates']
    if len(r)!=1 or r[0]['vtable']+8!=PARAM_VTABLE or core.u32(PARAM_VTABLE+4)!=APPLY|1:
        raise ValueError('Original FDRV parameter callback changed')
    if core.u32(OUTER_VTABLE+0x14)!=UPDATE|1 or core.u32(FDRV_VTABLE+0x14)!=SLOPE|1:
        raise ValueError('Outer update or companion slope slot changed')
    for pc,mnemonic,operand in (
        (0x011290fe,'cmp','r7, r1'),(0x01129104,'b','#0x11291ba'),
        (0x011291c0,'ldr','r0, [r0, #4]'),(0x011291c4,'ldr','r3, [r3, #4]'),
        (0x011291c6,'blx','r3'),(0x011291cc,'ldr','r1, [r1, #4]'),
        (0x61032efe,'blx','r2'),(0x61032f1c,'movs','r5, #0'),
        (0x61032f1e,'movs','r5, #0xd'),(0x61032f36,'vldr','s2, [pc, #0x2f0]'),
        (0x61032f40,'ldr','r3, [r1, #0x10]'),(0x61032f42,'movs','r1, #1'),
        (0x61032f44,'blx','r3'),(0x61032f5e,'subs','r2, r0, #1'),
        (0x61032f64,'ldr','r3, [r0, #0x14]'),(0x61032f68,'blx','r3'),
        (0x011024a0,'cpsid','i'),(0x011024be,'cpsie','i'),
        (0x011024ce,'cpsid','i'),(0x011024ec,'cpsie','i')):
        expect(core,pc,mnemonic,operand)
    if (core.u32(0x61033224)!=0 or core.u32(0x61033228)!=0x3f34fdf4):
        raise ValueError('Live1 fixed gain/Q constants changed')
    for start,end in ((0x01102494,0x011024c2),(0x011024c2,0x011024f0)):
        code=list(core.md.disasm(read(core,start,end-start),start))
        if sum(i.size for i in code)!=end-start or any(i.mnemonic in ('mrs','msr')for i in code):
            raise ValueError('Mask helper no longer matches the no-save/restore body')
    result.update(parameter_rtti=r[0],parameter_vtable=PARAM_VTABLE,parameter_apply=APPLY,
        outer_update=UPDATE,fields=[2,3],live_filter_index=1,fixed_gain=0.,fixed_q=_float32(.707),
        changed_input='logical recording callbacks; raw flag/buffer ABI not decoded',
        helper_preserves_incoming_primask=False,mask_helper_entries=[0x01102494,0x011024c2],
        registered_task_to_setter_route_proved=False,physical_ui_or_midi_mapping_proved=False)
    return result


class DispatchOracle(ModeOracle):
    ENTRIES=(*ModeOracle.ENTRIES,UPDATE)
    ALGORITHM=42

    def __init__(self,core):
        checked_source=report(core)
        super().__init__(core);self.checked.update(checked_source)
        for offset in (0x300,0x304,0x308):self.cpu.mem_write(RETURN+offset,bytes.fromhex('7047'))

    def _code(self,u,address,size,_):
        if self.mode=='fdrv'and address in (RETURN+0x300,RETURN+0x304,RETURN+0x308):
            self.pc=address;a=self.arm
            if u.reg_read(a.UC_ARM_REG_R0)!=self.interface:raise ValueError('Unexpected parameter interface')
            field=u.reg_read(a.UC_ARM_REG_R1)
            if address==RETURN+0x300:
                self.init_args.append((field,u.reg_read(a.UC_ARM_REG_R2)))
            elif address==RETURN+0x304:
                if field not in self.values:raise ValueError('Unexpected parameter value read')
                u.reg_write(a.UC_ARM_REG_R0,self.values[field])
            else:
                if not 0<=field<=21:raise ValueError('Unexpected changed-field query')
                u.reg_write(a.UC_ARM_REG_R0,int(field in self.changed))
            return
        if self.mode=='fdrv'and address in (FILTER,SLOPE):
            a=self.arm
            if u.reg_read(a.UC_ARM_REG_R0)!=self.effect:raise ValueError('Unexpected CFsp receiver')
            which=u.reg_read(a.UC_ARM_REG_R1);selector=u.reg_read(a.UC_ARM_REG_R2)
            if address==FILTER:
                self.setter_calls.append(dict(filter=which,type=selector,cutoff=self._f(0),gain=self._f(1),q=self._f(2)))
            else:
                self.pc=address;self.slope_calls.append((which,selector if selector<0x80000000 else selector-0x100000000))
                u.reg_write(a.UC_ARM_REG_PC,u.reg_read(a.UC_ARM_REG_LR));return
        super()._code(u,address,size,_)

    def _parameter_interface(self,wrapper,table,args):
        self.cpu.mem_write(self.interface,struct.pack('<I',table))
        for slot,stub in ((4,0x300),(8,0x304),(12,0x308)):
            self.cpu.mem_write(table+slot,struct.pack('<I',RETURN+stub+1))
        return args

    def _dispatch_parameter(self,outer,args):
        self._run(UPDATE,registers=(outer,self.ALGORITHM,*args),mode='fdrv')

    def parameter(self,values,changed,counter=0,index=0):
        events=inputs(values,changed,counter,index)
        self.values=values.copy();self.changed=set(changed);self.state(counter,index)
        self.current=stored_coefficients(coefficients(13,20,q=.25))[:2]
        self.init_args=[];self.setter_calls=[];self.slope_calls=[];self.envelope=None
        u=self.cpu;manager=MANAGERS+20*index
        outer,wrapper,self.interface,self.effect,table,parameter_table=(SCRATCH+i for i in (0x1000,0x1100,0x1200,0x1300,0x1400,0x1600))
        tags=(SCRATCH+0x1800,SCRATCH+0x1900)
        u.mem_write(manager,struct.pack('<5I',table,0,0,0,INTERFACE))
        u.mem_write(table+4,struct.pack('<I',0x01135189))
        for slot in (0xb8,0xc0,0xc8):u.mem_write(table+slot,struct.pack('<I',RETURN+0x100+slot+1))
        u.mem_write(self.effect,struct.pack('<5I',FDRV_VTABLE,manager,index,0x610e5c1c,0x610e5c34))
        self.symbols={self.core.u32(0x610e5c38+4*i):i for i in range(5)}
        u.mem_write(wrapper,struct.pack('<II',PARAM_VTABLE,self.interface))
        u.mem_write(wrapper+0x74,struct.pack('<I',self.effect))
        tags=self._parameter_interface(wrapper,parameter_table,tags)
        u.mem_write(outer,bytes(0x20));u.mem_write(outer,struct.pack('<I',OUTER_VTABLE))
        u.mem_write(outer+8,struct.pack('<I',wrapper));u.mem_write(outer+0x18,struct.pack('<I',self.ALGORITHM))
        self._dispatch_parameter(outer,tags)
        wanted=[dict(filter=1,type=e['type'],cutoff=_float32(e['cutoff']),gain=0.,q=_float32(e['q']))for e in events]
        expected=[]
        for e in events:
            expected.extend(update_plan(self.current,coefficients(e['type'],e['cutoff'],q=e['q']),envelope=counter==0))
        slopes=[(1,values[2]-1)]if 2 in self.changed else[]
        if (self.init_args!=[tags]or self.setter_calls!=wanted or self.slope_calls!=slopes
                or self.calls!=expected or self.envelope!=(counter==0 if events else None)):
            raise ValueError('Original outer/parameter/FDRV dispatch differs from the independent plan')
        return dict(init_args=self.init_args.copy(),setters=self.setter_calls.copy(),slopes=self.slope_calls.copy(),
            writes=self.calls.copy(),envelope=self.envelope)


def selfcheck(core):
    oracle=DispatchOracle(core);result=report(core);cases=writes=0
    for index in (0,3):
        for counter in (0,2):
            for mode in range(3):
                for cutoff in (20,19000):
                    for changed in ((),(2,),(3,),(2,3)):
                        row=oracle.parameter({2:mode,3:cutoff},changed,counter,index)
                        cases+=1;writes+=len(row['writes'])
    result.update(original_dispatch_cases=cases,coefficient_writes_compared=writes,
        companion_slope='recorded only; its coefficient changes are not applied',
        algorithm_change_path_executed=False,firmware_startup_or_os_tasks_executed=False)
    return result


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--execute-thumb',action='store_true')
    args=parser.parse_args();core=Core1(args.image)
    print(json.dumps(selfcheck(core)if args.execute_thumb else report(core),indent=2))

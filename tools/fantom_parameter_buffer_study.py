"""Pinned Fantom parameter snapshots, changed bytes and original FDRV dispatch."""
import struct

from fantom_parameter_dispatch_study import DispatchOracle,report as dispatch_report
from fantom_eqvg_study import SCRATCH

# Capacity: (vtable, reset, update, signed-value getter, signed-flag getter).
BUFFERS={20:(0x6117b7e0,0x0113995c,0x01139988,0x01139aa2,0x01139a9a),
    24:(0x6117b7f8,0x011399fc,0x01139a28,0x01139ab4,0x01139aac),
    32:(0x6117b810,0x610848d8,0x61084904,0x6108497e,0x61084976)}
BUFFER,SOURCE=SCRATCH+0x3000,SCRATCH+0x4000


def shorts(values):
    if (not isinstance(values,(list,tuple))
            or any(type(v)is not int or not -32768<=v<=32767 for v in values)):
        raise ValueError('Expected signed 16-bit parameter values')
    return list(values)


def initial_state(capacity,values):
    values=shorts(values)
    if type(capacity)is not int or capacity not in BUFFERS or len(values)!=capacity:
        raise ValueError('Expected a supported capacity and explicit prior value storage')
    return dict(capacity=capacity,count=0,values=values,changed=[1]*capacity)


def checked_state(state):
    if not isinstance(state,dict)or set(state)!={'capacity','count','values','changed'}:
        raise ValueError('Expected a complete bounded buffer state')
    capacity=state['capacity'];initial_state(capacity,state['values'])
    if (type(state['count'])is not int or not 0<=state['count']<=capacity
            or not isinstance(state['changed'],(list,tuple))or len(state['changed'])!=capacity
            or any(type(v)is not int or v not in (0,1)for v in state['changed'])):
        raise ValueError('Expected a nonnegative count and Boolean changed bytes')
    return dict(capacity=capacity,count=state['count'],values=list(state['values']),changed=list(state['changed']))


def update_state(state,values):
    """Copy a prefix; zero count keeps storage/flags, oversized count is a no-op."""
    result=checked_state(state);values=shorts(values);count=len(values)
    if count>result['capacity']:return result
    for i,value in enumerate(values):
        result['changed'][i]=int(result['count']==0 or value!=result['values'][i])
    result['values'][:count]=values;result['count']=count
    return result


def report(core):
    from core1_rtti import trace
    from dramio_owner_study import expect
    result=dispatch_report(core)
    for capacity,(vtable,reset,update,value,changed)in BUFFERS.items():
        rows=trace(core,f'22CEfctPrmBufferTemplateILi{capacity}EE')['candidates']
        if (len(rows)!=1 or rows[0]['vtable']+8!=vtable
                or [core.u32(vtable+4*i)for i in range(4)]!=[p|1 for p in (reset,update,value,changed)]):
            raise ValueError('Parameter buffer RTTI/vtable changed')
        for pc,mnemonic,operand in ((reset,'movs','r2, #0'),(reset+0x28,'str','r1, [r0, #4]'),
                (update+4,'cmp',f'r2, #{capacity:#x}'),(update+8,'pop.w','{r4, r5, r6, r7, r8, sb}'),
                (update+0x5a,'ldrh','r5, [r3], #-2'),(update+0x60,'strh.w','r5, [r8, #6]'),
                (update+0x6a,'str','r2, [r0, #4]'),(value+4,'ldrsh.w','r0, [r0, #8]'),
                (changed+2,'ldrsb.w',f'r0, [r0, #{8+2*capacity:#x}]')):
            expect(core,pc,mnemonic,operand)
    for pc,mnemonic,operand in (
            (0x6102f192,'bl','#0x61049e40'),(0x6102f198,'adds.w','r0, r5, #0x54'),
            (0x6102f1a0,'add.w','r2, r0, #8'),(0x6102f1a8,'str','r3, [r0, #8]'),
            (0x6102f1aa,'str','r2, [r0, #4]'),(0x6102f1ae,'str','r2, [r0]'),
            (0x6102f1b0,'str','r1, [r0, #0x74]')):
        expect(core,pc,mnemonic,operand)
    if core.u32(0x6102f260)!=BUFFERS[32][0]or core.u32(0x6102f2ac)!=0x61176e20:
        raise ValueError('FDRV factory buffer binding changed')
    result.update(buffer_capacities=list(BUFFERS),fdrv_buffer_capacity=32,
        parameter_buffer_offsets=dict(vtable=0,count=4,values=8,changed=0x48),
        raw_update_arguments='signed int16 source pointer, nonnegative element count',
        raw_count_is_bytes=False,raw_flags_are_input=False,
        source_lifetime='values copied synchronously; no retained source pointer in checked update',
        signed_negative_counts_admitted=False,registered_task_to_setter_route_proved=False)
    return result


class BufferOracle(DispatchOracle):
    ENTRIES=(*DispatchOracle.ENTRIES,*(p for row in BUFFERS.values()for p in row[1:]))

    def __init__(self,core):
        source=report(core);super().__init__(core);self.checked.update(source)

    def buffer(self,state,values=None):
        state=checked_state(state);capacity=state['capacity'];vtable,reset,update,value,flag=BUFFERS[capacity]
        payload=None if values is None else shorts(values)
        before=struct.pack('<Ii',vtable,state['count'])+struct.pack('<'+'h'*capacity,*state['values'])+bytes(state['changed'])
        canary=b'\xa5'*16;u=self.cpu
        u.mem_write(BUFFER-16,canary+before+canary)
        if payload is None:
            expected=initial_state(capacity,state['values']);self._run(reset,registers=(BUFFER,))
        else:
            expected=update_state(state,payload)
            source=SOURCE if 0<len(payload)<=capacity else 0
            if source:u.mem_write(source,struct.pack('<'+'h'*len(payload),*payload))
            self._run(update,registers=(BUFFER,source,len(payload)))
        after=bytes(u.mem_read(BUFFER,len(before)))
        if (bytes(u.mem_read(BUFFER-16,16))!=canary
                or bytes(u.mem_read(BUFFER+len(before),16))!=canary or self._word(BUFFER)!=vtable):
            raise ValueError('Parameter buffer wrote outside its state')
        actual=dict(capacity=capacity,count=struct.unpack_from('<i',after,4)[0],
            values=list(struct.unpack_from('<'+'h'*capacity,after,8)),changed=list(after[8+2*capacity:]))
        if actual!=expected:raise ValueError('Original parameter buffer differs from independent prefix model')
        if payload and len(payload)<=capacity:
            if bytes(u.mem_read(SOURCE,2*len(payload)))!=struct.pack('<'+'h'*len(payload),*payload):
                raise ValueError('Original parameter update modified its source')
        u.mem_write(SOURCE,b'\x5a'*(2*capacity))
        for i in range(capacity):
            for entry,wanted in ((value,actual['values'][i]),(flag,actual['changed'][i])):
                self._run(entry,registers=(BUFFER,i))
                got=self.cpu.reg_read(self.arm.UC_ARM_REG_R0)
                if got!=wanted&0xffffffff:raise ValueError('Original signed parameter getter differs')
        return actual

    def _parameter_interface(self,wrapper,table,args):
        # Use the factory's embedded interface position, then execute its real update/getters.
        self.interface=wrapper+8
        state=self.raw_state
        self.cpu.mem_write(wrapper+4,struct.pack('<I',self.interface))
        raw=struct.pack('<Ii',BUFFERS[32][0],0)+struct.pack('<32h',*state['values'])+bytes(32)
        self.cpu.mem_write(self.interface,raw)
        self._run(BUFFERS[32][1],registers=(self.interface,))
        self.cpu.mem_write(SOURCE,struct.pack('<32h',*state['values']))
        self._run(BUFFERS[32][2],registers=(self.interface,SOURCE,32))
        self.cpu.mem_write(SOURCE,struct.pack('<32h',*self.raw_values))
        return SOURCE,32

    def _code(self,u,address,size,_):
        if self.mode=='fdrv'and address==BUFFERS[32][2]:
            if u.reg_read(self.arm.UC_ARM_REG_R0)!=self.interface:
                raise ValueError('Unexpected raw parameter buffer receiver')
            self.init_args.append((u.reg_read(self.arm.UC_ARM_REG_R1),u.reg_read(self.arm.UC_ARM_REG_R2)))
        super()._code(u,address,size,_)

    def snapshot(self,previous,values,counter=0,index=0):
        previous=shorts(previous);values=shorts(values)
        if len(previous)!=32 or len(values)!=32 or any(previous[i]!=values[i]for i in range(32)if i not in (2,3)):
            raise ValueError('Connected fixture admits 32-field snapshots changing only live1 fields2/3')
        state=initial_state(32,previous)
        self.raw_state=update_state(state,previous);self.raw_values=values
        expected=update_state(self.raw_state,values)
        changed=[i for i in (2,3)if expected['changed'][i]]
        result=self.parameter({2:values[2],3:values[3]},changed,counter,index)
        stored=bytes(self.cpu.mem_read(self.interface,104))
        wanted=struct.pack('<Ii32h',BUFFERS[32][0],32,*values)+bytes(expected['changed'])
        if stored!=wanted:raise ValueError('Connected dispatch did not retain the checked raw snapshot')
        result.update(raw_count=32,changed_fields=changed)
        return result


def selfcheck(core):
    oracle=BufferOracle(core);result=report(core);cases=dispatches=writes=0
    for capacity in BUFFERS:
        values=[(-32768,32767,-1,0,1)[i%5]for i in range(capacity)]
        state=initial_state(capacity,values);state['count']=capacity;state['changed']=[i%2 for i in range(capacity)]
        state=oracle.buffer(state);cases+=1
        for incoming in (values,values,values[:1],[7]*capacity,[],values,[0]*(capacity+1)):
            state=oracle.buffer(state,incoming);cases+=1
    for index in (0,3):
        for counter in (0,2):
            for mode in range(3):
                for cutoff in (20,19000):
                    for changed in ((),(2,),(3,),(2,3)):
                        values=[0]*32;values[2]=mode;values[3]=cutoff
                        previous=values.copy()
                        for i in changed:previous[i]=values[i]-1
                        row=oracle.snapshot(previous,values,counter,index)
                        dispatches+=1;writes+=len(row['writes'])
    result.update(original_buffer_cases=cases,original_raw_dispatch_cases=dispatches,
        raw_dispatch_coefficient_writes=writes,original_buffer_routines_executed=True,
        firmware_startup_or_os_tasks_executed=False)
    return result


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--execute-thumb',action='store_true')
    args=parser.parse_args();core=Core1(args.image)
    print(json.dumps(selfcheck(core)if args.execute_thumb else report(core),indent=2))

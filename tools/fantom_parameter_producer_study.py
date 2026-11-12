"""Pinned EFCT callback -> stock FDRV descriptor reader -> coefficient dispatch."""
import struct

from fantom_parameter_buffer_study import BufferOracle,initial_state,update_state,shorts,report as buffer_report
from fantom_parameter_dispatch_study import UPDATE
from fantom_eqvg_study import SCRATCH
from fantom_envelope_mode_study import INTERFACE,checked

CALLBACK,HANDLER,PRODUCER=0x01126a6c,0x0110225c,0x610835d0
NOTIFY,NOTIFICATION=0x01126d2e,SCRATCH+0x5000
OWNER=SCRATCH+0x8000
DIRTY,ROOT,LATE_FLAGS=0x20083e74,0x200845b8,0x20094ed4
CALLBACK_SLOT,ACTIVITY,INVOCATIONS=0x20084978,0x200848f8,0x200848b8
PARAM_BASE,PARAM_STRIDE=0x614012d4,84
TYPE,RANGE,DESCRIPTORS=85,0x61093780,0x611616b8


def normalized(value,descriptor):
    """The original reader chooses signedness from min, then falls back to default."""
    if (not isinstance(descriptor,(list,tuple))or len(descriptor)!=5
            or any(type(v)is not int for v in descriptor)):
        raise ValueError('Expected five integer descriptor fields')
    default,minimum,maximum,offset,width=descriptor
    if (type(value)is not int or not -32768<=value<=32767 or width!=2
            or minimum>maximum or not minimum<=default<=maximum):
        raise ValueError('Expected a checked halfword parameter descriptor and raw value')
    decoded=value&0xffff
    if minimum<0 and decoded&0x8000:decoded-=0x10000
    return decoded if minimum<=decoded<=maximum else default


def fields(core):
    from kernel_abi import read
    start,end=struct.unpack('<HH',read(core,RANGE+4*TYPE,4))
    if (start,end)!=(2840,2865):raise ValueError('FDRV parameter range changed')
    result=[struct.unpack('<5i',read(core,DESCRIPTORS+20*(start+4+i),20))for i in range(end-start-3)]
    if any(row[3:]!=(16+2*i,2)for i,row in enumerate(result)):
        raise ValueError('FDRV halfword descriptor layout changed')
    return result


def checked_slot(index):
    if type(index)is not int or index not in (1,2,3):
        raise ValueError('Producer fixture admits stock MFX slots1..3 only')
    return index-1


def report(core):
    from dramio_owner_study import expect
    from kernel_abi import read
    result=buffer_report(core);descriptors=fields(core)
    for pc,mnemonic,operand in (
            (0x0110332e,'bl','#0x1126cec'),
            (0x01126cee,'movs','r3, #0x1c'),(0x01126cf0,'subw','r2, pc, #0x287'),
            (0x01126cf6,'movs','r0, #8'),(0x01126cf8,'bl','#0x1102064'),
            (0x01126c0e,'bl','#0x1134c86'),(0x01134c86,'movw','ip, #0xc8c5'),
            (0x01134c8a,'movt','ip, #0x6102'),(0x6102c8c8,'b.w','#0x610835d0'),
            (0x6108365a,'bl','#0x61077afe'),(0x61083666,'bl','#0x61004ff8'),
            (0x610836aa,'sub.w','r8, r0, #3'),(0x610836c8,'strh.w','r0, [r1, #0x144]'),
            (0x610836d0,'bl','#0x61077b08'),(0x610836de,'add.w','r2, r4, #0x144'),
            (0x610836e4,'bl','#0x61077b12'),(0x6108486c,'movs','r0, #0'),
            (0x61004094,'ite','lt'),(0x61004088,'ldr','r1, [r0]'),
            (0x0110ea0e,'add.w','r0, r0, #0x18c'),
            (0x01126d82,'str','r3, [r1, #8]'),(0x01126e20,'b.w','#0x11020c0')):
        expect(core,pc,mnemonic,operand)
    if (read(core,0x01126f24,5)!=b'EFCT\0' or core.u32(0x0110026c)!=HANDLER|1
            or struct.unpack('<h',read(core,0x6108499e+16,2))[0]!=139
            or core.u32(0x011023c8)!=0x200848d8):
        raise ValueError('EFCT registration/vector context changed')
    for pc,mnemonic,operand in ((0x0110226e,'add.w','r1, r4, #0x40'),
            (0x01102276,'add.w','r0, r1, #0x40'),
            (0x0110227a,'ldr','r0, [r0, #0x20]'),(0x01102280,'blx','r0')):
        expect(core,pc,mnemonic,operand)
    target=0x6102dcf0+2*struct.unpack('<H',read(core,0x6102dcf0+2*(TYPE+1),2))[0]
    if target!=0x6102f18a:raise ValueError('Factory ID no longer selects FDRV branch')
    result.update(task=dict(id=8,name='EFCT',callback=CALLBACK,irq=139,handler=HANDLER,
        callback_slot=CALLBACK_SLOT,priority_argument=28,priority_byte=0xe0),
        fdrv_factory_id=TYPE,stock_snapshot_count=len(descriptors),buffer_capacity=32,
        live1_descriptors=[dict(field=i,parameter=2844+i,default=descriptors[i][0],
            minimum=descriptors[i][1],maximum=descriptors[i][2],offset=descriptors[i][3])for i in (2,3)],
        producer=PRODUCER,producer_slots=[1,2,3],parameter_store_stride=PARAM_STRIDE,
        parameter_store_base=PARAM_BASE,registered_task_to_setter_route_proved=True,
        irq_arrival_or_preemption_observed=False,hardware_task_execution_verified=False,
        producer_reenables_task5_before_apply=True)
    return result


class ProducerOracle(BufferOracle):
    ENTRIES=(*BufferOracle.ENTRIES,HANDLER,NOTIFY)
    ALGORITHM=TYPE

    def __init__(self,core):
        source=report(core);super().__init__(core);self.checked.update(source)
        self.cpu.mem_map(0x61401000,0x2000,self.uc.UC_PROT_READ|self.uc.UC_PROT_WRITE)
        self.descriptors=fields(core)

    def _parameter_interface(self,wrapper,table,args):
        super()._parameter_interface(wrapper,table,args)
        return OWNER+0x144,22

    def _dispatch_parameter(self,outer,args):
        u=self.cpu
        u.mem_write(OWNER,bytes(0x300));u.mem_write(OWNER+2,b'\x01')
        self.receiver=OWNER+0x34+32*self.slot
        u.mem_write(self.receiver,bytes(u.mem_read(outer,32)))
        u.mem_write(ROOT,struct.pack('<I',OWNER));u.mem_write(DIRTY,bytes(0x40))
        u.mem_write(LATE_FLAGS,bytes(16));u.mem_write(CALLBACK_SLOT,struct.pack('<I',CALLBACK|1))
        for address in (ACTIVITY,INVOCATIONS):u.mem_write(address,bytes(4))
        store=bytearray(PARAM_STRIDE);store[0]=TYPE;store[1]=int(self.enabled)
        for raw,row in zip(self.raw_input,self.descriptors,strict=True):
            struct.pack_into('<H',store,row[3],raw&0xffff)
        u.mem_write(PARAM_BASE+PARAM_STRIDE*(self.slot-1),bytes(store))
        u.mem_write(NOTIFICATION,struct.pack('<BBH',0x21,0x84,self.slot-1))
        self.notifications=[]
        self._run(NOTIFY,registers=(NOTIFICATION,),mode='notify')
        if self.notifications!=['signal8']or self._word(DIRTY+8)!=1<<(self.slot-1):
            raise ValueError('Original notification did not mark and signal the selected producer')
        self.events=[];self.queue_polls=0
        self._run(HANDLER,mode='fdrv')
        wanted=['callback','queue-empty','producer','disable5','enable5','apply','route']
        if ([e[0]for e in self.events]!=wanted or self._word(INVOCATIONS)!=1
                or self._word(ACTIVITY)!=0 or self._word(DIRTY+8)!=0 or self._word(DIRTY+12)!=0):
            raise ValueError('EFCT callback/producer event order or dirty-flag consumption differs')

    def _code(self,u,address,size,_):
        if self.mode=='notify'and address==0x011020c0:
            if u.reg_read(self.arm.UC_ARM_REG_R0)!=8:raise ValueError('Unexpected notification task')
            self.notifications.append('signal8')
            u.reg_write(self.arm.UC_ARM_REG_PC,u.reg_read(self.arm.UC_ARM_REG_LR));return
        if self.mode=='fdrv':
            a=self.arm;r=lambda i:u.reg_read(a.UC_ARM_REG_R0+i)
            if address==CALLBACK:self.events.append(('callback',))
            elif address==0x011269ba:
                self.events.append(('queue-empty',));self.queue_polls+=1
                if self.queue_polls!=1:raise ValueError('Unexpected command-ring polling')
                u.reg_write(a.UC_ARM_REG_R0,0);u.reg_write(a.UC_ARM_REG_PC,u.reg_read(a.UC_ARM_REG_LR));return
            elif address==PRODUCER:
                if (r(0),r(1),r(2),r(3))!=(OWNER,1<<(self.slot-1),0,0):
                    raise ValueError('Unexpected original producer arguments')
                self.events.append(('producer',))
            elif address in (0x011024c2,0x01102494):
                if r(0)!=5:raise ValueError('Unexpected mapped IRQ mask request')
                self.events.append(('disable5'if address==0x011024c2 else'enable5',))
                u.reg_write(a.UC_ARM_REG_PC,u.reg_read(a.UC_ARM_REG_LR));return
            elif address==UPDATE:
                if (r(0),r(1),r(2),r(3))!=(self.receiver,TYPE,OWNER+0x144,22):
                    raise ValueError('Producer did not supply the stock FDRV snapshot')
                actual=struct.unpack('<22h',u.mem_read(OWNER+0x144,44))
                if list(actual)!=self.normalized:raise ValueError('Original descriptor reader differs from fallback model')
                self.events.append(('apply',))
            elif address==0x6102c118:
                if (r(0),r(1),r(2))!=(INTERFACE,self.slot,2 if self.enabled else 1):
                    raise ValueError('Unexpected original post-apply routing request')
                self.events.append(('route',))
                u.reg_write(a.UC_ARM_REG_PC,u.reg_read(a.UC_ARM_REG_LR));return
        super()._code(u,address,size,_)

    def producer(self,previous,values,counter=0,index=1,enabled=True):
        checked_slot(index);checked(counter,index)
        previous,values=shorts(previous),shorts(values)
        if len(previous)!=22 or len(values)!=22 or type(enabled)is not bool:
            raise ValueError('Expected two complete 22-field FDRV snapshots and an explicit enable flag')
        normalized_values=[normalized(v,row)for v,row in zip(values,self.descriptors,strict=True)]
        if any(previous[i]!=normalized_values[i]for i in range(22)if i not in (2,3)):
            raise ValueError('Connected fixture admits changes to live1 fields2/3 only')
        self.slot=index;self.enabled=enabled;self.raw_input=values;self.normalized=normalized_values
        self.raw_state=update_state(initial_state(32,previous+[0]*10),previous+[0]*10)
        self.raw_values=normalized_values+[0]*10
        changed=[i for i in (2,3)if previous[i]!=normalized_values[i]]
        result=self.parameter({2:normalized_values[2],3:normalized_values[3]},changed,counter,index)
        if self._word(self.interface+4)!=22:raise ValueError('Original buffer did not retain stock count22')
        result.update(events=self.events.copy(),normalized_fields=normalized_values,raw_count=22)
        return result


def selfcheck(core):
    oracle=ProducerOracle(core);result=report(core);cases=writes=0
    defaults=[row[0]for row in oracle.descriptors]
    for index in (1,2,3):
        for counter in (0,2):
            for enabled in (False,True):
                for mode in (0,1,2):
                    for cutoff in (20,16000):
                        for changed in ((),(2,),(3,),(2,3)):
                            values=defaults.copy();values[2:4]=mode,cutoff;previous=values.copy()
                            if 2 in changed:previous[2]=(mode+1)%3
                            if 3 in changed:previous[3]=16000 if cutoff==20 else 20
                            row=oracle.producer(previous,values,counter,index,enabled)
                            cases+=1;writes+=len(row['writes'])
    fallback_cases=[]
    for mode,cutoff in ((-1,19),(3,19000),(1,-1),(0,16001)):
        values=defaults.copy();values[2:4]=mode,cutoff;previous=defaults.copy();previous[2:4]=1,1000
        row=oracle.producer(previous,values,index=3)
        fallback_cases.append(dict(raw=[mode,cutoff],normalized=row['normalized_fields'][2:4]))
    result.update(original_registered_route_cases=cases,producer_coefficient_writes=writes,
        descriptor_fallback_cases=fallback_cases,irq_wrapper_body_executed=True,
        original_notification_executed=True,
        command_ring='controlled empty',nvic_helpers='recording callbacks; no NVIC or preemption execution',
        post_apply_routing='recorded, hardware effects excluded',algorithm_change_path_executed=False)
    return result


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--execute-thumb',action='store_true')
    args=parser.parse_args();core=Core1(args.image)
    print(json.dumps(selfcheck(core)if args.execute_thumb else report(core),indent=2))

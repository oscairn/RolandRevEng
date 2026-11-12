"""Assignment queue -> original PRMEdit block receiver -> EFCT/FDRV controls."""
import struct

from fantom_parameter_store_study import (StoreOracle,report as store_report,block_payload,
    VTABLE,CONSTRUCT,BLOCK,FINALIZE,GENERIC_FIELDS)
from fantom_parameter_producer_study import PARAM_STRIDE,checked_slot
from fantom_eqvg_study import SCRATCH

FORWARD,QUEUE_INIT,ASGN_HANDLER,ASGN_CALLBACK=0x0110a5a6,0x0110a4a6,0x011021cc,0x0110a65c
RECEIVERS_INIT,REASSEMBLE,DISPATCH=0x0110bbc8,0x0110ac78,0x0110ad92
EDIT,EDIT_VTABLE,QUEUE,WORD_INPUT=0x20089ad4,0x61179ae8,0x2008044c,SCRATCH+0xa000
ASGN_SLOT,ASGN_ACTIVITY,ASGN_COUNT=0x2008496c,0x200848ec,0x200848ac


def parameter_words(part,changes):
    """Original authored kind3 words; not a host ttyGS0 frame or device command."""
    if type(part)is not int or not 0<=part<=2:raise ValueError('Expected local MFX part0..2')
    payload=bytes((0x84,part,0))+block_payload(changes)
    words=[]
    for offset in range(0,len(payload),3):
        group=payload[offset:offset+3]
        tag=0x34 if offset+3<len(payload)else 0x34+len(group)
        words.append(int.from_bytes((bytes((tag,))+group).ljust(4,b'\0'),'little'))
    return words


def checked_cursor(cursor):
    if type(cursor)is not int or not 0<=cursor<2048:raise ValueError('Expected an empty assignment-ring cursor0..2047')
    return cursor


def report(core):
    from core1_rtti import trace
    from core1_task_context_study import report as task_report
    from dramio_owner_study import expect
    from kernel_abi import read
    result=store_report(core);tasks=task_report(core)
    rows=trace(core,'14CUMDWRxPRMEdit')['candidates']
    if (len(rows)!=1 or rows[0]['vtable']+8!=EDIT_VTABLE
            or [core.u32(EDIT_VTABLE+i)for i in (0,4)]!=[REASSEMBLE|1,DISPATCH|1]):
        raise ValueError('Original PRMEdit receiver changed')
    for pc,mnemonic,operand in (
            (0x0110a5c4,'ldr','r0, [r4]'),(0x0110a5c6,'bl','#0x110a390'),
            (0x0110a6c8,'bl','#0x110ac78'),(0x0110af08,'bl','#0x1134574'),
            (0x0110af0c,'movs','r1, #0'),(0x0110af10,'bl','#0x113457e'),
            (0x0110ad02,'mov','r0, r4'),(0x0110ad04,'blx','r3'),
            (0x0110bbd8,'str','r0, [r4]'),(0x0111ebc8,'bl','#0x110a5a6'),
            (0x0110a756,'str.w','r1, [r2, #0x100]')):
        expect(core,pc,mnemonic,operand)
    if (core.u32(0x0110bbf4)!=EDIT or core.u32(0x0110bbfc)!=EDIT_VTABLE
            or core.u32(0x0110b244)!=VTABLE
            or 0x0110adb4+2*read(core,0x0110adb8,1)[0]!=0x0110aef6
            or core.u32(0x011003e4)!=ASGN_HANDLER|1):
        raise ValueError('Stream selection/initialization or ASGN vector changed')
    task=next(t for t in tasks['tasks']if t['id']==5)
    if task['callback_thumb']!=ASGN_CALLBACK|1 or task['callback_slot']!=ASGN_SLOT:
        raise ValueError('ASGN callback binding changed')
    ui=trace(core,'18CEZSNDTonePrmSFSub')['candidates']
    if (len(ui)!=1 or ui[0]['vtable']+8!=0x6117b010
            or core.u32(0x6117b024)!=0x61080ac5 or core.u32(0x6117b02c)!=0x61080abd
            or core.u32(0x61080ad0)!=0x20081980):
        raise ValueError('Separate scalar/UI adapter RTTI binding changed')
    result.update(edit_rtti='CUMDWRxPRMEdit',edit_receiver=EDIT,edit_vtable=EDIT_VTABLE,
        assignment_input=FORWARD,assignment_handler=ASGN_HANDLER,assignment_callback=ASGN_CALLBACK,
        assignment_irq=233,reassembler=REASSEMBLE,stream_dispatcher=DISPATCH,
        stream_selector=0x84,fragment_header_high_nibble=3,continuation_tag=0x34,
        terminal_tags=[0x35,0x36,0x37],receiver_header_bytes=3,
        receive_path_passes_serialization_false=True,global_serialization_flag_required=False,
        rxdt_kind3_forward_edge_source_checked=True,full_rxdt_or_ingress_irq_executed=False,
        host_wire_bridge_proved=False,scalar_adapter_rtti='CEZSNDTonePrmSFSub',
        scalar_adapter_vtable=0x6117b010,global_serialization_flag_runtime_proved=False)
    return result


class StreamOracle(StoreOracle):
    ENTRIES=(*StoreOracle.ENTRIES,FORWARD,QUEUE_INIT,ASGN_HANDLER,RECEIVERS_INIT)
    WRITE_MODES=(*StoreOracle.WRITE_MODES,'stream')

    def __init__(self,core):
        source=report(core);super().__init__(core);self.checked.update(source)

    def _write_store_and_notify(self,address,store):
        u=self.cpu;before=bytearray(store);self.store_address=address
        for value,row in zip(self.previous,self.descriptors,strict=True):
            struct.pack_into('<H',before,row[3],value&0xffff)
        u.mem_write(address,bytes(before))
        self.allowed_bytes={address+16+2*field+k for field,_ in self.changes for k in (0,1)}
        self.notifications=[];self.messages=[];self.input_signals=[];self.epilogue=[]
        self.reassembled_words=[];self.dispatched=0
        self.incoming_words=parameter_words(self.slot-1,self.scalar_sources)
        self.expected_payload=bytes((0x84,self.slot-1,0))+block_payload(self.scalar_sources)
        u.mem_write(0x20081980,b'\x80')
        u.mem_write(QUEUE,bytes(0x40))
        self._run(QUEUE_INIT,mode='stream');self._run(RECEIVERS_INIT,mode='stream')
        u.mem_write(QUEUE,struct.pack('<II',self.cursor,self.cursor))
        u.mem_write(ASGN_SLOT,struct.pack('<I',ASGN_CALLBACK|1))
        for a in (ASGN_ACTIVITY,ASGN_COUNT):u.mem_write(a,bytes(4))
        for word in self.incoming_words:
            u.mem_write(WORD_INPUT,struct.pack('<I',word))
            self._run(FORWARD,registers=(WORD_INPUT,),mode='stream')
        # The original forwarder must copy words; no caller-owned input storage survives.
        u.mem_write(WORD_INPUT,struct.pack('<I',0xdeadbeef))
        self._run(ASGN_HANDLER,mode='stream')
        cursor=(self.cursor+len(self.incoming_words))&2047
        if (self.input_signals!=[5]*len(self.incoming_words)or self.dispatched!=1
                or self.reassembled_words!=self.incoming_words
                or (self._word(QUEUE),self._word(QUEUE+4),self._word(QUEUE+8))!=(cursor,cursor,0)
                or self._word(ASGN_COUNT)!=1 or self._word(ASGN_ACTIVITY)!=0
                or self.epilogue!=['enable3','enable_irq6']):
            raise ValueError('Original assignment-copy/queue/handler path differs')
        if bytes(u.mem_read(address,PARAM_STRIDE))!=store:
            raise ValueError('Original receive-side block writes differ from the low16 model')
        count=struct.unpack('<H',u.mem_read(EDIT+0x208,2))[0]
        if count!=len(self.expected_payload)or bytes(u.mem_read(EDIT+8,count))!=self.expected_payload:
            raise ValueError('Original receiver did not retain the exact assembled payload')
        dirty_ids=[GENERIC_FIELDS+field for field,_ in self.changes]
        wanted=[0x9f,0x84]if dirty_ids and min(dirty_ids)==max(dirty_ids)else[0x84]
        if ([m[0]for m in self.messages]!=[0x21]*len(wanted)
                or [m[1]for m in self.messages]!=wanted
                or self.notifications!=['signal8']*len(wanted)):
            raise ValueError('Original receive-side finalization differs')

    def _code(self,u,address,size,_):
        if self.mode=='stream':
            a=self.arm;r=lambda i:u.reg_read(a.UC_ARM_REG_R0+i)
            if address==0x011020c0 and r(0)==5:
                self.input_signals.append(5)
                u.reg_write(a.UC_ARM_REG_PC,u.reg_read(a.UC_ARM_REG_LR));return
            if address==0x01102494:
                if r(0)!=3:raise ValueError('Unexpected ASGN epilogue task')
                self.epilogue.append('enable3')
                u.reg_write(a.UC_ARM_REG_PC,u.reg_read(a.UC_ARM_REG_LR));return
            if address==0x0110a756:
                if r(1)!=0x40 or r(2)+0x100!=0xe000e100:raise ValueError('Unexpected ingress IRQ enable store')
                self.epilogue.append('enable_irq6')
                u.reg_write(a.UC_ARM_REG_PC,(address+size)|1);return
            if address==REASSEMBLE:
                if r(0)!=EDIT:raise ValueError('Unexpected parameter-edit receiver')
                self.reassembled_words.append(r(1))
            elif address==DISPATCH:
                if r(1)!=EDIT+8 or r(2)!=len(self.expected_payload):raise ValueError('Unexpected assembled dispatch buffer/count')
                self.dispatched+=1
            elif address==CONSTRUCT:self.writer_object=r(0)
            elif address==BLOCK:
                if (r(0)!=self.writer_object or self._word(r(0))!=VTABLE
                        or self._word(r(0)+0xc)!=self.store_address
                        or r(1)!=EDIT+11 or r(2)!=len(self.expected_payload)-3):
                    raise ValueError('Original selector did not bind the expected MFX stream')
            elif address==FINALIZE:
                ids=[GENERIC_FIELDS+field for field,_ in self.changes]
                wanted=(min(ids),max(ids))if ids else(32767,0)
                if r(0)!=self.writer_object or r(1)!=0 or struct.unpack('<hh',u.mem_read(r(0)+0x10,4))!=wanted:
                    raise ValueError('Original receiver finalizer arguments/dirty range differ')
                # The receiver's stream object is on its stack and expires on return.
                self.dirty_range=wanted
        super()._code(u,address,size,_)

    def stream_controls(self,previous,changes,counter=0,index=1,enabled=True,cursor=0):
        self.cursor=checked_cursor(cursor);checked_slot(index)
        row=self.write_controls(previous,changes,counter,index,enabled,form='block')
        row.update(assignment_words=len(self.incoming_words),assignment_cursor=self._word(QUEUE))
        return row


def selfcheck(core):
    oracle=StreamOracle(core);result=report(core);cases=writes=words=notifications=0
    defaults=[row[0]for row in oracle.descriptors]
    for cursor in (0,2047):
        for index in (1,2,3):
            for counter in (0,2):
                for enabled in (False,True):
                    for mode in (0,1,2):
                        for cutoff in (20,16000):
                            for changed in ((),(2,),(3,),(2,3)):
                                previous=defaults.copy();previous[2:4]=mode,cutoff
                                if 2 in changed:previous[2]=(mode+1)%3
                                if 3 in changed:previous[3]=16000 if cutoff==20 else 20
                                changes=[(i,mode if i==2 else cutoff)for i in changed]
                                row=oracle.stream_controls(previous,changes,counter,index,enabled,cursor)
                                cases+=1;writes+=len(row['writes']);words+=row['assignment_words']
                                notifications+=row['notification_count']
    boundary=oracle.stream_controls(defaults,[(3,65535)],index=3,cursor=2047)
    result.update(original_stream_route_cases=cases,stream_coefficient_writes=writes,
        incoming_assignment_words=words,stream_notifications=notifications,
        original_assignment_queue_and_receiver_executed=True,
        incoming_input_storage_overwritten_before_consume=True,assignment_wrap_cursors=[0,2047],
        assignment_nvic_epilogue='recorded; helpers/store effects excluded',
        task_arrivals_or_preemption_observed=False,serialization_flag_canary=0x80,
        all_ones_cutoff_normalized=boundary['normalized_fields'][3])
    return result


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--execute-thumb',action='store_true')
    args=parser.parse_args();core=Core1(args.image)
    print(json.dumps(selfcheck(core)if args.execute_thumb else report(core),indent=2))

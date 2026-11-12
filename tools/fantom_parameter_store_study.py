"""Original stream writes/finalization connected to the bounded EFCT/FDRV route."""
import struct

from fantom_parameter_producer_study import (ProducerOracle,report as producer_report,
    NOTIFY,PARAM_BASE,PARAM_STRIDE,checked_slot)
from fantom_parameter_buffer_study import shorts
from fantom_envelope_mode_study import checked
from fantom_eqvg_study import SCRATCH,STACK

VTABLE,CONSTRUCT,SCALAR,BLOCK,FINALIZE=0x6117958c,0x61004ff8,0x610050b6,0x610050ca,0x61005034
OBJECT,PAYLOAD=SCRATCH+0x6000,SCRATCH+0x7000
STREAM_BASE,GENERIC_FIELDS=0x587,0x597


def stored_short(value):
    if type(value)is not int or not -0x80000000<=value<=0x7fffffff:
        raise ValueError('Expected an explicit signed32 scalar source')
    return struct.unpack('<h',struct.pack('<H',value&0xffff))[0]


def control_writes(changes,form):
    if (form not in ('scalar','block')or not isinstance(changes,(list,tuple))or len(changes)>2
            or any(not isinstance(row,(list,tuple))or len(row)!=2
                or type(row[0])is not int or row[0]not in (2,3)for row in changes)):
        raise ValueError('Expected at most two checked live1 writes and scalar/block form')
    result=[(field,stored_short(value))for field,value in changes]
    if form=='block'and any(b[0]!=a[0]+1 for a,b in zip(result,result[1:])):
        raise ValueError('A block must contain complete consecutive fields in increasing order')
    return result


def block_payload(changes):
    changes=control_writes(changes,'block');first=changes[0][0]if changes else 2
    return struct.pack('<H',GENERIC_FIELDS+first-STREAM_BASE)+b''.join(struct.pack('<h',v)for _,v in changes)


def report(core):
    from core1_rtti import trace
    from dramio_owner_study import expect
    from kernel_abi import read
    result=producer_report(core)
    rows=trace(core,'14CMUSE_PrmStmSF')['candidates']
    if len(rows)!=1 or rows[0]['vtable']+8!=VTABLE:
        raise ValueError('Original MFX stream class changed')
    if [core.u32(VTABLE+i)for i in (0,4,8)]!=[0x01135e7f,0x01135e79,0x01135e75]:
        raise ValueError('Original stream bounds/size vtable changed')
    for pc,mnemonic,operand in (
            (0x610050c6,'b.w','#0x610040aa'),(0x610040b2,'mov','r6, r1'),
            (0x610040b4,'mov','r5, r2'),(0x610040de,'strh','r6, [r1, r0]'),
            (0x610040f2,'strh','r0, [r4, #0x10]'),(0x610040fe,'strh','r5, [r4, #0x12]'),
            (0x610050ce,'bl','#0x61004104'),(0x61004116,'orr.w','r5, r0, r2, lsl #8'),
            (0x61005080,'bne','#0x61005096'),(0x61005098,'bl','#0x61076c44'),
            (0x61076c44,'movw','ip, #0x6d2f'),(0x61076c48,'movt','ip, #0x112'),
            (0x610050ae,'bl','#0x6100447a')):
        expect(core,pc,mnemonic,operand)
    for i in (2,3):
        row=struct.unpack('<5i',read(core,0x611616b8+20*(GENERIC_FIELDS+i),20))
        if row!=(0,-20000,20000,16+2*i,2):raise ValueError('Generic live1 stream descriptor changed')
    result.update(stream_rtti='CMUSE_PrmStmSF',stream_vtable=VTABLE,
        scalar_write=SCALAR,block_write=BLOCK,finalize=FINALIZE,
        generic_live1_parameter_ids=[GENERIC_FIELDS+i for i in (2,3)],
        typed_live1_parameter_ids=[2844+i for i in (2,3)],
        writer_validates_value_range=False,writer_retains_low16_bits=True,
        single_field_notification=0x9f,finalizer_resets_dirty_range=False,
        finalizer_reserved_word_mask=0x1fc0,host_wire_bridge_proved=False)
    return result


class StoreOracle(ProducerOracle):
    ENTRIES=(*ProducerOracle.ENTRIES,CONSTRUCT,SCALAR,BLOCK,FINALIZE)

    def __init__(self,core):
        source=report(core);super().__init__(core);self.checked.update(source)

    def _write(self,u,access,address,size,value,_):
        if self.mode=='store'and PARAM_BASE<=address<PARAM_BASE+3*PARAM_STRIDE:
            if not all(byte in self.allowed_bytes for byte in range(address,address+size)):
                raise ValueError('Original writer touched an unrequested parameter byte')
            self.writes.append((self.pc,address,size,value));return
        super()._write(u,access,address,size,value,_)

    def _code(self,u,address,size,_):
        if self.mode=='store':
            if address==NOTIFY:
                self.messages.append(bytes(u.mem_read(u.reg_read(self.arm.UC_ARM_REG_R0),4)))
            elif address==0x011020c0:
                if u.reg_read(self.arm.UC_ARM_REG_R0)!=8:raise ValueError('Unexpected finalizer task signal')
                self.notifications.append('signal8')
                u.reg_write(self.arm.UC_ARM_REG_PC,u.reg_read(self.arm.UC_ARM_REG_LR));return
            elif address==0x6100447a:raise ValueError('Optional external serialization is excluded')
        super()._code(u,address,size,_)

    def _write_store_and_notify(self,address,store):
        u=self.cpu;before=bytearray(store)
        for value,row in zip(self.previous,self.descriptors,strict=True):
            struct.pack_into('<H',before,row[3],value&0xffff)
        u.mem_write(address,bytes(before));u.mem_write(OBJECT,struct.pack('<I',VTABLE)+bytes(24))
        self.allowed_bytes={address+16+2*field+k for field,_ in self.changes for k in (0,1)}
        self.notifications=[];self.messages=[]
        self._run(CONSTRUCT,registers=(OBJECT,self.slot-1),mode='store')
        if self._word(OBJECT+0xc)!=address:raise ValueError('Stream constructor chose another part store')
        if self.form=='scalar':
            for field,value in self.scalar_sources:
                self._run(SCALAR,registers=(OBJECT,value&0xffffffff,GENERIC_FIELDS+field),mode='store')
        else:
            payload=block_payload(self.scalar_sources);u.mem_write(PAYLOAD,payload)
            self._run(BLOCK,registers=(OBJECT,PAYLOAD,len(payload)),mode='store')
        if bytes(u.mem_read(address,PARAM_STRIDE))!=store:
            raise ValueError('Original stream writes differ from low16-bit store model')
        ids=[GENERIC_FIELDS+field for field,_ in self.changes]
        dirty=(min(ids),max(ids))if ids else(32767,0)
        if struct.unpack('<hh',u.mem_read(OBJECT+0x10,4))!=dirty:
            raise ValueError('Original writer dirty range differs')
        # Seed the finalizer's uninitialized stack slots so reserved bits cannot look zero by accident.
        u.mem_write(STACK-24,b'\x5a'*12)
        self._run(FINALIZE,registers=(OBJECT,0),mode='store')
        wanted=[0x9f,0x84]if dirty[0]==dirty[1]else[0x84]
        if ([m[0]for m in self.messages]!=[0x21]*len(wanted)
                or [m[1]for m in self.messages]!=wanted
                or self.notifications!=['signal8']*len(wanted)):
            raise ValueError('Original finalizer notification sequence differs')
        if dirty[0]==dirty[1]and struct.unpack_from('<H',self.messages[0],2)[0]!=dirty[0]:
            raise ValueError('Single-field notification ID differs')
        word=struct.unpack_from('<H',self.messages[-1],2)[0]
        if word&~0x1fc0!=self.slot-1:raise ValueError('Finalizer part/type flag fields differ')
        if word&0x1fc0!=0x5a5a&0x1fc0:raise ValueError('Reserved notification bits no longer retain prior stack contents')
        if struct.unpack('<hh',u.mem_read(OBJECT+0x10,4))!=dirty:
            raise ValueError('Finalizer unexpectedly reset the dirty range')

    def write_controls(self,previous,changes,counter=0,index=1,enabled=True,form='scalar'):
        checked_slot(index);checked(counter,index)
        previous=shorts(previous);prepared=control_writes(changes,form)
        if len(previous)!=22 or type(enabled)is not bool:
            raise ValueError('Expected a complete previous FDRV snapshot and explicit enable flag')
        values=previous.copy()
        for field,value in prepared:values[field]=value
        self.previous=previous;self.changes=prepared;self.scalar_sources=list(changes);self.form=form
        result=self.producer(previous,values,counter,index,enabled)
        result.update(notification_count=len(self.messages),written_range=struct.unpack('<hh',self.cpu.mem_read(OBJECT+0x10,4)))
        return result


def selfcheck(core):
    oracle=StoreOracle(core);result=report(core);cases=writes=notifications=0
    defaults=[row[0]for row in oracle.descriptors]
    for index in (1,2,3):
        for counter in (0,2):
            for enabled in (False,True):
                for form in ('scalar','block'):
                    for mode in (0,1,2):
                        for cutoff in (20,16000):
                            for changed in ((),(2,),(3,),(2,3)):
                                previous=defaults.copy();previous[2:4]=mode,cutoff
                                if 2 in changed:previous[2]=(mode+1)%3
                                if 3 in changed:previous[3]=16000 if cutoff==20 else 20
                                changes=[(i,mode if i==2 else cutoff)for i in changed]
                                row=oracle.write_controls(previous,changes,counter,index,enabled,form)
                                cases+=1;writes+=len(row['writes']);notifications+=row['notification_count']
    boundaries=[]
    for form in ('scalar','block'):
        for field,value in ((2,65537),(2,65539),(3,66536),(3,65535)):
            row=oracle.write_controls(defaults,[(field,value)],form=form)
            boundaries.append(dict(form=form,field=field,input=value,stored=stored_short(value),
                normalized=row['normalized_fields'][field]))
    same=oracle.write_controls(defaults,[(2,2),(2,2)])
    result.update(original_write_route_cases=cases,writer_coefficient_writes=writes,
        original_finalizer_notifications=notifications,low16_boundary_cases=boundaries,
        same_value_notifications=same['notification_count'],same_value_coefficient_writes=len(same['writes']),
        original_store_constructor_writer_finalizer_executed=True,optional_external_serialization_executed=False)
    return result


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--execute-thumb',action='store_true')
    args=parser.parse_args();core=Core1(args.image)
    print(json.dumps(selfcheck(core)if args.execute_thumb else report(core),indent=2))

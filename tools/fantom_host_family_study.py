"""Original host MFX callbacks and paired block/range messages; no peer emulation."""
import struct

from fantom_host_block_study import (HostImage,HostBlockOracle,report as host_report,
    RAM,OBJECT,HEAP,SERIALIZE,SINK)
from fantom_parameter_store_study import report as core_report
from kernel_abi import read

CFF,TABLE,DESCRIPTORS=0x424be78,0x13844c8,0x138b3d0
HOST_BASE,CORE_BASE,HOST_TYPED,CORE_TYPED=3486,0x587,4911,2840
STATUS=RAM+0x9000
PLACEMENTS=((6,0,0x424ce9c,0xc08858),(7,0,0x424cef0,0xc08a68),(7,1,0x424cf44,0xc08a68))
EXTRA_CODE=((0xc00000,0xc03000),(0xc07000,0xc09000),(0xc1a000,0xc1d000))


def descriptor(image,index):
    row=struct.unpack('<3iHBB',image.read(DESCRIPTORS+16*index,16))
    return row[:4]+(row[4]&15,)


def checked_range(first,last):
    if (type(first)is not int or type(last)is not int or first>last
            or not ((3504<=first<=last<=3505)or(4917<=first<=last<=4918)
                    or(first,last)==(3486,3533))):
        raise ValueError('Expected checked generic/typed live1 fields or full generic MFX range')


def notification_bytes(family,index,context,first,last):
    checked_range(first,last)
    if (type(family)is not int or family not in (6,7)
            or type(index)is not int or not 0<=index<=65535
            or type(context)is not int or not 0<=context<=255):
        raise ValueError('Expected explicit family6/7, unsigned16 index and unsigned8 context')
    lo,hi=first-HOST_BASE,last-HOST_BASE
    header=family|((index&0x3fff)<<10)|(context<<24)
    return struct.pack('<I',header)+bytes(((lo>>4)&255,(hi>>4)&255,(lo&15)|((hi&15)<<4)))


def report(image,core):
    import capstone
    result=host_report(image);core_report(core)
    for host_start,core_start,count in ((HOST_BASE,CORE_BASE,48),(HOST_TYPED,CORE_TYPED,26)):
        for i in range(count):
            original=struct.unpack('<5i',read(core,0x611616b8+20*(core_start+i),20))
            if descriptor(image,host_start+i)!=original:raise ValueError('Host/CORE1 descriptor correspondence changed')
    if struct.unpack('<HH',image.read(0x1613b40+85*4,4))!=(4911,4936):
        raise ValueError('Host FDRV algorithm range changed')
    for family,_,_,callback in PLACEMENTS:
        row=struct.unpack('<3Q4H',image.read(0x1384698+family*32,32))
        if row[0]!=(0xc00538 if family==6 else 0xc00548)or row[2]!=callback or row[3]!=0x3d:
            raise ValueError('Host MFX getter/callback registration changed')
    md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
    anchors={0xc1aa60:('ldp','x2, x3, [x1]'),0xc07f64:('bl','#0xc1aa60'),
        0xc00550:('mov','w2, #0x54'),0xc08954:('bl','#0xc02010'),0xc08b64:('bl','#0xc02010'),
        0xbe3f60:('bfxil','w6, w21, #0, #0xa'),0xbe3f6c:('bfi','w6, w2, #0xa, #0xe'),
        0xbe2c24:('bl','#0xbe3450'),0xbe43a4:('adrp','x0, #0x4114000')}
    for pc,expected in anchors.items():
        row=list(md.disasm(image.read(pc,4),pc))
        if len(row)!=1 or(row[0].mnemonic,row[0].op_str)!=expected:raise ValueError(f'Family anchor changed at {pc:#x}')
    result.update(host_generic_base=HOST_BASE,core1_generic_base=CORE_BASE,
        matching_generic_descriptors=48,matching_fdrv_typed_descriptors=26,id_shift=2071,
        host_live1_generic_ids=[3504,3505],host_live1_typed_ids=[4917,4918],
        host_store_addresses=[p[2]for p in PLACEMENTS],core1_slot_assignment_proved=False,
        full_range_flag_mask=1,send_flag_mask=2,notification_index_bits=14)
    return result


class FamilyOracle(HostBlockOracle):
    def __init__(self,image,core):
        source=report(image,core);super().__init__(image);self.checked.update(source)
        import unicorn
        self.image=image;u=self.cpu
        for start,end in EXTRA_CODE:
            u.mem_map(start,end-start);u.mem_write(start,image.read(start,end-start))
            u.mem_protect(start,end-start,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        for start,size in ((0x1384000,0x1c000),(0x1613000,0x1000)):
            u.mem_map(start,size);u.mem_write(start,image.read(start,size));u.mem_protect(start,size,unicorn.UC_PROT_READ)
        u.mem_map(0x424b000,0x3000)
        self._run(0xc1aa60,CFF,TABLE)

    def _code(self,u,pc,size,_):
        a=self.arm;r=lambda i:u.reg_read(getattr(a,f'UC_ARM64_REG_X{i}'))
        result=None
        if pc in (0x40ca10,0x40c690):
            if r(0)!=0x424cbd8:raise ValueError('Unexpected family mutex')
            self.locks.append('lock'if pc==0x40ca10 else'unlock');result=0
        elif pc in (0xbdf9b8,0xbdfa08):
            pointer=r(0)
            if pointer not in (HEAP,0x412efb0):raise ValueError('Unexpected retained allocation')
            value=struct.unpack('<I',u.mem_read(pointer,4))[0]+(1 if pc==0xbdf9b8 else-1)
            if not 0<=value<=3:raise ValueError('Unexpected reference count')
            u.mem_write(pointer,struct.pack('<I',value));self.refcalls+=1;result=value
        elif pc==0x40b0e0:
            if r(0)!=HEAP or struct.unpack('<I',u.mem_read(HEAP,4))[0]!=0:raise ValueError('Unexpected free')
            u.mem_write(HEAP,b'\xdd'*(self.length+8));self.frees+=1;result=0
        elif pc==0xbe26a8:
            if r(0)!=0x41145e0:raise ValueError('Unexpected output queue object')
            native=bytes(u.mem_read(r(1),24));kind=native[0]>>1
            if native[2]!=0xef or kind not in (7,8):raise ValueError('Unexpected routed message')
            payload=b''
            if native[0]&1:
                pointer=struct.unpack_from('<Q',native,8)[0]
                if pointer!=HEAP:raise ValueError('Unexpected queued allocation')
                length=struct.unpack('<I',u.mem_read(pointer+4,4))[0]
                if length!=self.length:raise ValueError('Unexpected queued length')
                payload=bytes(u.mem_read(pointer+8,length))
            self.queued.append((native,payload));result=0
        elif any(start<=pc<end for start,end in EXTRA_CODE):return
        else:return super()._code(u,pc,size,_)
        u.reg_write(a.UC_ARM64_REG_X0,result);u.reg_write(a.UC_ARM64_REG_PC,r(30))

    def callback(self,placement,index,first,last,flags=3,force_full=False,canary=0x5a):
        checked_range(first,last)
        if (type(placement)is not int or not 0<=placement<3 or type(index)is not int or not 0<=index<=65535
                or type(flags)is not int or flags not in (0,1,2,3)or type(force_full)is not bool
                or type(canary)is not int or not 0<=canary<=255):raise ValueError('Expected checked family callback arguments')
        family,context,address,entry=PLACEMENTS[placement];u=self.cpu
        store=bytearray(84)
        for i in range(48):
            default,_,_,offset,width=descriptor(self.image,HOST_BASE+i)
            store[offset:offset+width]=int(default&((1<<(8*width))-1)).to_bytes(width,'little')
        store[0]=85;struct.pack_into('<HH',store,20,1,1000)
        u.mem_write(address,bytes(store));u.mem_write(STATUS,struct.pack('<HBBHH',int(force_full),0,flags,0,0))
        u.mem_write(RAM+0x10000,bytes((canary,))*0xf000)
        u.mem_write(0x412efb0,struct.pack('<I',1))
        self.queued=[];self.locks=[];self.refcalls=self.frees=0;self.allocations=[];self.chunks=[]
        selected=(HOST_BASE,HOST_BASE+47)if force_full or flags&1 else(first,last)
        start=descriptor(self.image,selected[0])[3];last_desc=descriptor(self.image,selected[1])
        self.length=last_desc[3]+last_desc[4]-start
        self._run(entry,index,context,first,last,STATUS)
        converted=tuple({4917:3504,4918:3505}.get(i,i)for i in selected)
        status=struct.unpack('<HH',u.mem_read(STATUS+4,4))
        if (status!=converted or self.locks!=['lock','unlock']or bytes(u.mem_read(address,84))!=store
                or struct.unpack('<I',u.mem_read(0x424cc08,4))[0]!=0):
            raise ValueError(f'Family bookkeeping differs: args={(placement,index,first,last,flags)}, status={status}, expected={converted}, locks={self.locks}, store_equal={bytes(u.mem_read(address,84))==store}')
        if len(self.queued)!=(2 if flags&2 else 0):raise ValueError('Original paired route count differs')
        variable=bool(flags&2 and self.length>3)
        if (self.allocations!=([self.length+8]if variable else[])or self.frees!=int(variable)
                or struct.unpack('<I',u.mem_read(0x412efb0,4))[0]!=1):
            raise ValueError('Original temporary message ownership differs')
        wires=[]
        for native,payload in self.queued:
            u.mem_write(OBJECT,native)
            if payload:u.mem_write(HEAP,struct.pack('<II',1,len(payload))+payload)
            self.chunks=[];self._run(SERIALIZE,SINK,OBJECT);wires.append(b''.join(self.chunks))
        if wires:
            from bmc_ipc import frames
            block,=frames(wires[0]);notification,=frames(wires[1])
            expected=dict(u16=index,byte2=context,byte3=start,data=store[start:start+self.length].hex())
            if (block['kind']!=7 or block['selector']!=family or block['block']!=expected
                    or notification['kind']!=8 or bytes.fromhex(notification['payload'])!=notification_bytes(family,index,context,*selected)):
                raise ValueError('Original family block/range pair differs from independent layout')
        return dict(messages=len(wires),block_bytes=self.length if wires else 0,
            converted_range=list(status),range_ids=list(selected),mutex_calls=len(self.locks))


def selfcheck(image,core):
    oracle=FamilyOracle(image,core);cases=messages=payload_bytes=0
    ranges=((3504,3504),(3505,3505),(3504,3505),(4917,4917),(4918,4918),(4917,4918))
    for placement in range(3):
        for index in (0,65535):
            for canary in (0,0x5a,255):
                for first,last in ranges:
                    for flags in (0,1,2,3):
                        row=oracle.callback(placement,index,first,last,flags,canary=canary)
                        cases+=1;messages+=row['messages'];payload_bytes+=row['block_bytes']
    for placement in range(3):
        oracle.callback(placement,0,4917,4918,flags=2,force_full=True)
    return dict(oracle.checked,original_family_callback_cases=cases,paired_message_count=messages,
        copied_block_data_bytes=payload_bytes,forced_full_range_cases=3,
        original_getters_router_and_temporary_destruction_executed=True,
        output_queue_storage_and_mutex_effects_intercepted=True,host_to_core1_translation_proved=False)


if __name__=='__main__':
    import argparse,json
    from core1 import Core1
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('host');parser.add_argument('core1')
    parser.add_argument('--execute-arm64',action='store_true');args=parser.parse_args()
    from pathlib import Path
    image=HostImage(Path(args.host).read_bytes());core=Core1(args.core1)
    print(json.dumps(selfcheck(image,core)if args.execute_arm64 else report(image,core),indent=2))

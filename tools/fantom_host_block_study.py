"""Replay the pinned Fantom Linux kind-7 constructor/serializer in an isolated CPU."""
import hashlib
import io
import struct
from pathlib import Path

from qctest_shell_study import direct_callers

HOST_SHA256='90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7'
CONSTRUCT,SERIALIZE=0xbe3e38,0xbe1120
RAM,STOP=0x20000000,0x10000000
OBJECT,INPUT,HEAP,SINK,VTABLE=RAM+0x1000,RAM+0x2000,RAM+0x4000,RAM+0x800,RAM+0x900
CALLBACK=STOP+4
CALLERS=(0xc01f34,0xc0209c,0xc04cec,0xc0dc38,0xc0df78,0xc11510,0xc119e0,
    0xc12a30,0xc12a8c,0xc13840,0xc138a0,0xc1712c,0xc196b0,0xc19ed8,0xc1d754,
    0xc1dc48,0xc1dce8,0xc1f988,0xc1fa0c,0xc1fa78,0xc1fae4,0xc1fb50,0xc1fd4c,
    0xc1fef8,0xc1ff74,0xc1fff0,0xc20068,0xc201f8,0xc20268,0xc202d8,0xc20344,
    0xc204e0,0xc20558,0xc205d0,0xc20644,0xc26b28,0xc26b84)


class HostImage:
    def __init__(self,data):
        if hashlib.sha256(data).hexdigest()!=HOST_SHA256:
            raise ValueError('Expected pinned Fantom-0 v1.08 mi078 ELF')
        from elftools.elf.elffile import ELFFile
        self.data=data;self.elf=ELFFile(io.BytesIO(data))
        self.segments=[s for s in self.elf.iter_segments()if s['p_type']=='PT_LOAD']

    def read(self,address,size):
        for s in self.segments:
            start=s['p_vaddr']
            if start<=address and address+size<=start+s['p_filesz']:
                offset=s['p_offset']+address-start
                return self.data[offset:offset+size]
        raise ValueError('Requested host range is not file-backed')


def report(image):
    import capstone
    md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
    checks={0xbe3120:('str','wzr, [x0]'),0xbe3124:('strb','wzr, [x0, #0xb]'),
        0xbe3e70:('strb','w25, [x19, #3]'),0xbe3e7c:('cmp','w20, #3'),
        0xbe3ea0:('bl','#0xbe3758'),0xbe3eb4:('bl','#0xbe3528'),
        0xbe3eec:('add','x1, sp, #0x58'),0xbe3ef0:('add','w2, w20, #4'),
        0xbe375c:('str','w1, [x0, #0x10]'),0xbe35d0:('strb','w20, [x19, #0xb]'),
        0xbe357c:('bl','#0x40c350'),0xbe3594:('stp','w3, w20, [x2]'),
        0xbe1144:('mov','w2, #8'),0xbe1150:('add','x1, x20, #0x10'),
        0xbe1154:('mov','w2, #4'),0xbe1174:('mov','w2, #4'),
        0xbe11b4:('mov','w2, #0xc'),0xc01f4c:('bl','#0xbe4270'),
        0xc01f78:('bl','#0xbe3f30'),0xc020e0:('bl','#0xbe3f30')}
    for pc,expected in checks.items():
        rows=list(md.disasm(image.read(pc,4),pc))
        if len(rows)!=1 or (rows[0].mnemonic,rows[0].op_str)!=expected:
            raise ValueError(f'Host block anchor changed at {pc:#x}')
    text=image.elf.get_section_by_name('.text')
    callers=direct_callers(text.data(),text['sh_addr'],CONSTRUCT)
    if tuple(callers)!=CALLERS:raise ValueError('Direct kind-7 constructor caller set changed')
    symbols=image.elf.get_section_by_name('.dynsym')
    plt=image.elf.get_section_by_name('.plt')['sh_addr']
    imports={plt+32+16*i:symbols.get_symbol(r['r_info_sym']).name for i,r in
        enumerate(image.elf.get_section_by_name('.rela.plt').iter_relocations())}
    if [imports.get(pc)for pc in (0x40b2c0,0x40c350)]!=['memcpy','_Znam']:
        raise ValueError('Host copy/allocation import bindings changed')
    return dict(host_sha256=HOST_SHA256,direct_block_constructor_callers=callers,
        kind=7,inline_data_limit=3,metadata_bytes=4,native_object_bytes=24,
        variable_native_pointer_transmitted=False,host_to_core1_translation_proved=False,
        live_host_queue_or_device_executed=False)


def checked_args(selector,index,byte2,byte3,data,canary):
    if any(type(v)is not int or not 0<=v<=0xffffffff for v in (selector,index,byte2,byte3)):
        raise ValueError('Expected explicit unsigned32 constructor scalar arguments')
    if type(data)is not bytes or len(data)>0x660:
        raise ValueError('Expected at most 0x660 authored payload bytes for this replay')
    if type(canary)is not int or not 0<=canary<=255:raise ValueError('Expected one canary byte')


class HostBlockOracle:
    def __init__(self,image):
        self.checked=report(image)
        import unicorn
        from unicorn import arm64_const
        self.arm=arm64_const;self.cpu=unicorn.Uc(unicorn.UC_ARCH_ARM64,unicorn.UC_MODE_ARM)
        u=self.cpu
        u.mem_map(0xbe1000,0x4000);u.mem_write(0xbe1000,image.read(0xbe1000,0x4000))
        u.mem_protect(0xbe1000,0x4000,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        for base in (STOP,0x40b000,0x40c000,0xbdf000,0x3e5d000,0x412e000):u.mem_map(base,0x1000)
        u.mem_map(RAM,0x20000)
        u.mem_write(SINK,struct.pack('<Q',VTABLE));u.mem_write(VTABLE+16,struct.pack('<Q',CALLBACK))
        u.hook_add(unicorn.UC_HOOK_CODE,self._code)

    def _code(self,u,pc,size,_):
        a=self.arm;r=lambda i:u.reg_read(getattr(a,f'UC_ARM64_REG_X{i}'))
        result=None
        if pc==0x40b2c0:
            destination,source,count=r(0),r(1),r(2)
            if count>0x668:raise ValueError('Unexpected memcpy size')
            u.mem_write(destination,bytes(u.mem_read(source,count)));result=destination
        elif pc==0x40c350:
            self.allocations.append(r(0))
            if len(self.allocations)!=1 or r(0)!=self.length+8:raise ValueError('Unexpected allocation')
            result=HEAP
        elif pc==0xbdf9b8:
            if r(0)!=0x412efb0:raise ValueError('Unexpected reference-count target')
            self.refcalls+=1;result=0
        elif pc==CALLBACK:
            if r(0)!=SINK or r(2)>0x660:raise ValueError('Unexpected serializer sink arguments')
            self.chunks.append(bytes(u.mem_read(r(1),r(2))));result=1
        elif not 0xbe1000<=pc<0xbe5000:
            raise ValueError(f'Unexpected host execution at {pc:#x}')
        if result is not None:
            u.reg_write(a.UC_ARM64_REG_X0,result);u.reg_write(a.UC_ARM64_REG_PC,r(30))

    def _run(self,entry,*args):
        u=self.cpu;a=self.arm
        for i,value in enumerate(args):u.reg_write(getattr(a,f'UC_ARM64_REG_X{i}'),value)
        u.reg_write(a.UC_ARM64_REG_SP,RAM+0x1f000);u.reg_write(a.UC_ARM64_REG_X30,STOP)
        u.emu_start(entry,STOP,count=20000)
        if u.reg_read(a.UC_ARM64_REG_PC)!=STOP:raise ValueError('Host replay exceeded instruction budget')

    def serialize(self,selector,index,byte2,byte3,data,canary=0x5a):
        checked_args(selector,index,byte2,byte3,data,canary)
        u=self.cpu;self.length=len(data);self.allocations=[];self.chunks=[];self.refcalls=0
        u.mem_write(OBJECT,bytes((canary,))*24);u.mem_write(INPUT,data or b'\0')
        u.mem_write(RAM+0x10000,bytes((canary,))*0xf000)
        self._run(CONSTRUCT,OBJECT,selector,index,byte2,byte3,INPUT,len(data))
        native=bytes(u.mem_read(OBJECT,24))
        # The constructor must copy; the caller's original storage expires before serialization.
        u.mem_write(INPUT,b'\xa5'*max(1,len(data)))
        self._run(SERIALIZE,SINK,OBJECT)
        wire=b''.join(self.chunks)
        metadata=struct.pack('<HBB',index&65535,byte2&255,byte3&255)
        prefix=bytes((0x0f if len(data)>3 else 0x0e,0,0,selector&255))
        if len(data)>3:
            expected=prefix+bytes((canary,))*4+metadata+struct.pack('<I',len(data))+data
            sizes=[8,4,4,len(data)]
        else:
            expected=prefix+metadata+data+bytes((canary,))*(3-len(data))+bytes((len(data)+4,))
            sizes=[12]
        if wire!=expected or list(map(len,self.chunks))!=sizes:
            raise ValueError('Original host constructor/serializer differs from independent byte layout')
        if self.allocations!=([len(data)+8]if len(data)>3 else[])or self.refcalls!=(len(data)>3):
            raise ValueError('Unexpected host storage path')
        return dict(wire=wire,native=native,chunk_sizes=sizes,variable=len(data)>3)


def selfcheck(image):
    from bmc_ipc import frames
    oracle=HostBlockOracle(image);count=0
    for size in (0,1,2,3,4,5,7,8,9,0x54,0x410,0x660):
        data=bytes((i*73+129)&255 for i in range(size))
        for selector,index,b2,b3 in ((0x14,2,0,0),(0x91,0x1234,0x56,0x78),(0x184,0x12345,0x1ff,0x1fe)):
            for canary in (0x00,0x5a,0xff):
                row=oracle.serialize(selector,index,b2,b3,data,canary)
                frame,=frames(row['wire'])
                metadata=struct.pack('<HBB',index&65535,b2&255,b3&255)
                if (frame['kind']!=7 or frame['selector']!=selector&255
                        or bytes.fromhex(frame['payload'])!=(data if row['variable']else metadata+data)
                        or frame['block']!=dict(u16=index&65535,byte2=b2&255,byte3=b3&255,data=data.hex())):
                    raise ValueError('Existing capture decoder disagrees with original serializer')
                count+=1
    return dict(oracle.checked,original_host_block_cases=count,
        constructor_copies_input=True,padding_depends_on_seeded_memory=True,
        allocations_and_memcpy_intercepted=True,original_queue_execution=False)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('image',type=Path)
    parser.add_argument('--execute-arm64',action='store_true');args=parser.parse_args()
    image=HostImage(args.image.read_bytes())
    print(json.dumps(selfcheck(image)if args.execute_arm64 else report(image),indent=2))

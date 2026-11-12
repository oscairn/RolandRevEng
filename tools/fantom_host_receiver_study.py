"""Original host range registry, coalescing receiver and drain; emitter is intercepted."""
import itertools
import struct

from fantom_host_block_study import HostImage,HostBlockOracle,report as host_report,RAM,OBJECT,STOP

RECEIVER,WORKER,CFF=0x424bb20,0x424bdf8,0x424be78
STATIC_INIT,PROVIDERS_INIT,THREAD_SETUP=0x438240,0xc05580,0xbfe590
ENQUEUE,DRAIN,EMIT,WAKE=0xbfe640,0xbfe9b8,0xbfe7c0,0xbfed48
ARENA,ARENA_SIZE,PAYLOAD=0x30000000,0x800000,RAM+0x7000
CODE=((0x438000,0x439000),(0xbfe000,0xbff000),(0xc05000,0xc09000),
    (0xc0d000,0xc0e000),(0xc1a000,0xc1d000))


def checked_events(events):
    if not isinstance(events,(list,tuple))or len(events)>32:
        raise ValueError('Expected at most32 authored notification events')
    for row in events:
        if (not isinstance(row,(list,tuple))or len(row)!=5 or any(type(v)is not int for v in row)
                or row[0]not in (6,7)or not 0<=row[1]<=16383 or not 0<=row[2]<=255
                or not 3504<=row[3]<=row[4]<=3505):
            raise ValueError('Expected family6/7, index0..16383, context0..255 and checked generic live1 range')


def coalesced_ranges(events):
    result={}
    for family,index,context,first,last in events:
        key=(family,0,context if family==7 and context<2 else 0)
        lo,hi=result.get(key,(first,last))
        result[key]=(min(lo,first),max(hi,last))
    return [(*key,*bounds)for key,bounds in result.items()]


def report(image):
    import capstone
    result=host_report(image);md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
    inits=list(struct.iter_unpack('<Q',image.elf.get_section_by_name('.init_array').data()))
    if inits.count((STATIC_INIT,))!=1:raise ValueError('Stock registry initializer activation changed')
    for vtable,name,slots in ((0x1386030,b'14CIDMinMaxBlockILi1ELi1EE',(0xc0db40,0xc0db68)),
                             (0x1386090,b'14CIDMinMaxBlockILi1ELi2EE',(0xc0da48,0xc0da78))):
        ti=struct.unpack('<Q',image.read(vtable-8,8))[0]
        pointer=struct.unpack('<Q',image.read(ti+8,8))[0]
        if (image.read(pointer,len(name)+1)!=name+b'\0'
                or struct.unpack('<2Q',image.read(vtable,16))!=slots):
            raise ValueError('Stock dirty-record provider RTTI/vtable changed')
    checks={0x438258:('bl','#0xc05580'),0x438278:('str','x19, [x20, #0x700]'),
        0xc056f0:('str','x2, [x19, #0x30]'),0xc05720:('str','x2, [x19, #0x38]'),
        0xbfe6e0:('blr','x3'),0xbfea44:('blr','x4'),0xbfea54:('str','w2, [x0]'),
        0xbfead8:('bl','#0xbfe7c0'),0xbfed3c:('bl','#0xbfe9b8'),
        0xbfed6c:('str','w1, [x19, #0x30]'),0xbfe958:('mov','w0, #8'),
        0xbfe95c:('bl','#0xbe4270'),0xbfeddc:('mov','w4, #0x41f0')}
    for pc,expected in checks.items():
        rows=list(md.disasm(image.read(pc,4),pc))
        if len(rows)!=1 or(rows[0].mnemonic,rows[0].op_str)!=expected:
            raise ValueError(f'Receiver anchor changed at {pc:#x}')
    symbols=image.elf.get_section_by_name('.dynsym');plt=image.elf.get_section_by_name('.plt')['sh_addr']
    imports={plt+32+16*i:symbols.get_symbol(r['r_info_sym']).name for i,r in
        enumerate(image.elf.get_section_by_name('.rela.plt').iter_relocations())}
    addresses=(0x40bef0,0x40b060,0x40abd0,0x40c9b0,0x40b8b0,0x40b3a0,0x40cf40,0x40bac0)
    if [imports.get(p)for p in addresses]!=['_Znwm','memset','pthread_self','__cxa_atexit',
            'pthread_mutex_init','sem_init','usleep','pthread_cond_signal']:
        raise ValueError('Receiver runtime import bindings changed')
    result.update(registry_static_initializer=STATIC_INIT,providers_initializer=PROVIDERS_INIT,
        route4_receiver=ENQUEUE,range_drain=DRAIN,sys_ex_emitter=EMIT,
        family6_provider_rtti='CIDMinMaxBlock<1,1>',family7_provider_rtti='CIDMinMaxBlock<1,2>',
        sys_ex_kind2_destination8_source_checked=True,sys_ex_emitter_executed=False,
        full_worker_thread_executed=False,host_to_core1_translation_proved=False)
    return result


class ReceiverOracle(HostBlockOracle):
    def __init__(self,image):
        source=report(image);super().__init__(image);self.checked.update(source)
        import unicorn
        self.arena_next=ARENA;self.allocations=[];self.runtime=[];u=self.cpu
        u.reg_write(self.arm.UC_ARM64_REG_CPACR_EL1,0x300000)
        for start,end in CODE:
            u.mem_map(start,end-start);u.mem_write(start,image.read(start,end-start))
            u.mem_protect(start,end-start,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        u.mem_map(0x40a000,0x1000)
        u.mem_map(0x1384000,0x1c000);u.mem_write(0x1384000,image.read(0x1384000,0x1c000))
        u.mem_protect(0x1384000,0x1c000,unicorn.UC_PROT_READ)
        u.mem_map(0x424a000,0x4000);u.mem_map(ARENA,ARENA_SIZE)
        self._run(0xc1aa60,CFF,0x13844c8)
        # The complete provider constructor exceeds the small fragment instruction budget.
        u.reg_write(self.arm.UC_ARM64_REG_SP,RAM+0x1f000);u.reg_write(self.arm.UC_ARM64_REG_X30,STOP)
        u.emu_start(STATIC_INIT,STOP,count=1000000)
        if u.reg_read(self.arm.UC_ARM64_REG_PC)!=STOP:raise ValueError('Registry initializer exceeded its instruction budget')
        self.registry=self._word(RECEIVER,8)
        self.provider6=self._word(self.registry+6*8,8);self.provider7=self._word(self.registry+7*8,8)
        if (len(self.allocations)!=78 or self._word(self.provider6,8)!=0x1386030
                or self._word(self.provider7,8)!=0x1386090):raise ValueError('Original provider registration differs')
        self.records=(self.provider6+8,self.provider7+8,self.provider7+32)
        self._run(THREAD_SETUP,WAKE)
        if self._word(RECEIVER+0xd0,8)!=WAKE:raise ValueError('Original wake callback binding differs')
        self._empty()

    def _word(self,address,size=4):return int.from_bytes(self.cpu.mem_read(address,size),'little')

    def _empty(self):
        if self._word(self.registry+0x800,8)or self._word(self.registry+0x808,8):
            raise ValueError('Pending list did not empty')
        for record in self.records:
            if (self._word(record)!=65535 or self._word(record+4,2)
                    or self._word(record+8,8)or self._word(record+16,8)):
                raise ValueError('Dirty record was not reset for reuse')

    def _code(self,u,pc,size,_):
        a=self.arm;r=lambda i:u.reg_read(getattr(a,f'UC_ARM64_REG_X{i}'))
        result=None
        if pc==0x40bef0:
            count=r(0);address=self.arena_next;self.arena_next=(address+count+15)&~15
            if not 0<count<=ARENA_SIZE or self.arena_next>ARENA+ARENA_SIZE:raise ValueError('Unexpected registry allocation')
            self.allocations.append((address,count));result=address
        elif pc==0x40b060:
            if r(2)>ARENA_SIZE:raise ValueError('Unexpected registry memset')
            u.mem_write(r(0),bytes((r(1)&255,))*r(2));result=r(0)
        elif pc in (0x40abd0,0x40c9b0,0x40b8b0,0x40b3a0):
            self.runtime.append((pc,r(0)));result=1 if pc==0x40abd0 else 0
        elif pc in (0x40ca10,0x40c690):
            if r(0)not in (RECEIVER+8,WORKER):raise ValueError('Unexpected receiver mutex address')
            self.runtime.append((pc,r(0)));result=0
        elif pc==0x40bac0:
            if r(0)!=WORKER+0x38 or self._word(WORKER+0x30)!=1:raise ValueError('Wake signal/flag differs')
            self.signals+=1;result=0
        elif pc==0x40cf40:
            if r(0)!=10000:raise ValueError('Unexpected drain delay request')
            self.delays+=1;result=0
        elif pc==EMIT:
            if r(0)!=RECEIVER:raise ValueError('Unexpected drained receiver')
            p=bytes(u.mem_read(r(1),7));header=int.from_bytes(p[:4],'little')
            self.drained.append((header&1023,(header>>10)&16383,header>>24,
                3486+(p[4]<<4)+(p[6]&15),3486+(p[5]<<4)+(p[6]>>4)))
            result=0
        elif any(start<=pc<end for start,end in CODE):return
        else:return super()._code(u,pc,size,_)
        u.reg_write(a.UC_ARM64_REG_X0,result);u.reg_write(a.UC_ARM64_REG_PC,r(30))

    def run_case(self,events,canary=0x5a):
        checked_events(events)
        if type(canary)is not int or not 0<=canary<=255:raise ValueError('Expected a canary byte')
        self._empty();u=self.cpu;self.signals=self.delays=0;self.drained=[];self.runtime=[]
        u.mem_write(WORKER+0x30,bytes(4));u.mem_write(RAM+0x10000,bytes((canary,))*0xf000)
        for family,index,context,first,last in events:
            self._run(0xbe40d0,PAYLOAD,family,index,context,first,last)
            self._run(0xbe2998,OBJECT,PAYLOAD)
            self._run(0xbe4270,4,OBJECT)
        wanted=coalesced_ranges(events)
        if self.signals!=len(events)or self._word(WORKER+0x30)!=bool(events):
            raise ValueError('Original wake count/pending flag differs')
        self._run(DRAIN,RECEIVER);self._empty()
        if self.drained!=wanted or self.delays!=len(wanted):raise ValueError('Original coalescing/FIFO drain differs')
        before=list(self.drained);self._run(DRAIN,RECEIVER)
        if self.drained!=before:raise ValueError('Empty drain replayed an old notification')
        return dict(events=len(events),drained=len(wanted))


def selfcheck(image):
    oracle=ReceiverOracle(image);cases=events=drained=0
    atoms=((6,0,0,3504,3504),(6,16383,255,3505,3505),(7,0,0,3504,3504),
        (7,0,1,3505,3505),(7,1,2,3504,3505),(7,16383,255,3505,3505))
    for length in range(4):
        for sequence in itertools.product(atoms,repeat=length):
            for canary in (0,0x5a,255):
                row=oracle.run_case(sequence,canary);cases+=1;events+=row['events'];drained+=row['drained']
    return dict(oracle.checked,original_receiver_cases=cases,incoming_local_notifications=events,
        coalesced_emitter_calls=drained,original_registry_allocations=len(oracle.allocations),
        original_registry_receiver_provider_wake_and_drain_executed=True,
        mutex_sem_thread_runtime_and_delays_intercepted=True,sys_ex_emitter_executed=False)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('host')
    parser.add_argument('--execute-arm64',action='store_true');args=parser.parse_args()
    image=HostImage(Path(args.host).read_bytes())
    print(json.dumps(selfcheck(image)if args.execute_arm64 else report(image),indent=2))

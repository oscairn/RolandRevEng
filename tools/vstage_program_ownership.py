"""Pinned shared-program descriptors and bounded CORE1 caller evidence, offline."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from bmc_dsp import swap_words
from core1_rtti import trace,word_refs
from kernel_abi import program_list,read
from vstage_core1_comparison import report as comparison,segments
from vstage_firmware_study import UPDATE_SHA256
from edge_juno_firmware_study import update_parts


def literal_loads(core,pool):
    """Halfword candidates within Thumb literal reach; callers need corroboration."""
    from capstone.arm import ARM_OP_MEM,ARM_REG_PC
    off=core.offset(pool)
    low,high=((0x01100000,0x01100000+core.eram_offset)if off<core.eram_offset else
              (0x61000000,0x61000000+len(core.data)-core.eram_offset))
    rows=[]
    for pc in range(max(low,pool-4100),min(high-3,pool+4100),2):
        data=read(core,pc,4);first=int.from_bytes(data[:2],'little')
        if first&0xf800!=0x4800 and first not in (0xf8df,0xf85f):continue
        ins=next(core.md.disasm(data,pc,count=1),None)
        if not ins or ins.mnemonic not in ('ldr','ldr.w')or len(ins.operands)!=2:continue
        operand=ins.operands[1]
        if (operand.type==ARM_OP_MEM and operand.mem.base==ARM_REG_PC and not operand.mem.index
                and ((pc+4)&~3)+operand.mem.disp==pool):
            rows.append(dict(pc=pc,pool=pool,value=core.u32(pool),instruction=f'{ins.mnemonic} {ins.op_str}'))
    return rows


def locate(core,digest):
    from analyze import core_lists
    _,entries,_=segments(core)
    wanted={(r['source_offset'],r['length'])for r,_,_ in entries if r['sha256']==digest}
    rows=[]
    for item in core_lists(core):
        address=core.address(item['payload_offset'])
        for index,(base,length,capacity,source)in enumerate(item['segments']):
            if (source,length)not in wanted:continue
            listing=program_list(core,address)
            seg=listing['segments'][index]
            if (seg['base'],seg['length'],seg['capacity'],seg['source'])!=(base,length,capacity,core.address(source)):
                raise ValueError('Candidate list and bounded parser disagree')
            refs=[core.address(o)for o in word_refs(core.data,address)]
            rows.append(dict(list_address=address,header_dsp=item['dsp'],row_index=index,
                table_address=core.u32(address+4),segment_base=base,length=length,capacity=capacity,
                source=core.address(source),source_payload_offset=source,source_c1a_offset=core.header+source,
                sha256=digest,list_pointer_locations=refs,
                literal_load_candidates=[r for pool in refs for r in literal_loads(core,pool)]))
    return rows


def require_shape(core,address,expected):
    instructions=list(core.md.disasm(read(core,address,64),address))[:len(expected)]
    actual=[(i.mnemonic,i.op_str)for i in instructions]
    if actual!=expected:raise ValueError(f'Unexpected caller shape at {address:#x}')
    return [dict(pc=i.address,bytes=i.bytes.hex(),instruction=f'{i.mnemonic} {i.op_str}')for i in instructions]


def fdrv_owner(core,row):
    rtti=trace(core,'11CFspMfxFDRV');owners=[]
    for load in row['literal_load_candidates']:
        pc=load['pc'];entry=pc-10
        candidates=[v for v in rtti['candidates']if len(v['thumb_callback_candidates'])>2
                    and v['thumb_callback_candidates'][2]==entry|1]
        if not candidates:continue
        shape=require_shape(core,entry,[('push','{r4, lr}'),('mov','r4, r0'),('ldr','r0, [r0, #4]'),
            ('ldr','r1, [r0]'),('ldr','r2, [r1, #0x28]'),
            ('ldr',load['instruction'].split(' ',1)[1]),('blx','r2')])
        owners.append(dict(encoded_class=rtti['encoded_name'],typeinfo=candidates[0]['typeinfo'],
            vtable=candidates[0]['vtable'],address_point=candidates[0]['vtable']+8,
            callback_slot=8,callback_entry=entry,dispatch_slot=0x28,program_list_argument='r1',instructions=shape))
    if len(owners)!=1:raise ValueError('Expected one RTTI-linked FDRV program-list caller')
    return owners[0]


def diagnostic_dispatch(core,row):
    results=[]
    text=b'CFspDspTest::EResult CFspDspTest::TestEram()\0'
    for load in row['literal_load_candidates']:
        pc=load['pc']
        shape=require_shape(core,pc-4,[('ldr','r1, [r0]'),('ldr','r2, [r1, #0x18]'),
            ('ldr',load['instruction'].split(' ',1)[1]),('blx','r2')])
        nearby=core.u32(load['pool']-4)
        if read(core,nearby,len(text))!=text:raise ValueError('Diagnostic assertion text differs')
        assertion_loads=[r for r in literal_loads(core,load['pool']-4)if 0<pc-r['pc']<128]
        if len(assertion_loads)!=1:raise ValueError('Expected nearby diagnostic assertion literal reader')
        results.append(dict(dispatch_slot=0x18,program_list_argument='r1',instructions=shape,
            assertion_text=text[:-1].decode(),assertion_address=nearby,assertion_load=assertion_loads[0],
            named_method_inferred_from_assertion=True))
    if not results:raise ValueError('No diagnostic program-list dispatch found')
    return results


def bootstrap_references(core,row):
    evidence=[]
    for load in row['literal_load_candidates']:
        pc=load['pc'];register=load['instruction'].split(' ',1)[1].split(',')[0]
        if register=='r1':
            shape=require_shape(core,pc+30,[('ldr','r2, [r0]'),('ldr','r2, [r2, #0x18]'),('blx','r2')])
            evidence.append(dict(kind='selected_list_dispatch',load=load,dispatch_slot=0x18,instructions=shape))
        elif register=='r6':
            count=require_shape(core,pc+6,[('ldrb','r0, [r6, #2]'),('movs','r5, #0'),('cmp','r0, #0')])
            table=require_shape(core,pc+14,[('ldr','r0, [r6, #4]'),('adds.w','r8, r0, r5, lsl #4')])
            evidence.append(dict(kind='list_count_and_16_byte_row_walk',load=load,instructions=count+table))
    if len(evidence)!=2:raise ValueError('Expected selected-list dispatch and row-reader references')
    return evidence


def report(update,fantom):
    checked=comparison(update,fantom)
    hashes={s['length']:s['sha256']for s in checked['groups'][0]['shared_segments']if s['length']in (11572,51542)}
    parts=dict(update_parts(update,UPDATE_SHA256));result=[]
    from core1 import Core1
    with tempfile.TemporaryDirectory(prefix='vstage-owner-')as directory:
        paths=[('Fantom',[0],Path(fantom))]
        for index,group in ((0,[0]),(1,[1,2])):
            name=f'bmc{index}_MI087_C1A_up.bin';path=Path(directory)/name;path.write_bytes(parts[name])
            paths.append(('V-STAGE',group,path))
        for model,targets,path in paths:
            core=Core1(path)
            fdrv=[]
            if model=='Fantom' or targets==[1,2]:
                listing=program_list(core,0x610e5a94 if model=='Fantom'else 0x611008a8)
                seg=listing['segments'][1 if model=='Fantom'else 0]
                logical=swap_words(read(core,seg['source'],(seg['length']+3)&~3))[:seg['length']]
                digest=hashlib.sha256(logical).hexdigest();fdrv=locate(core,digest)
                if len(fdrv)!=1:raise ValueError('Expected one containing FDRV list')
                fdrv[0]['owner']=fdrv_owner(core,fdrv[0])
                proof=checked['groups'][1]['relocated_fdrv_body_checks']
                body=next(p for p in proof if p['vstage_hits'])
                if hashlib.sha256(logical[0x3ec:0x446]).hexdigest()!=body['sha256']:
                    raise ValueError('Caller list does not contain the checked relocated body')
            shared=[]
            for length,digest in hashes.items():
                for row in locate(core,digest):
                    if length==11572:row['diagnostic_dispatch']=diagnostic_dispatch(core,row)
                    else:row['bootstrap_references']=bootstrap_references(core,row)
                    shared.append(row)
            result.append(dict(model=model,targets=targets,payload_sha256=hashlib.sha256(core.data).hexdigest(),
                fdrv_programs=fdrv,shared_programs=shared))
    return dict(update_sha256=UPDATE_SHA256,images=result,hardware_compatibility_verified=False,
        limitations=['Literal-load scans include halfword candidates; FDRV ownership also requires RTTI and exact caller shape.',
            'The 11572-byte diagnostic method name is inferred from assertion text and nearby dispatch, not a symbol table.',
            '51542-byte program has list-selection/read-loop references; its exact class/function owner remains unresolved.',
            'Vtable dispatch targets depend on runtime object identity; this report does not execute a loader.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('update',type=Path);parser.add_argument('fantom',type=Path);parser.add_argument('--out',type=Path)
    args=parser.parse_args();result=report(args.update,args.fantom)
    data=json.dumps(result,indent=2)+'\n'
    if args.out:args.out.write_text(data)
    print(data)

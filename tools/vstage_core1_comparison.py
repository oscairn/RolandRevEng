"""Pinned V-STAGE/Fantom service and candidate DSP comparisons, without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from additional_firmware_study import FANTOM_SHA256,find_windows
from bmc_dsp import assemble,command_count,packets,swap_words
from edge_juno_firmware_study import update_parts
from header_study import layout
from kernel_abi import program_list,read
from vstage_firmware_study import UPDATE_SHA256,report as inventory_report

WINDOWS=(('MMIO read prefix',0x6102d2e6,324),('RAMCLR body',0x61056b14,158),
         ('DRAM-IO low23 rewrite',0x0113383c,14))


def context_key(words):
    """Ignore numeric literals/resources, retain control/extension syntax and tags."""
    controls=tuple(words[1:1+command_count(words[0])])
    try:
        fields=layout(words)['fields']
    except ValueError:
        return ('unclassified',words[0],controls,(),())
    extensions=tuple((f['offset'],words[f['offset']//2])for f in fields if f['role']=='extension')
    tags=tuple((f['offset'],words[f['offset']//2]&0xf000)for f in fields if f['role']=='address')
    return ('layout',words[0],controls,extensions,tags)


def segments(core):
    from analyze import core_lists
    lists=core_lists(core);seen=set();entries=[];failures=[];contexts={}
    for item in lists:
        for base,length,_,source in item['segments']:
            if not length or (source,length)in seen:continue
            seen.add((source,length))
            try:
                stream=swap_words(read(core,core.address(source),(length+3)&~3))[:length]
                decoded=packets(stream)
                if assemble(w for _,w in decoded)!=stream:raise ValueError('Packet roundtrip differs')
            except ValueError as error:
                failures.append(dict(source_offset=source,length=length,error=str(error)));continue
            row=dict(source_offset=source,length=length,segment_base=base,
                     sha256=hashlib.sha256(stream).hexdigest(),packets=len(decoded))
            entries.append((row,stream,{offset for offset,_ in decoded}|{len(stream)}))
            for offset,words in decoded:
                key=context_key(words)
                contexts.setdefault(key,dict(source_offset=source,logical_byte_offset=offset,
                    header=words[0],controls=list(key[2]),classification=key[0],
                    extensions=list(key[3]),transfer_tags=list(key[4])))
    return dict(candidate_lists=len(lists),unique_nonempty_candidates=len(seen),
                framed_segments=len(entries),framing_failures=failures,
                distinct_logical_segments=len({r['sha256']for r,_,_ in entries}),
                distinct_contexts=len(contexts)),entries,contexts


def body_hits(entries,body):
    hits=[]
    for row,stream,boundaries in entries:
        cursor=0
        while (offset:=stream.find(body,cursor))>=0:
            cursor=offset+1
            if offset in boundaries and offset+len(body)in boundaries:
                hits.append(dict(source_offset=row['source_offset'],logical_byte_offset=offset))
    return hits


def report(update,fantom_path):
    from core1 import Core1
    verified=inventory_report(update)
    fantom=Core1(fantom_path)
    if hashlib.sha256(fantom.data).hexdigest()!=FANTOM_SHA256:
        raise ValueError('Unsupported Fantom comparison digest')
    patterns=[(name,read(fantom,address,length))for name,address,length in WINDOWS]
    baseline,baseline_entries,baseline_contexts=segments(fantom)
    baseline_hashes={r['sha256']for r,_,_ in baseline_entries}
    bodies=[]
    for seg in program_list(fantom,0x610e5a94)['segments']:
        stream=swap_words(read(fantom,seg['source'],(seg['length']+3)&~3))[:seg['length']]
        body=stream[0x3ec:0x446]
        witnesses=body_hits(baseline_entries,body)
        if len(body)!=90 or not witnesses:raise ValueError('Fantom relocated-body positive control failed')
        bodies.append((dict(fantom_segment_base=seg['base'],sha256=hashlib.sha256(body).hexdigest(),
                            fantom_hits=witnesses),body))
    parts=dict(update_parts(update,UPDATE_SHA256));rows=[]
    with tempfile.TemporaryDirectory(prefix='vstage-compare-')as directory:
        for group in verified['identical_component_groups']:
            target=group[0];name=f'bmc{target}_MI087_C1A_up.bin'
            path=Path(directory)/name;path.write_bytes(parts[name]);core=Core1(path)
            regions=[dict(name='ITCM',runtime_base=0x01100000,analysis_offset=0,
                          source_offset=core.header,size=core.eram_offset),
                     dict(name='ERAM',runtime_base=0x61000000,analysis_offset=core.eram_offset,
                          source_offset=core.header+core.eram_offset,size=len(core.data)-core.eram_offset)]
            summary,entries,contexts=segments(core)
            shared=sorted({r['sha256']for r,_,_ in entries}&baseline_hashes)
            novel=sorted(set(contexts)-set(baseline_contexts))
            rows.append(dict(targets=group,component=name,sha256=hashlib.sha256(parts[name]).hexdigest(),
                service_windows=find_windows(dict(regions=regions),core.data,patterns),inventory=summary,
                shared_segments=[dict(sha256=h,length=next(r['length']for r,_,_ in entries if r['sha256']==h),
                    packets=next(r['packets']for r,_,_ in entries if r['sha256']==h))for h in shared],
                unseen_context_count=len(novel),unseen_context_examples=[contexts[k]for k in novel[:8]],
                relocated_fdrv_body_checks=[dict(meta,vstage_hits=body_hits(entries,body))for meta,body in bodies]))
    return dict(update_sha256=UPDATE_SHA256,fantom_payload_sha256=FANTOM_SHA256,baseline=baseline,groups=rows,
        context_policy='Header/base controls, classified long extensions and transfer tags; numeric literals/indices excluded.',
        new_opcode_meanings_proved=False,owner_proven_inventory=False,hardware_compatibility_verified=False,
        limitations=['Exact service windows are not whole functions or host/loading compatibility proofs.',
            'Segment lists are structural candidates; framing failures remain reported.',
            'Unseen contexts are observed encodings, not proved new ISA operations; unclassified layouts stay unclassified.',
            'An absent exact relocated body does not establish an absent algorithm or semantic equivalence.',
            'Source offsets in service-window hits include the C1A prefix; they are not outer-tar offsets.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('update',type=Path);parser.add_argument('fantom',type=Path)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args();result=report(args.update,args.fantom)
    if args.out:args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

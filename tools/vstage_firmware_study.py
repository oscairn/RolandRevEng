"""Inventory the pinned official V-STAGE update offline; no device execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

from c0_header import header
from edge_juno_firmware_study import update_parts

SOURCE_URL='https://static.roland.com/assets/media/zip/vstage_sys_v111.zip'
ZIP_SHA256='8e883fa00fd083926716d2fd0f0cac6744eebda7f50fb905dc04ca4844ae6572'
UPDATE_SHA256='145262c536dec1928c4652bec6c5c84318374445219832c34e864760377644a8'


def report(path):
    parts=dict(update_parts(path,UPDATE_SHA256))
    expected={f'bmc{i}_MI087_{kind}_up.bin'for i in range(5)for kind in ('C0A','C1A','C1C')}
    if set(parts)!=expected:
        raise ValueError('Unexpected V-STAGE target/component inventory')
    from core1 import Core1
    rows=[];groups={}
    with tempfile.TemporaryDirectory(prefix='vstage-core1-')as directory:
        for target in range(5):
            components=[]
            for kind in ('C0A','C1A','C1C'):
                name=f'bmc{target}_MI087_{kind}_up.bin';data=parts[name]
                footer=re.search(rb'Roland MI087_'+kind.encode()+rb'VER\.1\.11BLD\.0098Commit:[0-9a-f]{9}',data[-96:])
                if footer is None:
                    raise ValueError('V-STAGE component identification footer differs')
                item=dict(name=name,size=len(data),sha256=hashlib.sha256(data).hexdigest(),
                          footer=footer.group().decode())
                if kind=='C0A':item['header']=header(data)
                if kind=='C1A':
                    analysis=Path(directory)/name;analysis.write_bytes(data)
                    core=Core1(analysis)
                    item['core1']=dict(prefix_bytes=core.header,eram_offset=core.eram_offset,
                        initial_stack=int.from_bytes(core.data[:4],'little'),
                        reset_entry=int.from_bytes(core.data[4:8],'little'),
                        scatter_records=len(core.scatter()),mapper_accepted=True)
                components.append(item)
            signature=tuple(item['sha256']for item in components)
            groups.setdefault(signature,[]).append(target)
            rows.append(dict(target=target,components=components))
    if list(groups.values())!=[[0],[1,2],[3,4]]:
        raise ValueError('V-STAGE code/content sharing groups differ')
    return dict(source_url=SOURCE_URL,zip_sha256=ZIP_SHA256,update_sha256=UPDATE_SHA256,
                update_bytes=Path(path).stat().st_size,bmc_target_indices=list(range(5)),
                component_count=len(parts),identical_component_groups=list(groups.values()),targets=rows,
                physical_chip_count_verified=False,host_cpu_identified=False,
                separately_named_host_image_present=False,dsp_isa_compatibility_verified=False,
                key_recovered=False,decryption_performed=False,hardware_execution=False,
                limitations=['Five named BMC firmware targets are not an independent board-chip count.',
                    'The existing CORE1 mapper accepts the vectors/scatter layout, not an exact CPU part.',
                    'Encrypted CORE0 payloads remain opaque; header key index is not a key value.',
                    'No separately named host/Linux image was found; embedded opaque content and host architecture remain unresolved.',
                    'Duplicate images do not establish engine-to-chip roles, available capacity or load compatibility.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('update',type=Path)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args();result=report(args.update)
    if args.out:args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

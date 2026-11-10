"""Inspect pinned SH-4d/TR-8S factory updates and compare file-backed code windows."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

from c0_header import header
from qspi_c1 import parse_c1

SH_UPDATE_SHA256 = '744584b30b93fd57b1ab271105a64a6c48b609217175b7d5b54b640ae58f9f5e'
TR_UPDATE_SHA256 = 'f1948e2719fef2735f0611848501f1eb3a1a163b5b75aaef20ae3db28489f2ba'
FANTOM_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


def components(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Unsupported factory archive digest')
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for member in archive:
            if not member.isfile():
                raise ValueError('Expected regular firmware archive members')
            name = Path(member.name).name
            if name in result or not 0 < member.size <= 0x1000000:
                raise ValueError('Duplicate or oversized firmware component')
            result[name] = archive.extractfile(member).read()
    return result


def find_windows(manifest, view, patterns):
    """Search each actual region separately; a match cannot bridge an ITCM gap."""
    rows = []
    for name, pattern in patterns:
        if not pattern:
            raise ValueError('Expected a nonempty comparison window')
        hits = []
        for region in manifest['regions']:
            start, size = region['analysis_offset'], region['size']
            if start < 0 or size < 0 or start + size > len(view):
                raise ValueError('Region exceeds analysis view')
            data, cursor = view[start:start+size], 0
            while (cursor := data.find(pattern, cursor)) >= 0:
                hits.append(dict(member=region['name'], runtime=region['runtime_base']+cursor,
                                 container_offset=region['source_offset']+cursor))
                cursor += 1
        rows.append(dict(name=name, length=len(pattern),
                         sha256=hashlib.sha256(pattern).hexdigest(), hits=hits))
    return rows


def report(sh_update, tr_update, fantom):
    if hashlib.sha256(fantom.data).hexdigest() != FANTOM_SHA256:
        raise ValueError('Unsupported Fantom comparison digest')
    sh, tr = components(sh_update, SH_UPDATE_SHA256), components(tr_update, TR_UPDATE_SHA256)
    if set(sh) != {'DD013_C1A_up.bin', 'DD013_C1C_up.bin', 'DD013_C0A_up.bin',
                   'DD013_C0C_up.bin', 'DD013_SUB_up.bin'}:
        raise ValueError('Unexpected SH-4d component inventory')
    if set(tr) != {'rpg42_m0c0a_up.bin', 'rpg42_init_param.bin'}:
        raise ValueError('Unexpected TR-8S component inventory')
    manifest, view = parse_c1(sh['DD013_C1A_up.bin'])
    patterns = []
    for name, address, length in (('MMIO read prefix', 0x6102d2e6, 324),
                                  ('RAMCLR body', 0x61056b14, 158),
                                  ('DRAM-IO low23 rewrite', 0x0113383c, 14)):
        offset = fantom.offset(address)
        patterns.append((name, fantom.data[offset:offset+length]))
    windows = find_windows(manifest, view, patterns)
    if [r['hits'] for r in windows] != [
            [dict(member='sdram1.bin', runtime=0x61029baa, container_offset=0x6abca)],
            [dict(member='sdram1.bin', runtime=0x610593b0, container_offset=0x9a3d0)],
            [dict(member='idm1.bin', runtime=0x01134f48, container_offset=0x35f68)]]:
        raise ValueError('Expected unique file-backed SH-4d comparison windows')
    def inventory(parts):
        return [dict(name=name, size=len(data), sha256=hashlib.sha256(data).hexdigest())
                for name, data in parts.items()]
    return dict(sh4d=dict(update_sha256=SH_UPDATE_SHA256, components=inventory(sh),
                         c1=manifest, exact_windows=windows,
                         c0=header(sh['DD013_C0A_up.bin'])),
                tr8s=dict(update_sha256=TR_UPDATE_SHA256, components=inventory(tr),
                         c0=header(tr['rpg42_m0c0a_up.bin']), plaintext_c1_component_present=False),
                execution_ready=False,
                limitations=['Shared windows do not establish common external routes or whole-function semantics.',
                             'The inspected TR-8S update supplies no readable CORE1 component.',
                             'No decryption, installation, target execution or physical-chip compatibility proof.'])


if __name__ == '__main__':
    from core1 import Core1
    corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1]/'local'))
    result = report((corpus/'crossmodel/sh-4d/SH4d_UPA_up.bin').read_bytes(),
                    (corpus/'crossmodel/tr-8s/TR8S_UP.bin').read_bytes(),
                    Core1(corpus/'b0c1a.bin'))
    target = Path(__file__).resolve().parents[1]/'local/additional-firmware-study.json'
    target.write_text(json.dumps(result, indent=2)+'\n')
    print('SH-4d: three exact windows; TR-8S: encrypted application and parameters only')

"""Inspect pinned official AX-Edge/JUNO-X updates offline; never execute vendor code."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile

from additional_firmware_study import FANTOM_SHA256, find_windows
from core0_ciphertext_study import INPUTS as C0_INPUTS, payload_blocks
from key_material_scan import scan
from qspi_c1 import parse_c1

INPUTS = {
    'ax-edge': ('KY022_UPA_up.bin', 'a9d0e103d7a16619b4a84045cd55c56312fd291411f4dd66ff5d2ea9fa815a60',
                {'KY022_C1A_up.bin', 'KY022_C1C_up.bin', 'KY022_C0A_up.bin',
                 'KY022_C0C_up.bin', 'KY022_WV0_up.bin'}),
    'juno-x': ('JUNOX_UPA_up.bin', '83516fc8a459879a976033fd68fe551b350bbd084e4ec78704885208142fbc5e',
               {'JUNOX_C1A_up.bin', 'JUNOX_C1C_up.bin', 'JUNOX_C0A_up.bin',
                'JUNOX_C0C_up.bin', 'JUNOX_SUB_up.bin'}),
}


def update_parts(path, expected):
    """Hash before parsing; read regular members without extracting their paths."""
    with Path(path).open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError('Unsupported official update digest')
    names, total = set(), 0
    with tarfile.open(path, 'r:') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            total += member.size
            if (not member.isfile() or name.is_absolute() or '..' in name.parts
                    or name.name in names or not 0 < member.size <= 0x8000000
                    or total > 0xa000000 or len(names) >= 32):
                raise ValueError('Unsupported archive member or scope')
            names.add(name.name)
            with archive.extractfile(member) as stream:
                data = stream.read()
            if len(data) != member.size:
                raise ValueError('Truncated firmware member')
            yield name.name, data


def study(corpus):
    from core1 import Core1
    corpus = Path(corpus)
    reference = Core1(corpus/'b0c1a.bin')
    if hashlib.sha256(reference.data).hexdigest() != FANTOM_SHA256:
        raise ValueError('Unsupported Fantom comparison digest')
    c0_name, c0_hash = C0_INPUTS['fantom0']
    c0 = (corpus/c0_name).read_bytes()
    if hashlib.sha256(c0).hexdigest() != c0_hash:
        raise ValueError('Unsupported Fantom CORE0 digest')
    _, baseline = payload_blocks(c0)
    patterns = []
    for name, address, length in (('MMIO read prefix', 0x6102d2e6, 324),
                                  ('RAMCLR body', 0x61056b14, 158),
                                  ('DRAM-IO low23 rewrite', 0x0113383c, 14)):
        offset = reference.offset(address)
        patterns.append((name, reference.data[offset:offset+length]))
    results = []
    for model, (filename, digest, expected_names) in INPUTS.items():
        rows, c1, c0_info = [], None, None
        for name, data in update_parts(corpus/'crossmodel'/model/filename, digest):
            rows.append(dict(name=name, **scan(data)))
            if name.endswith('_C1A_up.bin'):
                manifest, view = parse_c1(data)
                c1 = dict(manifest=manifest, exact_windows=find_windows(manifest, view, patterns))
            if name.endswith('_C0A_up.bin'):
                info, blocks = payload_blocks(data)
                c0_info = dict(header=info, distinct_nontrivial_blocks=len(blocks),
                               shared_with_fantom0=len(blocks & baseline))
        if {row['name'] for row in rows} != expected_names or c1 is None or c0_info is None:
            raise ValueError('Unexpected official component inventory')
        results.append(dict(model=model, update_sha256=digest, components=rows, c1=c1, c0=c0_info))
    return dict(models=results, key_recovered=False, decryption_performed=False,
                hardware_execution=False, execution_ready=False,
                limits=['ROM scan covers exact reported identities/vector prefixes and address anchors only.',
                        'Other compression, transformed keys and unknown ROM revisions remain outside this scan.',
                        'Exact code/ciphertext windows do not establish common external routes or whole-function semantics.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Detailed ignored local JSON report')
    args = parser.parse_args()
    try:
        corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1]/'local'))
        result = study(corpus)
        if args.out:
            args.out.write_text(json.dumps(result, indent=2)+'\n')
        for row in result['models']:
            print(row['model'], len(row['components']), 'components;', row['c0']['shared_with_fantom0'],
                  'ciphertext blocks shared with Fantom;',
                  sum(len(window['hits']) for window in row['c1']['exact_windows']), 'exact code-window hits')
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(2, f'{error}\n')

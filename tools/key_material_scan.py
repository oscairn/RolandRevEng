"""Search local firmware for two conflicting reported MC-101 ROM identities; no key output."""
import hashlib
import json
import os
from pathlib import Path
import struct
import tarfile
import tempfile

ROM_SIZE = 0x4000
ROM_IDENTITIES = {
    '742b1dd61d07509d8c72a1c7bcf3a44b9707e72d31543e3256415eb4307e60d5': 'docs/boot_rom_analysis.md',
    '2ac61a90d721a87753917c49fde45df2703e03fdaf6301adb00456093759d0b2': 'README.md',
}
ROM_VECTOR_PREFIX = struct.pack('<II', 0x01060000, 0x012000d1)
ANCHORS = {'rom_base': 0x01200000, 'rom_key_table': 0x012023b0,
           'selected_b6_entry': 0x012034c0, 'des_key_registers': 0x40020400,
           'crypto_control': 0xb6020001}


def offsets(data, needle):
    count, samples, cursor = 0, [], 0
    while (cursor := data.find(needle, cursor)) >= 0:
        count += 1
        if len(samples) < 16:
            samples.append(cursor)
        cursor += 1
    return dict(count=count, first_offsets=samples, offsets_truncated=count > len(samples))


def scan(data):
    """Only metadata leaves this scanner; pointer literals are not treated as keys."""
    vector = offsets(data, ROM_VECTOR_PREFIX)
    windows, exact, cursor = [], [], 0
    while (cursor := data.find(ROM_VECTOR_PREFIX, cursor)) >= 0:
        complete = cursor + ROM_SIZE <= len(data)
        digest = hashlib.sha256(data[cursor:cursor+ROM_SIZE]).hexdigest() if complete else None
        if digest in ROM_IDENTITIES:
            exact.append(cursor)
        if len(windows) < 16:
            windows.append(dict(offset=cursor, complete_16k_window=complete, sha256=digest,
                                matches_documented_rom=digest in ROM_IDENTITIES))
        cursor += 1
    digest = hashlib.sha256(data).hexdigest()
    if len(data) == ROM_SIZE and digest in ROM_IDENTITIES and 0 not in exact:
        exact.append(0)
    return dict(size=len(data), sha256=digest, vector_prefix=vector, vector_windows=windows,
                exact_documented_rom_offsets=exact,
                literal_address_anchors={name: offsets(data, struct.pack('<I', value))
                                         for name, value in ANCHORS.items()},
                documented_rom_found=bool(exact), rom_identity_verified=False,
                key_bytes_emitted=False)


def study(corpus):
    from core1 import Core1
    from core1_wait_study import IMAGE_SHA256, expand_initial_data
    from qspi_c1 import parse_c1
    corpus = Path(corpus)
    rows, by_digest, expansions = [], {}, []

    def record(label, data, provenance):
        digest = hashlib.sha256(data).hexdigest()
        if digest in by_digest:
            by_digest[digest]['aliases'].append(label)
            return
        row = dict(label=label, aliases=[], provenance=provenance, **scan(data))
        by_digest[digest] = row
        rows.append(row)

    reference = Core1(corpus/'b0c1a.bin')
    if hashlib.sha256(reference.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Unknown reference image for verified initial-data handler')
    handler_offset = reference.offset(0x6100003c)
    handler = reference.data[handler_offset:handler_offset+0x5a]

    def initial_data(label, data, qspi=False):
        if qspi:
            manifest, view = parse_c1(data)
        else:
            view = data
        with tempfile.TemporaryDirectory(prefix='bmc-keyscan-view-') as folder:
            path = Path(folder)/'analysis-view.bin';path.write_bytes(view)
            core = Core1(path)
        selected = []
        for r in core.scatter():
            try:
                off = core.offset(r['handler'])
                if core.data[off:off+0x5a] != handler:
                    continue
                source = core.offset(r['source'])
            except ValueError:
                continue
            # Only this verified byte-identical handler is interpreted, never arbitrary code.
            source_end = core.eram_offset if source < core.eram_offset else len(core.data)
            expanded, consumed = expand_initial_data(core.data[source:source_end], r['length'])
            name = f"{label}:initial-data@{r['destination']:08x}"
            record(name, expanded, dict(kind='verified-handler-expansion', parent=label,
                   source_runtime=r['source'], source_bytes_consumed=consumed,
                   destination_runtime=r['destination'], handler=r['handler']))
            selected.append(dict(destination=r['destination'], size=len(expanded),
                                 source=r['source'], consumed=consumed))
        expansions.append(dict(label=label, scatter_records=len(core.scatter()),
                               recognized_expansions=selected,
                               other_handlers_not_interpreted=True))

    for name in ('b0c1a.bin', 'b1c1a.bin', 'bmc0_MI078_C0A_up.bin',
                 'bmc1_MI078_C0A_up.bin', 'mi078', 'qctest'):
        data = (corpus/name).read_bytes()
        record(name, data, dict(kind='local-artifact'))
        if name in ('b0c1a.bin', 'b1c1a.bin'):
            initial_data(name, data)
    updates = [('mc101', 'MC101_UPA_up.bin'), ('jupiter-x', 'MI077_UPA_up.bin'),
               ('sh-4d', 'SH4d_UPA_up.bin'), ('tr-8s', 'TR8S_UP.bin')]
    for model, filename in updates:
        path = corpus/'crossmodel'/model/filename
        parent_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        with tarfile.open(path, 'r:') as archive:
            members = archive.getmembers()
            if len(members) > 128 or sum(m.size for m in members if m.isfile()) > 0x10000000:
                raise ValueError('Archive exceeds the bounded local firmware scope')
            for member in members:
                if not member.isfile():
                    continue
                if not 0 < member.size <= 0x4000000:
                    raise ValueError('Firmware component exceeds supported size')
                data = archive.extractfile(member).read()
                label = f'{model}/{filename}:{member.name}'
                record(label, data, dict(kind='tar-member', parent_sha256=parent_hash,
                                        member_name=member.name, component_size=member.size))
                if member.name.endswith('_C1A_up.bin') and data[0x20:0x24] == b'QSPI':
                    initial_data(label, data, qspi=True)
    return dict(reported_rom_identities=ROM_IDENTITIES, known_rom_size=ROM_SIZE,
                rom_identity_verified=False,
                known_key_entry_offset=0x34c0, objects=rows, initial_data_expansions=expansions,
                unique_objects=len(rows), total_scanned_bytes=sum(r['size'] for r in rows),
                exact_rom_copies=sum(len(r['exact_documented_rom_offsets']) for r in rows),
                key_bytes_emitted=False,
                limits=['Searches a documented ROM identity and literal anchors, not arbitrary candidate keys.',
                        'A pointer/control constant is not key material; missing literals do not prove missing keys.',
                        'Other compression, synthesized constants, unrecognized ROM revisions and opaque payloads remain unresolved.',
                        'No target execution, hardware read, decryption attempt or key guess is performed.'])


if __name__ == '__main__':
    corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1]/'local'))
    result = study(corpus)
    out = Path(__file__).resolve().parents[1]/'local/key-material-scan.json'
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('unique_objects', 'total_scanned_bytes', 'exact_rom_copies', 'key_bytes_emitted')}))

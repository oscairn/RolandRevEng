"""Fail-closed census of indexed-transfer memory operands in render programs.

Lane A5 scoping step named by run 19: which memory spaces stock render programs
address through the admitted indexed-transfer control form, in which direction,
at which addresses, and in how many programs. Inventory only: no instruction
semantics, no opcode admission, no hardware claim.

The admitted transfer form is the fragment emulator's: a control word with bits
4..11 equal 0xfe0 and bit 0 clear; its low nibble halves to a shared-pool
halfword index and its top nibble is the port. The direction convention is the
emulator's: ports 0..7 load, 8..15 store (port 11 occurs only in corpus images,
never in an admitted fragment profile). The 16-bit pool word's top nibble is
reported here as the address tag; only tags 0/2/4/c have native provenance
(transfer-spaces-study.md). Tags 1/3 are near-singleton and every occurrence is
recorded verbatim in rare_contexts, as is tag f, so rare-syntax questions stay
inspectable without a rerun.

Framing: the two pinned CORE1 payloads and the three cross-model QSPI images use
program_slot_census.frame_lists (count <= 64, run 19's accepted framing;
analyze.core_lists caps count at 16 and drops b1c1a's long dsp0..3 base-0
lists). The desktop ZENOLOGY arm64 image uses the accepted
zenology_inventory.json lists (runs 4/11); its 305 stored segments include 128
that do not packet-decode and are counted, not fatal. All images are hash-pinned.
"""
import collections
import hashlib
import json
from pathlib import Path
import tempfile

from bmc_dsp import command_count, packets, swap_words
from program_slot_census import frame_lists

B0C1A = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'
B1C1A = 'c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd'
CORE_HASHES = {'b0c1a': B0C1A, 'b1c1a': B1C1A}
ZEN_SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'
QSPI_PATHS = (
    'crossmodel/jupiter-x/MI077_C1A_up.bin',
    'crossmodel/mc101/RPG69_C1A_up.bin',
    'crossmodel/sh-4d/DD013_C1A_up.bin',
)
# Tags with singleton or near-singleton corpus use; every access context is
# recorded so rare-syntax questions stay inspectable without a rerun.
RARE_TAGS = frozenset({1, 3, 0xF})
NATIVE_PROVENANCED_TAGS = frozenset({0, 2, 4, 0xC})


def transfer_form(word):
    """The admitted indexed-transfer control form; bit 0 set is another form."""
    return (word & 0xff0) == 0xfe0 and not word & 1


def scan_segments(data, segments):
    """Scan framed (segment, dsp) pairs; unknown shapes are counted, not fatal.

    Segments whose stored bytes do not packet-decode are counted unframeable
    (the pinned b1c1a data segment is one). A transfer whose pool index exceeds
    the packet's pool is counted, never guessed.
    """
    counts = collections.Counter()
    rows = {tag: dict(accesses=0, loads=0, stores=0, addresses=set(),
                      programs=set(), dsps=set())
            for tag in range(16)}
    rare = []
    for segment, dsp in segments:
        base, length, capacity, source = segment
        if not length:
            continue
        chunk = data[source:source + ((length + 3) & ~3)]
        stream = swap_words(chunk)[:length]
        try:
            decoded = packets(stream)
        except ValueError:
            counts['unframeable_segments'] += 1
            continue
        counts['framed_segments'] += 1
        counts['framed_packets'] += len(decoded)
        for offset, words in decoded:
            count = command_count(words[0])
            controls, pool = words[1:1 + count], words[1 + count:]
            for word in controls:
                if word & 0xff0 == 0xfe0 and word & 1:
                    counts['odd_form_controls'] += 1
                    continue
                if not transfer_form(word):
                    continue
                counts['transfer_controls'] += 1
                index, port = (word & 15) // 2, word >> 12
                counts[f'port_{port:x}'] += 1
                if index >= len(pool):
                    counts['pool_index_overflow'] += 1
                    continue
                address = pool[index]
                tag = address >> 12
                row = rows[tag]
                row['accesses'] += 1
                row['loads' if port < 8 else 'stores'] += 1
                row['addresses'].add(address & 0xfff)
                row['programs'].add((dsp, base))
                row['dsps'].add(dsp)
                if tag in RARE_TAGS:
                    rare.append(dict(dsp=dsp, base=base, length=length,
                                     offset=offset, header=words[0],
                                     controls=[f'{w:04x}' for w in controls],
                                     pool=[f'{w:04x}' for w in pool],
                                     port=port, address=f'{address:04x}'))
    tags = {}
    for tag in range(16):
        row = rows[tag]
        tags[f'{tag:x}'] = dict(
            accesses=row['accesses'], loads=row['loads'], stores=row['stores'],
            distinct_addresses=len(row['addresses']),
            min_address=min(row['addresses']) if row['addresses'] else None,
            max_address=max(row['addresses']) if row['addresses'] else None,
            programs=len(row['programs']), dsps=sorted(row['dsps']))
    return dict(counts=dict(sorted(counts.items())), tags=tags,
                rare_contexts=rare)


def core_segments(path):
    """Framed segments of a header-stripped CORE1 payload via run 19 framing."""
    from core1 import Core1
    core = Core1(path)
    return core.data, [((segment['base'], segment['length'],
                         segment['capacity'], segment['source']), row['dsp'])
                       for row in frame_lists(core) for segment in row['segments']]


def qspi_segments(path):
    """Framed segments of a QSPI C1A member pair through its analysis view."""
    from qspi_c1 import read_c1
    from core1 import Core1
    _manifest, view = read_c1(path)
    with tempfile.TemporaryDirectory(prefix='render-transfer-') as directory:
        image = Path(directory) / 'analysis.bin'
        image.write_bytes(view)
        core = Core1(image)
        data = bytes(core.data)
        segments = [((segment['base'], segment['length'],
                      segment['capacity'], segment['source']), row['dsp'])
                    for row in frame_lists(core) for segment in row['segments']]
    return data, segments


def zen_segments(base):
    """Framed segments of the desktop image through the accepted inventory."""
    import lib
    inventory = json.loads((base / 'zenology_inventory.json').read_text())
    return lib.Z, [((segment[0], segment[1], segment[2], segment[3]), row[1])
                   for row in inventory['lists'] for segment in row[3]]


def study(corpus_dir='local'):
    """Census every prepared image; skip absent ones, require at least one."""
    base = Path(corpus_dir)
    sources = []
    if (base / 'zen_arm64').exists() and (base / 'zenology_inventory.json').exists():
        digest = hashlib.sha256((base / 'zen_arm64').read_bytes()).hexdigest()
        if digest != ZEN_SHA256:
            raise SystemExit(f'Unexpected zen_arm64 SHA-256 {digest}')
        inventory = json.loads((base / 'zenology_inventory.json').read_text())
        if inventory.get('sha256') != ZEN_SHA256:
            raise ValueError('zenology_inventory.json does not pin zen_arm64')
        sources.append(('zen_arm64', zen_segments(base)))
    for name, digest in sorted(CORE_HASHES.items()):
        path = base / f'{name}.bin'
        if not path.exists():
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'Unexpected {name} SHA-256 '
                             f'{hashlib.sha256(path.read_bytes()).hexdigest()}')
        sources.append((name, core_segments(path)))
    for rel in QSPI_PATHS:
        path = base / rel
        if not path.exists():
            continue
        sources.append((path.name, qspi_segments(path)))
    if not sources:
        raise ValueError('No prepared corpus image found under BMC_CORPUS_DIR')
    result = collections.OrderedDict()
    totals = collections.Counter()
    for name, (data, segments) in sources:
        report = scan_segments(data, segments)
        totals.update(report['counts'])
        for tag, row in report['tags'].items():
            totals[f'tag_{tag}_accesses'] += row['accesses']
        result[name] = report
    result['totals'] = dict(sorted(totals.items()))
    observed = {tag for tag in range(16)
                if result['totals'].get(f'tag_{tag:x}_accesses')}
    result['totals']['observed_tags'] = [f'{tag:x}' for tag in sorted(observed)]
    result['totals']['absent_tags'] = [f'{tag:x}' for tag in
                                       sorted(set(range(16)) - observed)]
    result['totals']['native_provenanced_tags'] = sorted(
        f'{t:x}' for t in NATIVE_PROVENANCED_TAGS)
    result['opcode_admission'] = False
    result['hardware_verified'] = False
    return result


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(study(os.environ.get('BMC_CORPUS_DIR', 'local')),
                     indent=2))


if __name__ == '__main__':
    main()
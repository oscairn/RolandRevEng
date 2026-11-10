"""Reproduce structural findings without running a plugin or touching hardware."""
import collections
import hashlib
import json
from pathlib import Path
import struct

from bmc_dsp import assemble, command_count, literal, packets, swap_words
from core1 import Core1
import lib


def core_lists(core):
    data, result = core.data, []
    for offset in range(0, len(data) - 8, 4):
        kind, dsp, count, pad, pointer = struct.unpack_from('<BBBBI', data, offset)
        if kind or dsp > 6 or not 1 <= count <= 16 or pad or pointer % 4:
            continue
        try:
            table = core.offset(pointer)
        except ValueError:
            continue
        if table + 16 * count > len(data):
            continue
        segments = []
        for index in range(count):
            base, length, capacity, source = struct.unpack_from('<4I', data, table + 16 * index)
            if base > 0x20000 or length % 2 or not 0 <= length <= capacity <= 0x10000 or not capacity or source % 4:
                break
            try:
                source_offset = core.offset(source)
            except ValueError:
                break
            if source_offset + ((length + 3) & ~3) > len(data):
                break
            segments.append([base, length, capacity, source_offset])
        if len(segments) == count:
            result.append(dict(payload_offset=offset, dsp=dsp, segments=segments))
    return result


def check_segments(data, segments):
    counts, headers, failures, rows = collections.Counter(), collections.Counter(), [], []
    for name, base, length, capacity, offset in segments:
        if not length:
            continue
        stream = swap_words(data[offset:offset + ((length + 3) & ~3)])[:length]
        try:
            decoded = packets(stream)
            if assemble(words for _, words in decoded) != stream:
                raise AssertionError('Packet round trip changed the stream')
        except ValueError as error:
            failures.append(dict(name=name, base=base, offset=offset, error=str(error)))
            continue
        counts['segments'] += 1
        counts['bytes'] += length
        counts['packets'] += len(decoded)
        counts['long_packets'] += sum(len(words) > 15 for _, words in decoded)
        counts['compact_001f'] += sum(words == [31] for _, words in decoded)
        counts['compact_0001'] += sum(words == [1] for _, words in decoded)
        for _, words in decoded:
            count = command_count(words[0])
            for word in words[1:1 + count]:
                if word & 0xff0 == 0xfe0 and not word & 1:
                    counts['indexed_transfers'] += 1
                    if 1 + count + (word & 15) // 2 >= len(words):
                        raise AssertionError(f'{name}: transfer operand outside packet')
        headers.update(words[0] for _, words in decoded)
        rows.append(dict(name=name, base=base, length=length, capacity=capacity,
                         offset=offset, packets=len(decoded)))
    return dict(counts=counts, headers={f'{word:04x}': count for word, count in headers.most_common()},
                failures=failures, segments=rows)


def coefficient_widths(inventory):
    """Use actual _CoefSym width records, never a best-fit literal length."""
    data = lib.Z
    image_starts = sorted({s[3] for item in inventory['lists'] for s in item[3] if s[1]})
    counts, rows = collections.Counter(), []
    for cls, (defaults, driver, lists) in lib.pairs().items():
        render = [item for item in lists or [] if item[1] == 0]
        if not render:
            continue
        primary = max(render[0][3], key=lambda s: s[1])
        base, length, capacity, source = primary
        stream = swap_words(data[source:source + ((length + 3) & ~3)])[:length]
        starts = [s[3] + ((s[1] + 3) & ~3) for item in lists for s in item[3]]
        start = max(starts)
        end = min(next((p for p in image_starts if p >= start), len(data)), start + 0x4000)
        for relative, native, raw_double in defaults:
            if relative == 0:
                counts['non_literal_default_records'] += 1
                continue
            if relative is None or relative >= length:
                counts['outside_primary'] += 1
                continue
            symbol = struct.pack('<II', base + relative, relative)
            pos, widths, matches = start, set(), []
            while (pos := data.find(symbol, pos, end)) >= 0:
                if pos + 12 <= end:
                    kind = struct.unpack_from('<I', data, pos + 8)[0]
                    if kind in (2, 3, 4):
                        widths.add(kind)
                        matches.append(pos)
                pos += 4
            if len(widths) != 1:
                counts['unresolved_width'] += 1
                continue
            width = next(iter(widths))
            if relative + width > length:
                raise AssertionError(f'{cls}: literal outside program')
            encoded = stream[relative:relative + width]
            decoded = literal(encoded)
            quantum = 2.0 ** (-24 + 4 * ((encoded[0] >> 5) & 3) + 8 * (3 - width))
            error = abs(decoded - native)
            counts[f'width_{width}'] += 1
            counts['exact' if error == 0 else 'within_lsb' if error <= quantum else 'different'] += 1
            rows.append(dict(cls=cls, relative=relative, width=width, symbol_offsets=matches,
                             native=native, decoded=decoded, error=error, quantum=quantum))
    return dict(counts=counts, records=rows)


def paired_layout():
    counts = collections.Counter()
    for cls, (defaults, driver, lists) in lib.pairs().items():
        render = [item for item in lists or [] if item[1] == 0]
        if not render:
            continue
        segments = render[0][3]
        primary = max(segments, key=lambda s: s[1])
        peer = next((s for s in segments if s is not primary and s[1] == primary[1]), primary)
        def read(segment):
            _, length, _, source = segment
            return swap_words(lib.Z[source:source + ((length + 3) & ~3)])[:length]
        first, second = read(primary), read(peer)
        for offset, words in packets(first):
            count = command_count(words[0])
            boundary = offset + 2 * (count + 1)
            counts['packets'] += 1
            for index, word in enumerate(words):
                position = offset + 2 * index
                if first[position:position + 2] != second[position:position + 2]:
                    counts['relocating_words'] += 1
                    if position < boundary:
                        raise AssertionError(f'{cls}: relocation changes a control word')
            for relative, *_ in defaults:
                if relative and offset <= relative < offset + 2 * len(words):
                    counts['native_literal_anchors'] += 1
                    if relative < boundary:
                        raise AssertionError(f'{cls}: literal overlaps control words')
            for word in words[1:1 + count]:
                if word & 0xff0 == 0xfe0 and not word & 1:
                    counts['indexed_transfers'] += 1
                    if count + 1 + (word & 15) // 2 >= len(words):
                        raise AssertionError(f'{cls}: indexed operand outside payload')
    return counts


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / 'evidence'
    out.mkdir(exist_ok=True)
    inventory = json.loads((lib.BASE / 'zenology_inventory.json').read_text())
    segments = [(hex(item[0]), *segment) for item in inventory['lists'] if item[1] == 0
                for segment in item[3]]
    zen = check_segments(lib.Z, segments)
    summary = dict(zenology_sha256=hashlib.sha256(lib.Z).hexdigest(), zenology=zen,
                   paired_render_classes=sum(any(p[1] == 0 for p in v[2] or []) for v in lib.pairs().values()))
    summary['paired_layout'] = paired_layout()
    for filename in ('b0c1a.bin', 'b1c1a.bin'):
        core = Core1(lib.BASE / filename)
        lists = core_lists(core)
        segments = [(f'{r["payload_offset"]:#x}/DSP{r["dsp"]}', *s) for r in lists for s in r['segments']]
        result = check_segments(core.data, segments)
        result.update(sha256=hashlib.sha256(core.data).hexdigest(), eram_offset=core.eram_offset,
                      scatter=core.scatter(), lists=lists)
        summary[filename] = result
    coefficients = coefficient_widths(inventory)
    (out / 'coefficient_widths.json').write_text(json.dumps(coefficients, indent=2) + '\n')
    (out / 'analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
    aggregate = dict(
        artifacts={name: dict(sha256=summary['zenology_sha256'] if name == 'zenology' else summary[name]['sha256'],
                              counts=summary[name]['counts'], distinct_headers=len(summary[name]['headers']),
                              failed_segments=len(summary[name]['failures']))
                   for name in ('zenology', 'b0c1a.bin', 'b1c1a.bin')},
        paired_render_classes=summary['paired_render_classes'],
        paired_layout=summary['paired_layout'], coefficient_checks=coefficients['counts'])
    (out / 'summary.json').write_text(json.dumps(aggregate, indent=2) + '\n')
    for name in ('zenology', 'b0c1a.bin', 'b1c1a.bin'):
        result = summary[name]
        print(name, dict(result['counts']), f'{len(result["headers"])} headers',
              f'{len(result["failures"])} failures')
    print('coefficient widths', dict(coefficients['counts']))
    print('paired layout', dict(summary['paired_layout']))
    if any(summary[key]['failures'] for key in ('zenology', 'b0c1a.bin', 'b1c1a.bin')):
        raise SystemExit('Some candidate render segments remain undecoded; see evidence/analysis.json')


if __name__ == '__main__':
    main()

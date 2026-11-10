"""Locate owner-proven DSP4 test-oscillator literals; assign no oscillator opcodes."""
import json
import os
from pathlib import Path
import struct

from bmc_dsp import command_count, literal, packets, swap_words
from header_study import layout, UnsupportedLayout


def anchor_packets(stream, anchors):
    decoded, result = packets(stream), []
    for anchor in anchors:
        relative, width = anchor['relative'], anchor['width']
        if width not in (2, 3, 4) or relative < 0 or relative + width > len(stream):
            raise ValueError('Coefficient anchor outside program or unsupported width')
        offset, words = next((offset, words) for offset, words in decoded
                             if offset <= relative < offset + 2 * len(words))
        if relative < offset + 2 * (1 + command_count(words[0])) or relative + width > offset + 2 * len(words):
            raise ValueError('Coefficient anchor overlaps controls or next packet')
        row = dict(anchor, packet_offset=offset, header=words[0],
                   value=literal(stream[relative:relative + width]))
        try:
            fields = layout(words)['fields']
            row['layout_matches'] = [field for field in fields if field['role'] == 'literal'
                                     and field['offset'] + offset == relative and field['width'] == width]
        except (UnsupportedLayout, ValueError) as error:
            row['layout_error'] = str(error)
        result.append(row)
    return result


def study():
    from core1 import Core1
    corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1] / 'local'))
    core = Core1(corpus / 'b0c1a.bin')
    kind, dsp, count, _, table = struct.unpack_from('<4BI', core.data, core.offset(0x610a1f18))
    if kind != 0 or dsp != 4 or not count:
        raise ValueError('Not the studied ordinary DSP4 program list')
    base, length, capacity, source = struct.unpack_from('<4I', core.data, core.offset(table))
    if not 0 < length <= capacity:
        raise ValueError('Invalid primary segment length')
    pos = core.offset(source)
    stream = swap_words(core.data[pos:pos + ((length + 3) & ~3)])[:length]
    anchors = []
    for name, symbol in [('SineFreq', 0x610a2114), ('SineLev', 0x610a2124),
                         ('ImpulseRate', 0x610a20b4), ('ImpulseLev', 0x610a20a4),
                         ('WhiteLev', 0x610a2154), ('DCLev', 0x610a2094)]:
        record = core.u32(symbol + 8)
        if core.data[core.offset(symbol + 12)] != 1:
            raise ValueError('Expected one owner-proven coefficient record')
        absolute, relative, width, segment = struct.unpack_from('<IIBB', core.data, core.offset(record))
        if absolute != base + relative or segment != 0:
            raise ValueError('Coefficient is not in the primary segment')
        anchors.append(dict(name=name, symbol=symbol, relative=relative, width=width))
    return dict(list_address=0x610a1f18, base=base, length=length, source=source,
                anchors=anchor_packets(stream, anchors))


if __name__ == '__main__':
    result = study()
    (Path(__file__).resolve().parents[1] / 'local/oscillator-regions-study.json').write_text(
        json.dumps(result, indent=2) + '\n')
    for anchor in result['anchors']:
        print(anchor['name'], hex(anchor['packet_offset']), hex(anchor['header']),
              anchor.get('layout_error', anchor.get('layout_matches')))

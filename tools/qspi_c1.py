"""Read the observed two-member QSPI C1A format; never modify the update file."""
import hashlib
from pathlib import Path
import re
import struct
import zlib


def parse_c1(data):
    """Return original-file metadata and an explicitly synthetic CORE1 analysis view.

    The returned view concatenates idm1/sdram1 after their zero prefixes. It has no
    padding for the unmapped ITCM gap and is not a flashable or original image.
    """
    if len(data) < 0xa4 or data[0x20:0x24] != b'QSPI':
        raise ValueError('Expected a QSPI C1A container')
    end = len(data) - 0x34
    declared = struct.unpack_from('<I', data)[0]
    header, stride, count = struct.unpack_from('<3I', data, 0x24)
    expected = struct.unpack_from('<I', data, end)[0]
    actual = zlib.crc32(data[:end])
    if declared != end + 4 or (header, stride, count) != (32, 32, 2):
        raise ValueError('Unsupported QSPI C1A header layout')
    if expected != actual:
        raise ValueError('QSPI outer CRC32 mismatch')
    footer = data[-48:].rstrip(b'\0 \r\n')
    if not footer.startswith(b'Roland ') or any(c < 32 or c > 126 for c in footer):
        raise ValueError('Unsupported identification footer')
    members, names, spans, payloads = [], set(), [], {}
    for index in range(count):
        entry = 0x30 + stride*index
        raw_name = data[entry:entry+16].split(b'\0', 1)[0]
        if not re.fullmatch(rb'[A-Za-z0-9_.-]+', raw_name) or raw_name in (b'.', b'..'):
            raise ValueError('Invalid member name')
        name = raw_name.decode('ascii')
        offset, length, checksum, reserved = struct.unpack_from('<4I', data, entry+16)
        if name in names or reserved or offset % 4 or length < 40 or length % 4:
            raise ValueError('Unsupported member metadata')
        if offset < 0x30 + stride*count or offset + length > end:
            raise ValueError('Member outside container data area')
        if any(offset < hi and lo < offset + length for lo, hi in spans):
            raise ValueError('Overlapping QSPI members')
        raw = data[offset:offset+length]
        if raw[:32] != bytes(32):
            raise ValueError('Unsupported member prefix; expected 32 zero bytes')
        additive = sum(word[0] for word in struct.iter_unpack('<H', raw)) & 0xffff
        members.append(dict(name=name, offset=offset, size=length,
                            sha256=hashlib.sha256(raw).hexdigest(), checksum_field=checksum,
                            additive_u16=additive, additive_u16_matches=checksum == additive))
        names.add(name)
        spans.append((offset, offset+length))
        payloads[name] = raw[32:]
    if names != {'idm1.bin', 'sdram1.bin'}:
        raise ValueError('Expected exactly idm1.bin and sdram1.bin')
    combined = payloads['idm1.bin'] + payloads['sdram1.bin']
    by_name = {m['name']: m for m in members}
    regions = [dict(name=name, runtime_base=base,
                    source_offset=by_name[name]['offset']+32,
                    size=len(payloads[name]), analysis_offset=analysis)
               for name, base, analysis in (('idm1.bin', 0x01100000, 0),
                   ('sdram1.bin', 0x61000000, len(payloads['idm1.bin'])))]
    return dict(container_size=len(data), container_sha256=hashlib.sha256(data).hexdigest(),
                footer_crc32=actual, footer_crc32_valid=True, footer_id=footer.decode('ascii'),
                members=members, regions=regions,
                analysis_view_sha256=hashlib.sha256(combined).hexdigest(),
                analysis_view_is_original=False), combined


def read_c1(path):
    return parse_c1(Path(path).read_bytes())

#!/usr/bin/env python3
"""Cross-check the measured 0xEF settings traffic against pinned mi078.

Static, read-only analysis of the pinned Fantom-0 v1.08 `mi078` ELF plus the
saved unit strace captures. No device access, no execution. Companion to
docs/host-byte1-study.md (run 1 scanner), docs/host-status9-study.md (run 2)
and docs/host-status9-readers-study.md (run 3).

The unit captures show Roland's app sending settings traffic to destination
0xEF: kind-7 parameter blocks (selector 0x0E level, selector 0x01 system)
each immediately followed by a kind-8 companion frame, every frame with
source byte 1 = 0x00, and no reply ever sourced 0xEF. This tool verifies the
host half of the responder question:

- send side: every direct route call `bl 00be4270` with immediate route 0xEF,
  the constructor wrappers called in each enclosing function, and the
  immediate-stamp sites `mov w0, #0xef`,
- receive side: every `cmp #0xe1/#0xe2/#0xef` on the pinned image, classified
  into the known reply handlers (source byte 1 checks) and the non-frame
  sites, proving no receive path compares a frame's byte 1 to 0xEF,
- capture side: every write()/read() in the saved traces re-framed, counting
  the exact 0xEF frame shapes and every byte-1 value seen.
"""
import argparse
import hashlib
import io
import json
import re
import struct
from collections import Counter
from pathlib import Path

HOST_SHA256 = '90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7'
ROUTE = 0xbe4270
KIND7_WRAPPER, KIND8, KIND9_WRAPPER = 0xbe2b98, 0xbe2bf8, 0xbe2c60
KIND7, KIND9 = 0xbe3e38, 0xbe2968
BLOCK_LIMIT = 160
TRACE_FDS = {11: 'w', 10: 'r', 12: 'w'}  # fd -> direction per capture set

CONSTRUCTOR_NAMES = {
    KIND7_WRAPPER: 'kind7-wrapper',
    KIND7: 'kind7',
    KIND8: 'kind8',
    KIND9_WRAPPER: 'kind9-wrapper',
    KIND9: 'kind9',
}

ESC = re.compile(r'\\x([0-9a-f]{2})')
HEXDUMP = re.compile(
    r'\s*\|\s*[0-9a-f]{5}\s+((?:[0-9a-f]{2} ){1,8})\s?((?:[0-9a-f]{2} ){0,8})\s*\|')
WRITE = re.compile(r'^\d+\s+\S+\s+write\((\d+), ')
READ_START = re.compile(r'^\d+\s+\S+\s+read\((\d+)')
READ_RESUME = re.compile(r'^\d+\s+\S+\s+<\.\.\. \S+ resumed>.*?read\((\d+)')


def frames(data):
    """Decode the bounded wire layout (same rules as tools/bmc_ipc.py)."""
    offset = 0
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError(f'Truncated 12-byte prefix at {offset:#x}')
        prefix = data[offset:offset + 12]
        kind, variable = prefix[0] >> 1, bool(prefix[0] & 1)
        if kind > 9:
            raise ValueError(f'Unsupported message kind {kind} at {offset:#x}')
        if variable:
            if len(data) - offset < 16:
                raise ValueError(f'Truncated payload length at {offset:#x}')
            length = struct.unpack_from('<I', data, offset + 12)[0]
            end = offset + 16 + length
            payload = data[offset + 16:end]
        else:
            length = prefix[11]
            if length > 7:
                raise ValueError(
                f'Unsupported inline payload length {length} at {offset:#x}')
            end = offset + 12
            payload = prefix[4:4 + length]
        yield dict(offset=offset, kind=kind, variable=variable,
                   byte1=prefix[1], destination=prefix[2], selector=prefix[3],
                   payload=payload.hex(), payload_length=len(payload))
        offset = end


def syscall_bytes(path, fd, direction):
    """Concatenated payload bytes of every write(fd)/read(fd) in an strace."""
    buf = bytearray()
    pending = False
    for line in path.read_text(errors='replace').splitlines():
        if direction == 'w':
            match = WRITE.match(line)
            started = match and int(match.group(1)) == fd
        else:
            match = READ_START.match(line) or READ_RESUME.match(line)
            started = match and int(match.group(1)) == fd
        if started:
            pending = True
            buf += bytes(int(b, 16) for b in ESC.findall(line))
            continue
        if pending:
            dump = HEXDUMP.match(line)
            if dump:
                buf += bytes(int(b, 16)
                             for b in (dump.group(1) + dump.group(2)).split())
                continue
            pending = False
    return bytes(buf)


def text_rows(path):
    """Disassemble the pinned ELF's .text; hash-check it first."""
    import capstone
    from elftools.elf.elffile import ELFFile
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != HOST_SHA256:
        raise ValueError('Expected pinned Fantom-0 v1.08 mi078 ELF')
    elf = ELFFile(io.BytesIO(data))
    text = elf.get_section_by_name('.text')
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    return list(md.disasm(text.data(), text['sh_addr']))


def immediate(ins):
    from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG
    if ins.mnemonic not in ('mov', 'movz') or len(ins.operands) != 2:
        return None
    destination, source = ins.operands
    if destination.type == ARM64_OP_REG and source.type == ARM64_OP_IMM:
        return source.imm
    return None


def block_start(rows, index):
    """Start of the straight-line block ending at the call at index."""
    start = index
    while start > 0 and index - start < BLOCK_LIMIT:
        previous = rows[start - 1]
        if previous.mnemonic in ('bl', 'ret', 'br', 'b', 'cbz', 'cbnz',
                                 'tbz', 'tbnz'):
            break
        start -= 1
    return start


def call_site(route_value):
    """Return a matcher for `bl <target>` with the given immediate target."""
    def match(ins):
        if ins.mnemonic != 'bl':
            return False
        try:
            return int(ins.op_str.lstrip('#'), 0) == route_value
        except ValueError:
            return False
    return match


def enclosing_function(rows, order, address):
    """Backward scan to the nearest function entry (stp x29, x30 push)."""
    index = order.index(address)
    while index > 0:
        ins = rows[index]
        if (ins.mnemonic == 'stp' and 'x29, x30' in ins.op_str
                and '[sp, #' in ins.op_str):
            return ins.address
        index -= 1
    return rows[0].address


def send_census(rows):
    """Route calls with their immediate route argument.

    The straight-line block is enough for the route immediate: the register
    write and the call are adjacent at every verified site. Constructor
    classification is deliberately left to the enclosing-function census, the
    spot checks in the study note, and the capture cross-check; a proven
    per-site constructor would need a full dataflow pass.
    """
    calls = []
    for index, ins in enumerate(rows):
        if not call_site(ROUTE)(ins):
            continue
        block = rows[block_start(rows, index):index]
        route = None
        from capstone.arm64 import ARM64_OP_REG
        for member in block:
            value = immediate(member)
            if (value is not None
                    and member.operands[0].type == ARM64_OP_REG
                    and member.reg_name(member.operands[0].reg) == 'w0'):
                route = value
        calls.append(dict(call=ins.address, route=route))
    return calls


def enclosing_census(rows, order, calls):
    """Group each 0xEF route call by its enclosing function entry."""
    groups = {}
    for call in calls:
        entry = enclosing_function(rows, order, call['call'])
        groups.setdefault(entry, []).append(call['call'])
    return groups


def compare_census(rows):
    """Every `cmp #0xe1/#0xe2/#0xef` with six instructions of context."""
    from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG
    rows_by_address = {ins.address: ins for ins in rows}
    order = [ins.address for ins in rows]
    out = {}
    for value in (0xe1, 0xe2, 0xef):
        sites = []
        for index, ins in enumerate(rows):
            if ins.mnemonic != 'cmp' or len(ins.operands) != 2:
                continue
            register, source = ins.operands
            if (register.type == ARM64_OP_REG
                    and source.type == ARM64_OP_IMM
                    and source.imm == value):
                sites.append(ins.address)
        out[value] = sites
    return out


def compare_context(rows, order, address, before=6):
    """Disassembly lines before (and including) one address."""
    index = order.index(address)
    return [f'{ins.address:x}: {ins.mnemonic} {ins.op_str}'
            for ins in rows[max(0, index - before):index + 1]]


def capture_census(directory):
    """Re-frame every trace write and read; count shapes and byte-1 values."""
    captures = ('slider', 'rest', 'local', 'local2')
    result = {}
    for name in captures:
        path = directory / f'{name}.trace.raw'
        if not path.exists():
            continue
        written = syscall_bytes(path, 12, 'w')
        reads = bytearray()
        for fd in (10, 11):
            reads += syscall_bytes(path, fd, 'r')
        rows = list(frames(written))
        read_rows = list(frames(bytes(reads)))
        shapes = Counter((f['kind'], f['byte1'], f['destination'],
                          f['selector'], f['payload_length']) for f in rows)
        ef_kinds = Counter((f['kind'], f['selector'], f['payload_length'])
                            for f in rows if f['destination'] == 0xef)
        companions = 0
        last_kind7 = -1
        for index, f in enumerate(rows):
            if f['destination'] == 0xef and f['kind'] == 7:
                last_kind7 = index
            elif (f['destination'] == 0xef and f['kind'] == 8
                  and last_kind7 >= 0):
                # The companion is written by a separate call; unrelated frames
                # (MIDI clock, panel words) may be interleaved between the two.
                companions += 1
                last_kind7 = -1
        result[f'{name}.trace.raw'] = dict(
            frames=len(rows), shapes={str(k): v for k, v in shapes.items()},
            ef_shapes={str(k): v for k, v in ef_kinds.items()},
            kind7_followed_by_kind8=companions,
            write_byte1_values=sorted({f['byte1'] for f in rows}),
            read_frames=len(read_rows),
            read_shapes={str(k): v for k, v in Counter(
                (f['kind'], f['byte1'], f['destination'], f['selector'],
                 f['payload_length']) for f in read_rows).items()},
            read_byte1_values=sorted({f['byte1'] for f in read_rows}),
        )
    return result


def function_constructor_kinds(rows, order, entry):
    """Kinds any call inside one enclosing function constructs.

    Boundary: from the function entry to the next `stp x29, x30` prologue.
    This is a bounded structural classification of the *function*, not a
    proven constructor-to-route data dependency at each site.
    """
    start = order.index(entry)
    end = start + 1
    while end < len(rows):
        ins = rows[end]
        if (ins.mnemonic == 'stp' and 'x29, x30' in ins.op_str
                and '[sp, #-' in ins.op_str):
            break
        end += 1
    kinds = set()
    for member in rows[start:end]:
        if member.mnemonic != 'bl':
            continue
        try:
            target = int(member.op_str.lstrip('#'), 0)
        except ValueError:
            continue
        if target in CONSTRUCTOR_NAMES:
            kinds.add(CONSTRUCTOR_NAMES[target])
    return kinds


def static_report(host):
    rows = text_rows(host)
    order = [ins.address for ins in rows]
    calls = send_census(rows)
    ef_calls = [c for c in calls if c['route'] == 0xef]
    functions = {}
    for call in ef_calls:
        entry = enclosing_function(rows, order, call['call'])
        functions.setdefault(entry, []).append(call['call'])
    return dict(
        route_calls_total=len(calls),
        ef_route_calls=len(ef_calls),
        ef_call_sites=[hex(c['call']) for c in ef_calls],
        ef_functions={hex(entry): dict(
            calls=[hex(a) for a in sites],
            constructor_kinds=sorted(function_constructor_kinds(
                rows, order, entry)))
            for entry, sites in sorted(functions.items())},
        compares={hex(value): [hex(a) for a in sites]
                  for value, sites in compare_census(rows).items()},
        compare_contexts={hex(a): compare_context(rows, order, a)
                          for value in (0xe1, 0xe2, 0xef)
                          for a in compare_census(rows)[value]},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--captures', type=Path, default=None,
                        help='Directory holding the saved *.trace.raw files')
    args = parser.parse_args()
    report = static_report(args.image)
    if args.captures:
        report['captures'] = capture_census(args.captures)
    print(json.dumps(report, indent=2, default=dict))


if __name__ == '__main__':
    main()
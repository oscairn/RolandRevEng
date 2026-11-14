"""Local artifact access for the preserved SIM constructor and native operand readers.

parse.py and lift.py originated in the owner's 2026-11-09 analysis scratchpad.
They are heuristics, not complete ARM emulators. Validate their output against bytes.
"""
import bisect
import json
import os
from pathlib import Path
import struct

import capstone

BASE = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1] / 'local'))
Z = (BASE / 'zen_arm64').read_bytes()


def load_exports():
    return {name: int(addr, 16) for addr, name in
            (line.split('\t', 1) for line in (BASE / 'exports_dem.txt').read_text().splitlines())}


def func_starts():
    offset, starts = 32, []
    for _ in range(struct.unpack_from('<I', Z, 16)[0]):
        cmd, size = struct.unpack_from('<II', Z, offset)
        if cmd == 0x26:
            pos, length = struct.unpack_from('<II', Z, offset + 8)
            end, address = pos + length, 0
            while pos < end:
                value, shift = 0, 0
                while True:
                    byte = Z[pos]
                    pos += 1
                    value |= (byte & 127) << shift
                    shift += 7
                    if byte < 128:
                        break
                if not value:
                    break
                address += value
                starts.append(address)
        offset += size
    return starts


STARTS = func_starts()


def func(address):
    index = bisect.bisect_right(STARTS, address) - 1
    if index < 0 or index + 1 >= len(STARTS):
        raise ValueError(f'No bounded function at {address:#x}')
    return STARTS[index], STARTS[index + 1]


def be(data):
    if len(data) % 4:
        raise ValueError('Storage reads must include the full final 32-bit word')
    return b''.join(data[i:i + 4][::-1] for i in range(0, len(data), 4))


def pairs():
    return json.loads((BASE / 'pairs.json').read_text())


def md():
    return capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

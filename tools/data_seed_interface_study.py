"""Inspect stock typed state writers offline; never emit or perform a device write."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from core1_wait_study import IMAGE_SHA256
from line_shaping_study import NATIVE_SHA256, _finite


def float_sources(values):
    """Describe CPU binary32 source rounding, not the BMC's stored representation."""
    if not isinstance(values, dict):
        raise ValueError('Expected a logical-index/value dictionary')
    rows = []
    for address, value in values.items():
        if type(address) is not int or not 0 <= address < 2048:
            raise ValueError('Expected an enum-0 logical index in 0..2047')
        value = _finite(value)
        try:
            source = struct.pack('<f', value)
        except (OverflowError, struct.error) as error:
            raise ValueError('Seed exceeds the finite binary32 source range') from error
        rounded = struct.unpack('<f', source)[0]
        rows.append(dict(logical_index=address, requested=value, source_float32=rounded,
                         cpu_little_endian_bytes=source.hex(), error=rounded-value))
    return sorted(rows, key=lambda row: row['logical_index'])


def report(core, native):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Unsupported CORE1 payload digest')
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native payload digest')
    from dramio_owner_study import expect
    for anchor in (
            (0x01132eae, 'mov', 'r0, r4'), (0x01132eb0, 'bl', '#0x1131968'),
            (0x01132eb4, 'adds', 'r2, r0, r6'), (0x01132eb8, 'ldrb', 'r1, [r4, #0x10]'),
            (0x01132eba, 'vmov.f32', 's0, s16'), (0x01132ebe, 'ldr', 'r0, [r0]'),
            (0x01132ec8, 'b.w', '#0x11300ac'),
            (0x011300ac, 'cmp', 'r0, #7'), (0x011300ae, 'blt', '#0x11300be'),
            (0x011300be, 'cmp', 'r1, #0xc'),
            (0x011300d2, 'ldr.w', 'r3, [r3, r1, lsl #2]'),
            (0x011300d8, 'itt', 'ne'),
            (0x011300da, 'ldr.w', 'r3, [r3, r0, lsl #2]'),
            (0x011300ea, 'ldr.w', 'r0, [r1, r0, lsl #2]'),
            (0x011300ee, 'cmp', 'r0, r2'), (0x011300f0, 'ittt', 'hi'),
            (0x011300f2, 'add.w', 'r0, r3, r2, lsl #2'),
            (0x011300f6, 'vstr', 's0, [r0]'),
            (0x011302a2, 'cmp', 'r1, #0'), (0x011302a4, 'it', 'ne'), (0x011302a6, 'cmp', 'r1, #1'),
            (0x011302a8, 'beq', '#0x11302ea'),
            (0x01130382, 'cmp', 'r1, #0'), (0x01130384, 'it', 'ne'), (0x01130386, 'cmp', 'r1, #1'),
            (0x01130388, 'beq', '#0x11303c4'),
            (0x01130416, 'cmp', 'r1, #0'), (0x01130418, 'it', 'ne'), (0x0113041a, 'cmp', 'r1, #1'),
            (0x0113041c, 'beq', '#0x1130458'),
            (0x011319ee, 'ldr', 'r1, [r5, #0x20]'),
            (0x01131a3a, 'ldr', 'r0, [r5, #0x20]'),
            (0x01131a3e, 'ldr.w', 'r0, [r0, r7, lsl #3]'),
            (0x01131a42, 'add', 'r0, r1'),
            (0x01130898, 'movs', 'r6, r2'), (0x011308a2, 'it', 'eq'), (0x011308a4, 'pop.w', '{r4, r5, r6, r7, r8, sb, sl, fp, ip, pc}'),
            (0x011308b2, 'ldr', 'r0, [r5, #0x34]'),
            (0x011308be, 'ldr.w', 'r0, [fp, #4]'),
            (0x011308c2, 'bl', '#0x11271b8'),
            (0x011308ca, 'add.w', 'r0, r8, r4'),
            (0x011308ce, 'ite', 'ne'), (0x011308d0, 'str', 'r0, [r5, #0x40]'),
            (0x011308d2, 'str', 'r0, [r5, #0x50]'),
            (0x011308d4, 'add.w', 'r0, r7, r4, lsl #2'),
            (0x011308d8, 'vldr', 's0, [r0]'),
            (0x011308dc, 'ite', 'ne'), (0x011308de, 'vstr', 's0, [sl]'),
            (0x011308e2, 'vstr', 's0, [sl, #0x10]')):
        expect(core, *anchor)
    if [core.u32(a) for a in (0x0113014c, 0x01130150, 0x01130560,
                              0x01130564, 0x0113056c, 0x01130570)] != [
            0x0113aac0, 0x0113aaf0, 0x0113ab20, 0x0113ab50, 0x0113ab80, 0x0113abb0]:
        raise ValueError('Typed aperture table references differ')
    banks = []
    for kind in (0, 1):
        tables = [core.u32(address+4*kind) for address in
                  (0x0113aac0, 0x0113aaf0, 0x0113ab20, 0x0113ab50, 0x0113ab80, 0x0113abb0)]
        for dsp in range(7):
            floats, capacity, fixed, fixed_capacity, raw, raw_capacity = (
                core.u32(table+4*dsp) for table in tables)
            base = (0x41400000+dsp*0x100000 if dsp < 6 else 0x41200000)+kind*0x10000
            if (floats, fixed, raw, capacity, fixed_capacity, raw_capacity) != (
                    base, base+0x2000, base+0x4000, 2048, 2048, 2048):
                raise ValueError('Enum-0/1 aperture or capacity differs')
            banks.append(dict(kind=kind, dsp=dsp, float_write_aperture=floats,
                              fixed_write_aperture=fixed, raw_write_aperture=raw,
                              element_capacity=capacity, stock_typed_read_allowed=False))
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    def native_check(address, rows):
        actual = [(i.mnemonic, i.op_str) for i in
                  md.disasm(native[address:address+4*len(rows)], address)]
        if actual != rows:
            raise ValueError(f'Native state mapping differs at {address:#x}')
    native_check(0xfc060, [('ldr', 'x0, [x20, #0x18]'), ('ldrb', 'w1, [x19, #0x10]'),
                         ('ldr', 'x8, [x0]'), ('ldr', 'x8, [x8, #0x40]'),
                         ('blr', 'x8'), ('str', 'd8, [x0]')])
    native_check(0x16bb8c, [('adrp', 'x9, #0xa14000'), ('add', 'x9, x9, #0xe60'),
                          ('stp', 'x9, x1, [x0]')])
    native_check(0x16c3f4, [('cmp', 'w1, #5'), ('b.hi', '#0x16c464'),
                          ('mov', 'w9, w1'), ('adrp', 'x10, #0x7ae000'),
                          ('add', 'x10, x10, #0x3fb'), ('adr', 'x11, #0x16c418'),
                          ('ldrb', 'w12, [x10, x9]'), ('add', 'x11, x11, x12, lsl #2'),
                          ('br', 'x11')])
    native_check(0x16c418, [('ldr', 'x8, [x8, #0x10]'), ('ldr', 'x9, [x8, #0x18]'),
                          ('ldr', 'w8, [x8, #0x20]'), ('sub', 'w8, w2, w8'),
                          ('and', 'w8, w8, #0x7ff'), ('add', 'x0, x9, w8, uxtw #3'), ('ret', '')])
    native_check(0x16c434, [('ldr', 'x8, [x8, #0x18]'), ('ldr', 'x9, [x8, #0x18]'),
                          ('ldr', 'w8, [x8, #0x20]'), ('sub', 'w8, w2, w8'),
                          ('and', 'w8, w8, #0x7ff'), ('add', 'x0, x9, w8, uxtw #3'), ('ret', '')])
    if native[0x7ae3fb:0x7ae401] != bytes.fromhex('00070e131311'):
        raise ValueError('Native memory-kind dispatch differs')
    if struct.unpack_from('<Q', native, 0xa14e60+0x40)[0] != 0x16c3ec:
        raise ValueError('Native core GetMemoryAdrs vtable target differs')
    if core.u32(0x6117647c+0x84) != 0x01132e69 or core.u32(0x01130a0c) != 0x41158000:
        raise ValueError('Manager writer or global float portal differs')
    return dict(payload_sha256=IMAGE_SHA256, native_sha256=NATIVE_SHA256,
                float_driver=0x011300ac, float_manager=0x01132e68, manager_slot=0x84,
                float_driver_arguments=['r0 DSP', 'r1 memory kind', 'r2 logical index', 's0 float32'],
                enum0_descriptor_group=0x20, native_enum0_ring_pointer=0x10,
                native_enum1_ring_pointer=0x18, native_index_mask=0x7ff,
                banks=banks, cpu_source_format='IEEE-754 binary32',
                global_float_driver=0x01130892, global_float_portal=0x41158000,
                global_portal_to_enum0_join_proven=False,
                owner_reservation_for_original_oscillator_proven=False,
                hardware_encoding_verified=False, hardware_cadence_verified=False,
                execution_ready=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('native', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    print(json.dumps(report(Core1(args.image), args.native.read_bytes()), indent=2))

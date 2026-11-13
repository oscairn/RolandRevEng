#!/usr/bin/env python3
"""Decode the bmc0 CORE1 DRAM-IO program aperture tables and their users.

Run 11's load-route census (tools/core1_load_route_study.py) found the boot
verify routine 0x610010d0 uploading program and DRAM-IO lists and named the
DRAM-IO aperture tables at 0x0113a970/0x0113a988 without decoding them, and
run 12's boot-entry study queued this decode. This tool answers:

1. GetDramIOProgAdrs (0x0112fb74): DSP<6, 8-byte alignment, and the r2 bank
   selector choosing between two aperture sub-tables; full body byte-pinned.
2. The two sub-tables are one contiguous 24-word array at 0x0113a970:
   bank 0 (DSP0..5) at 0x41440000+dsp*0x100000, bank 1 at +0x40000, bank 2
   at +0x80000, bank 3 at +0xc0000. Every word is checked against that
   closed-form layout.
3. Which functions use which bank: literal-pool pc-relative load census for
   the aperture words (GetDramIOProgAdrs banks 0/1, StackFillDramIOProgNop,
   ReadDramIOProg, SetDramIOMuteCounter, GetDramIOMuteCounter) plus the
   literal-port tables that follow (exec control 0x4110X310, SetDspFlag
   0x4110X318, CopyDramIOProgPage 0x4110X300/0x4110X200) and SetExeMode/
   GetExeMode use of the 0x4110X310 table.
4. The boot verify routine's DRAM-IO phase: the manager upload dispatch
   0x61001124..0x61001156 (vtable byte 0x1c, TBB-decoded per-DSP targets
   cross-checked with a Unicorn single-step), its object literals, and the
   readback-compare call of GetDramIOProgAdrs with bank 0 at 0x610012ae.
5. CopyDramIOProgPage (0x0112fdc0): the page-copy contract (page-aligned
   offsets, span bound 0x3000, per-page literal-port command pairs with
   bit 24 set and busy-bit wait) a resident loader's own verify could reuse.

Static, read-only file analysis. No firmware execution, no device access,
no key/ciphertext material.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

GET_DRAM_IO_PROG_ADRS = 0x0112fb75
TABLE_BASE = 0x0113a970
BANK_WORDS = 6
BANKS = 4
BANK_BASES = (0x41440000, 0x41444000, 0x41448000, 0x4144c000)
DSP_STRIDE = 0x100000
EXEC_PORTS = 0x0113a9ec          # 0x41104310.. per DSP+MDSP (SetExeMode)
FLAG_PORTS = 0x0113a9d0          # 0x41104318.. (SetDspFlag)
COPY_PORTS_300 = 0x0113aa08      # 0x41104300.. (CopyDramIOProgPage)
COPY_PORTS_200 = 0x0113aa24      # 0x41104200.. (CopyDramIOProgPage offset 0x100)
COPY_PORTS_400 = 0x0113aa3c      # 0x41104400.. (raw/fixed ports region)

# (address, hex bytes, label) — byte-exact anchors.
ANCHORS = (
    # GetDramIOProgAdrs full body: dsp<6, alignment, bank select, add, pops.
    (0x0112fb74, '10b5062808dbaff2443240f29911444805f0b5f9002010bd'),
    (0x0112fb8c, '11f0070f08d0aff25c324ff4cd713e4805f0a9f9002010bd'),
    (0x0112fba4, '22b1394a52f82000084410bd354a52f82000084410bd'),
    # GetDspProgAdrs aperture-table load (render, 7 words at 0x0113a954).
    (0x0112f95a, 'c94a52f82000084410bd'),
    # StackWriteDramIOProg 0x112f964: bank select ite on sb (r2==0 -> 0x113a970).
    (0x0112f9c4, 'b9f1000f0cbfaf48af4850f82600402d00eb0806'),
    # ReadDramIOProg 0x112fa8f: bank select ite on r2.
    (0x0112fa98, '002a0cbf7a4a7b4a52f820004618402d45d3724c'),
    # StackFillDramIOProgNop 0x112fcbd: bank select ite on r8.
    (0x0112fd42, 'b8f1000f14bfef48f04850f82700002106442078'),
    # SetDramIOMuteCounter 0x1130761: banks 3/2 selection.
    (0x01130772, '4ff0040cc9080cebc1013bb19e4b53f82000084402600260026006e09b4b53f8'),
    # GetDramIOMuteCounter 0x11307a7: banks 1/2 selection with ubfx 20-bit read.
    (0x011307e0, '0423c90803ebc10132b1864a52f820004058c0f3130010bd804a52f820004058c0f31300'),
    # CopyDramIOProgPage head: dsp<6, page alignment checks, span bound 0x3000.
    (0x0112fdc0, 'f0b4062807dbaff29052f0bc40f21521cf4805f08eb8'),
    (0x0112fdd6, 'c1f3090cbcf1000f07d0aff2ac52f0bc40f21621c94805f081b8'),
    (0x0112fdf0, '01eb020cbcf5405f07d9aff2c452f0bc40f21721c24805f074b8'),
    # CopyDramIOProgPage loop: page count, port command pairs with bit 24,
    # busy wait on [aperture+8] bit 31.
    (0x0112fe58, '960a0022002ecebfac4df0bc704700bf55f8204001eb822c4cf4803c'),
    (0x0112fe74, 'c4f800c055f8204003eb822c4cf4803cc4f804c055f820c0dcf80840002cfbd1521cb242e6dbf0bc7047'),
    # SetExeMode writes the packed mode/event word through EXEC_PORTS.
    (0x01130bd4, '1b0743ea01611143'),
    (0x01130bdc, '114a52f8200001607047'),
    # GetExeMode reads bits 27..24 back through the same table.
    (0x01130bfe, '094951f820000068c0f3016010bd'),
    # SetDspFlag writes through FLAG_PORTS.
    (0x0112f4f6, 'd24905f07f0040ea047051f82610086070bd'),
    # Boot verify DRAM-IO phase: bypass entry, TBB, literal loads, dispatch.
    (0x61001120, '002405e0032c17d2dfe804f002160400'),
    (0x61001130, 'ee4900e0ee4979b1200008bf'),
    (0x61001148, '062c08bfe64803d110b1'),
    (0x61001152, '0268d2699047'),
    # The phase-2 readback-compare calls GetDramIOProgAdrs with bank 0.
    (0x610012a6, '00222046d8f80010'),
    (0x610012ae, '75f0edfb'),
    # Phase-2 loop bound: DSP 0..5.
    (0x61001390, '641c052c'),
    # VerifyDrProg log string.
    (0x61001518, '445350256320566572696679447250726f672829203d2000'),
)

# Boot verify phase-2 upload dispatch: per-DSP target of the TBB at
# 0x61001128 (r4=0 bypasses the TBB via the branch at 0x61001122) and the
# object the dispatch consumes. The DSP1/3/4/5 targets fall through to the
# shared skip at 0x61001158 (no DRAM-IO upload in the stock boot image).
PHASE2_TBB_INSN = 0x61001128
PHASE2_TBB_SKIP = 0x61001158
PHASE2_UPLOAD_SITES = {0: 0x61001154, 2: 0x61001154, 6: 0x61001154}
PHASE2_UPLOAD_OBJECTS = {
    0: ('literal', 0x61085dcc),      # DSP0 bank-1 stub, 16 bytes
    2: ('literal', 0x61085ddc),      # DSP2 bank-1 stub, 16 bytes
    6: ('sram_deref', 0x20084bb4),   # DSP6/MDSP object pointer in SRAM
}
PHASE1_TBB_INSN = 0x610010e2
PHASE1_TBB_OBJECTS = {          # first upload-phase object per DSP index
    0: 0x61085dc4, 2: 0x61085dd4, 6: 0x61085de4,
}


def load_image(path):
    from core1 import Core1
    return Core1(path)


def check_anchors(core):
    problems = []
    for address, hex_bytes in ANCHORS:
        expected = bytes.fromhex(hex_bytes)
        try:
            actual = core.data[core.offset(address):core.offset(address) + len(expected)]
        except ValueError:
            problems.append((hex(address), 'not backed by image'))
            continue
        if actual != expected:
            problems.append((hex(address), f'expected {hex_bytes}, got {actual.hex()}'))
    return len(ANCHORS), problems


def aperture_words(core):
    return [core.u32(TABLE_BASE + 4 * i) for i in range(BANKS * BANK_WORDS)]


def expected_aperture_words():
    return [BANK_BASES[bank] + dsp * DSP_STRIDE
            for bank in range(BANKS) for dsp in range(BANK_WORDS)]


def tbb_targets(core, insn, count):
    """Branch targets of tbb [pc, Rn]; table base is insn+4 (unaligned),
    each byte is a halfword (x2) offset, per Unicorn single-step."""
    base = insn + 4
    offset = core.offset(base)
    return [base + 2 * core.data[offset + i] for i in range(count)]


def unicorn_tbb_targets(insn, count, image_path):
    """Cross-check the TBB decode by single-stepping each index in Unicorn."""
    try:
        from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
        from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_R4
    except ImportError:
        return None
    image = Path(image_path)
    if not image.exists():
        return None
    from core1 import Core1
    core = Core1(image)
    eram_off = core.eram_offset
    itcm_len = (eram_off + 0xfff) & ~0xfff
    eram_len = (len(core.data) - eram_off + 0xfff) & ~0xfff
    targets = {}
    for r4 in range(count):
        mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        mu.mem_map(0x01100000, itcm_len)
        mu.mem_write(0x01100000, bytes(core.data[:eram_off]))
        mu.mem_map(0x61000000, eram_len)
        mu.mem_write(0x61000000, bytes(core.data[eram_off:]))
        mu.reg_write(UC_ARM_REG_R4, r4)
        mu.reg_write(UC_ARM_REG_PC, insn)
        try:
            mu.emu_start(insn | 1, insn + 0x400, count=1)
            targets[r4] = mu.reg_read(UC_ARM_REG_PC)
        except UcError:
            targets[r4] = None
    return targets


def pc_relative_loads(core, targets):
    """Instruction addresses whose literal-pool slot holds one of `targets`
    (name -> value). Results are keyed by name."""
    data = core.data
    hits = {name: [] for name in targets}
    wanted = {value: name for name, value in targets.items()}
    for base_off, base, end in ((0, 0x01100000, eram_end(core)),
                                (core.eram_offset, 0x61000000,
                                 0x61000000 + len(data) - core.eram_offset)):
        for off in range(0, end - base - 4, 2):
            hw = struct.unpack_from('<H', data, base_off + off)[0]
            if 0x4800 <= hw < 0x5000:
                address = base + off
                pool = ((address + 4) & ~3) + (hw & 0xFF) * 4
            elif hw == 0xF8DF:
                if off + 4 > end - base:
                    continue
                address = base + off
                pool = ((address + 4) & ~3) + struct.unpack_from(
                    '<H', data, base_off + off + 2)[0]
            else:
                continue
            try:
                value = struct.unpack_from('<I', data,
                                           core.offset(pool & ~1))[0]
            except ValueError:
                continue
            name = wanted.get(value)
            if name is not None:
                hits[name].append(address)
    return {name: sorted(sites) for name, sites in hits.items()}


def eram_end(core):
    return 0x01100000 + core.eram_offset


def literal_word_refs(core, value):
    """Image words equal to value (pointers into literal pools and data)."""
    needle = struct.pack('<I', value)
    rows = []
    off = 0
    while True:
        index = core.data.find(needle, off)
        if index < 0:
            break
        rows.append(core.address(index))
        off = index + 1
    return rows


def aperture_users(core):
    """Which functions load which aperture table / port table literal."""
    targets = {
        'bank0': TABLE_BASE, 'bank1': TABLE_BASE + 4 * BANK_WORDS,
        'bank2': TABLE_BASE + 8 * BANK_WORDS, 'bank3': TABLE_BASE + 12 * BANK_WORDS,
        'exec_ports': EXEC_PORTS, 'flag_ports': FLAG_PORTS,
        'copy_ports_300': COPY_PORTS_300, 'copy_ports_200': COPY_PORTS_200,
        'copy_ports_400': COPY_PORTS_400,
    }
    loads = pc_relative_loads(core, targets)
    # Drop false positives where the word is only a pointer elsewhere in the
    # image: pc-relative loads are the real literal-pool references.
    return {name: [hex(a) for a in sites] for name, sites in loads.items()}, \
           {name: [hex(a) for a in literal_word_refs(core, target)]
            for name, target in targets.items()}


def object_records(core):
    """Boot-verify list objects: header (tag, byte count at +2, list at +4)
    and their 16-byte records. Compare-walk semantics (both phases):
    word0 = aperture offset for Get{,DramIO}ProgAdrs, word1 = length,
    word2 = length repeat, word3 = compare source pointer (r3)."""
    rows = []
    for address in (0x61085dc4, 0x61085dcc, 0x61085dd4, 0x61085ddc,
                    0x61085de4):
        count = core.data[core.offset(address + 2)]
        list_pointer = core.u32(address + 4)
        records = []
        for index in range(count):
            record = list_pointer + 16 * index
            records.append(dict(word0=core.u32(record),
                                length=core.u32(record + 4),
                                length_repeat=core.u32(record + 8),
                                word3=core.u32(record + 0xc)))
        rows.append(dict(object=hex(address), tag=hex(core.u32(address)),
                         count=count, list=hex(list_pointer), records=records))
    return rows


def report(image_path, skip_unicorn=False):
    core = load_image(image_path)
    anchors_checked, anchor_problems = check_anchors(core)
    words = aperture_words(core)
    expected_words = expected_aperture_words()
    phase2_static = tbb_targets(core, PHASE2_TBB_INSN, 4)
    phase1_static = tbb_targets(core, PHASE1_TBB_INSN, 8)
    unicorn = None if skip_unicorn else (
        unicorn_tbb_targets(PHASE2_TBB_INSN, 4, image_path),
        unicorn_tbb_targets(PHASE1_TBB_INSN, 8, image_path))
    users, word_refs = aperture_users(core)
    ok = (not anchor_problems
          and words == expected_words
          and phase2_static[0] == 0x61001130
          and phase2_static[2] == 0x61001134
          and phase2_static[3] == 0x6100112c
          and phase1_static[0] == 0x610010ee
          and phase1_static[2] == 0x610010f2
          and phase1_static[6] == 0x610010f6)
    return dict(ok=ok,
                sha256=hashlib.sha256(core.data).hexdigest(),
                anchors_checked=anchors_checked,
                anchor_problems=anchor_problems,
                aperture_words=[hex(word) for word in words],
                aperture_words_match_closed_form=words == expected_words,
                phase2_tbb_targets=[hex(target) for target in phase2_static],
                phase1_tbb_targets=[hex(target) for target in phase1_static],
                unicorn_phase2_tbb=None if unicorn is None else
                {str(k): None if v is None else hex(v) for k, v in unicorn[0].items()},
                unicorn_phase1_tbb=None if unicorn is None else
                {str(k): None if v is None else hex(v) for k, v in unicorn[1].items()},
                aperture_users=users,
                aperture_word_refs=word_refs,
                verify_objects=object_records(core))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', default='local/b0c1a.bin',
                        type=Path)
    parser.add_argument('--json', action='store_true',
                        help='print the JSON report only')
    parser.add_argument('--skip-unicorn', action='store_true',
                        help='omit the Unicorn TBB cross-check')
    args = parser.parse_args()
    result = report(args.image, skip_unicorn=args.skip_unicorn)
    if args.json:
        print(json.dumps(result, indent=1))
    else:
        print(json.dumps(result, indent=1))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()
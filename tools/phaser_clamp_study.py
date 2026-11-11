"""Prove late phaser clamp stores across pointer-preserving phase branches."""
import argparse
import hashlib
import json
from pathlib import Path

from bmc_dsp import packets
from condition_return_study import preserved
from limit_control_study import checked_access, native_context
from line_shaping_study import NATIVE_SHA256, _finite
from transfer_study import native_accesses
from weighted_mix_study import require_instructions, require_window


def clamp_reference(value):
    return min(1.0, max(-1.0, _finite(value)))


def packet_context(words, following):
    if (len(words) == 4 and len(following) == 7 and words[:3] == [0x1b04, 0xbedb, 0xafe0]
            and following[:4] == [0x3e07, 0xbfe0, 0x0fe2, 0x4fe4]):
        form, targets = 'STPS', [words[3], following[4]]
    elif (len(words) == 6 and len(following) == 14 and words[:4] == [0x3a06, 0xbedb, 0xafe0, 0x0fe2]
          and following[:7] == [0xc64e, 0x0c3a, 0x4010, 0xbfe2, 0x3fe4, 0x7fe6, 0x4fe8]):
        form, targets = 'TVPS', [words[4], following[8]]
    else:
        raise ValueError('Unrecognized phaser clamp packet context')
    if targets[0] == targets[1] or any(not 0 <= target < 0x800 for target in targets):
        raise ValueError('Phaser clamp targets alias or exceed data range')
    return dict(form=form, targets=targets)


def check_join(native, start, window, end):
    """Accept forward numeric branches whose paths all enter the same window."""
    import capstone
    from capstone import arm64

    if not start <= window < end or any(pc not in native for pc in range(start, end, 4)):
        raise ValueError('Incomplete native join interval')
    require_window(native, window, end-4)
    branches = []
    for pc in range(start, window, 4):
        ins = native[pc]
        if any(ins.group(group) for group in (capstone.CS_GRP_CALL, capstone.CS_GRP_RET, capstone.CS_GRP_INT)):
            raise ValueError('Late-window provenance crosses an unchecked call or return')
        if ins.group(capstone.CS_GRP_JUMP):
            if not ins.operands or ins.operands[-1].type != arm64.ARM64_OP_IMM:
                raise ValueError('Late-window provenance has an indirect branch')
            target = ins.operands[-1].imm
            if target not in native or not pc < target <= window:
                raise ValueError('Numeric branch bypasses the window or has a back edge')
            branches.append(dict(pc=pc, target=target))
    for register in ('x22', 'x8', 'w9'):
        preserved([native[pc] for pc in range(start, end, 4)], register)
    return branches


def report():
    from capstone import arm64
    import lib

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    results = []
    for cls, seed_end, window, clamp, end, packet, relatives, object_fields, bounds in (
            ('SIM_MFX_STPS', 0x148e94, 0x148fa8, 0x149004, 0x149020, 0x18a,
             (0x190, 0x19a), (0x254, 0x25c), ((0x148fbc, 'd4', 1), (0x148fc4, 'd6', -1))),
            ('SIM_MFX_TVPS', 0x278fb8, 0x2790cc, 0x27912c, 0x279148, 0x178,
             (0x180, 0x194), (0x2a4, 0x2ac), ((0x2790e4, 'd5', 1), (0x2790ec, 'd9', -1)))):
        program, native, _, fields, prefix_trace = native_context(cls)
        entry = min(native)
        if prefix_trace['stop'] != dict(pc=seed_end, mnemonic='b.pl'):
            raise ValueError('Phaser prefix does not end at the checked phase branch')
        require_window(native, entry, seed_end-4)
        branches = check_join(native, seed_end, window, end)

        def memory_write(ins):
            # Capstone 5 marks some load operands read/write; use the known load mnemonics.
            return (any(op.type == arm64.ARM64_OP_MEM for op in ins.operands)
                    and ins.mnemonic not in ('ldr', 'ldur', 'ldp', 'ldnp'))

        prefix_writes = {row['pc']: row for row in prefix_trace['accesses'] if row['kind'] == 'write'}
        for pc in range(entry, seed_end, 4):
            ins = native[pc]
            if memory_write(ins) and ins.reg_name(ins.operands[-1].mem.base) != 'sp':
                if pc not in prefix_writes or prefix_writes[pc]['path'] not in (
                        ['wrapper', 8, 0x18, 0x10, 0x18], ['wrapper', 8, 0x18, 0x28, 0x18]):
                    raise ValueError('Phaser prefix may write constructor/address records')
        rows = dict(packets(program))
        context = packet_context(rows[packet], rows[packet+2*len(rows[packet])])
        upper, lower = (item[1] for item in bounds)
        for pc, register, value in bounds:
            require_instructions(native, pc, (('fmov', f'{register}, #{value:.8f}'),))
            preserved([native[ip] for ip in range(pc+4, end, 4)], register)
        require_instructions(native, clamp, (
            ('fmin', f'd0, d1, {upper}'), ('fcmp', f'd1, {lower}'),
            ('fcsel', f'd0, {lower}, d0, mi'),
        ))
        store_pcs = (clamp-4, clamp+24)
        # Only proven-invariant pointer/index roots cross the omitted numeric paths.
        projected = [native[pc] for pc in range(entry, seed_end, 4)]
        numeric_stores = []
        for pc in range(seed_end, end, 4):
            ins = native[pc]
            if not memory_write(ins):
                continue
            load = native[pc-12]
            if (load.mnemonic != 'ldr' or len(load.operands) != 2
                    or load.operands[1].type != arm64.ARM64_OP_MEM
                    or load.operands[1].mem.disp not in fields):
                raise ValueError('Numeric path has an unrecognized memory write')
            field = load.operands[1].mem.disp
            value = ins.reg_name(ins.operands[0].reg)
            if not value.startswith('d') or any(pc-12 < branch['target'] <= pc for branch in branches):
                raise ValueError('Numeric path can bypass a bounded data-store address')
            require_instructions(native, pc-12, (
                ('ldr', f'w12, [x22, #{field:#x}]'), ('add', 'w12, w9, w12'),
                ('and', 'w12, w12, #0x7ff'), ('str', f'{value}, [x8, w12, uxtw #3]'),
            ))
            projected += [native[ip] for ip in range(pc-12, pc+4, 4)]
            numeric_stores.append(pc)
        trace = native_accesses(projected, fields, {})
        bindings = []
        for pc, relative, field in zip(store_pcs, relatives, object_fields, strict=True):
            record = fields[field]
            if record['relative'] != relative or int.from_bytes(program[relative:relative+2], 'big') != record['address']:
                raise ValueError('Phaser native record differs from the exact DSP operand')
            binding = checked_access(native, fields, trace, pc, 'write', **record)
            if binding['object_field'] != field:
                raise ValueError('Phaser store uses another constructor record')
            require_instructions(native, pc, (('str', 'd0, [x8, w12, uxtw #3]'),))
            bindings.append(binding)
        if [row['address'] for row in bindings] != context['targets']:
            raise ValueError('Phaser clamp transfer operands do not match native stores')
        results.append(dict(cls=cls, packet=packet, control=0xbedb, clamp=clamp,
                            stores=bindings, branches=branches, result_store_port=3,
                            source_native_register='d1', input_port_candidate=3,
                            input_port_verified=False, native_interval=[window, end],
                            checked_numeric_stores=numeric_stores))
    return dict(native_sha256=NATIVE_SHA256, contexts=results,
                native_execution_verified=False, bmc_execution_verified=False,
                isolated_opcode_admission=False)


def fantom_report(core):
    from functools import partial
    from effect_lifecycle_study import IMAGE_SHA256
    from line_mix_variation import core_report
    from quantizer_context_inventory import scan

    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom BMC0 CORE1 image')
    inventory = core_report(core, partial(scan, controls=(0xbedb,)))
    matches = []
    for row in inventory['matches']:
        try:
            context = packet_context(row['packet'], row['following'] or [])
        except ValueError:
            continue
        matches.append(dict(**{key: row[key] for key in ('descriptor', 'base', 'source', 'offset')},
                            **context))
    return dict(counts=inventory['counts'], matches=matches,
                unmatched_bedb_contexts=len(inventory['matches'])-len(matches),
                algorithm_ownership_verified=False, hardware_execution_verified=False)


def native_probes(values):
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping

    values = tuple(_finite(value) for value in values)
    checked = report()
    start = checked['contexts'][0]['clamp']
    code = lib.Z[start:start+12] + bytes.fromhex('c0035fd6')
    result = []
    with executable_mapping(code) as address:
        # The original three instructions use only caller-saved FP registers.
        invoke = ctypes.CFUNCTYPE(ctypes.c_double, *([ctypes.c_double]*7))(address)
        for value in values:
            actual = invoke(0, value, 0, 0, 1, 0, -1)
            if actual.hex() != clamp_reference(value).hex():
                raise ValueError(f'Native clamp differs at {value!r}')
            result.append(dict(input=value, output=actual))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core1', type=Path)
    args = parser.parse_args()
    result = report()
    if args.core1:
        from core1 import Core1
        result['fantom'] = fantom_report(Core1(args.core1))
    print(json.dumps(result, indent=2, allow_nan=False))

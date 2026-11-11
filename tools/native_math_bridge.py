"""Relocate checked ARM64 log/exp calls to local process-libm trampolines."""
import ctypes
import struct

TRAMPOLINE = bytes.fromhex('5000005800021fd6')  # LDR X16,PC+8 / BR X16 / address.
NOP = bytes.fromhex('1f2003d5')


def _math_address(symbol):
    try:
        address = ctypes.cast(getattr(ctypes.CDLL(None), symbol), ctypes.c_void_p).value
    except (AttributeError, OSError) as error:
        raise ValueError(f'Could not resolve process libm {symbol}') from error
    if not address or not 0 < address < 2**64:
        raise ValueError(f'Invalid process libm {symbol} address')
    return address


def bind_math_calls(code, base, expected):
    """Validate relocation, not code safety; the caller must pin and check its source."""
    if not isinstance(code, bytes) or not code or len(code) % 4:
        raise ValueError('Expected nonempty complete ARM64 instruction bytes')
    if type(base) is not int or not 0 <= base <= 2**64-len(code) or base % 4:
        raise ValueError('Expected an aligned ARM64 source address')
    if not isinstance(expected, dict) or not expected:
        raise ValueError('Expected explicit nonempty math-call bindings')
    for pc, binding in expected.items():
        if (type(pc) is not int or pc % 4 or not base <= pc < base+len(code)
                or not isinstance(binding, tuple) or len(binding) != 2
                or type(binding[0]) is not int or not 0 <= binding[0] < 2**64 or binding[0] % 4
                or binding[1] not in ('log', 'exp')):
            raise ValueError('Expected aligned PC/target and a log or exp binding')
    import capstone
    from capstone import arm64

    decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    decoder.detail = True
    instructions = list(decoder.disasm(code, base))
    addresses = set(range(base, base+len(code), 4))
    if [ins.address for ins in instructions] != list(range(base, base+len(code), 4)):
        raise ValueError('Incomplete ARM64 decoding')
    if (instructions[-1].mnemonic, instructions[-1].op_str) != ('ret', ''):
        raise ValueError('Expected one final ordinary RET')
    seen = set()
    for ins in instructions:
        if ins.mnemonic in ('adr', 'adrp') or any(ins.group(group) for group in
                (capstone.CS_GRP_INT, capstone.CS_GRP_IRET)):
            raise ValueError('Unsupported position-dependent or interrupt instruction')
        if ins.mnemonic in ('ldr', 'ldrsw', 'prfm') and ins.operands[-1].type == arm64.ARM64_OP_IMM:
            raise ValueError('PC-relative literal access is unsupported')
        if ins.group(capstone.CS_GRP_CALL):
            if (ins.mnemonic != 'bl' or ins.address not in expected
                    or ins.operands[-1].imm != expected[ins.address][0]):
                raise ValueError('Unexpected, indirect or mismatched math call')
            seen.add(ins.address)
        elif ins.group(capstone.CS_GRP_JUMP):
            if ins.operands[-1].type != arm64.ARM64_OP_IMM or ins.operands[-1].imm not in addresses:
                raise ValueError('Branch leaves the decoded callback or is indirect')
        elif ins.group(capstone.CS_GRP_RET) and ins.address != base+len(code)-4:
            raise ValueError('Unexpected early return')
    if seen != set(expected):
        raise ValueError('Math-call bindings do not match the complete call set')
    if [(ins.mnemonic, ins.op_str) for ins in decoder.disasm(TRAMPOLINE, 0)] != [
            ('ldr', 'x16, #8'), ('br', 'x16')]:
        raise ValueError('Math trampoline encoding differs')
    image = bytearray(code + NOP*((-len(code) % 16)//4))
    stubs, calls = {}, []
    for pc in sorted(expected):
        target, symbol = expected[pc]
        if symbol not in stubs:
            stubs[symbol] = len(image)
            image += TRAMPOLINE + struct.pack('<Q', _math_address(symbol))
        delta = stubs[symbol] - (pc-base)
        if delta % 4 or not -(2**25) <= delta//4 < 2**25:
            raise ValueError('Math trampoline exceeds signed BL imm26 range')
        struct.pack_into('<I', image, pc-base, 0x94000000 | ((delta//4)&0x3ffffff))
        calls.append(dict(pc=pc, target=target, symbol=symbol, trampoline_offset=stubs[symbol]))
    return bytes(image), dict(calls=calls, callback_length=len(code), trampolines=len(stubs))

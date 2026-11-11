"""Manage executable memory for the separately validated native callback fixtures."""
from contextlib import contextmanager
import ctypes
import mmap
import platform
import struct


class RingFixture:
    """Keep the recovered callback pointer graph and its data buffers alive."""

    def __init__(self, context):
        self.context = context
        self.ring = (ctypes.c_double * 2048)()
        self.ring_context = ctypes.create_string_buffer(0x28)
        self.owner = ctypes.create_string_buffer(0x120)  # TRANSIENT caches/cursors extend through +0x118.
        self.manager = ctypes.create_string_buffer(0x20)
        self.wrapper = ctypes.create_string_buffer(0x30)
        for buffer, offset, target in (
                (self.ring_context, 0x18, self.ring), (self.owner, 0x10, self.ring_context),
                (self.manager, 0x18, self.owner), (self.wrapper, 8, self.manager),
                (self.wrapper, 0x28, context)):
            struct.pack_into('<Q', buffer, offset, ctypes.addressof(target))


@contextmanager
def executable_mapping(code):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Native callback execution requires macOS ARM64')
    if not isinstance(code, bytes) or not code or len(code) % 4:
        raise ValueError('Expected complete ARM64 instruction bytes')
    size = (len(code) + mmap.PAGESIZE - 1) // mmap.PAGESIZE * mmap.PAGESIZE
    with mmap.mmap(-1, size, prot=mmap.PROT_READ | mmap.PROT_WRITE) as mapping:
        mapping.write(code)
        address = ctypes.addressof(ctypes.c_char.from_buffer(mapping))
        system = ctypes.CDLL(None, use_errno=True)
        system.mprotect.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
        system.mprotect.restype = ctypes.c_int
        if system.mprotect(address, size, mmap.PROT_READ | mmap.PROT_EXEC):
            raise OSError(ctypes.get_errno(), 'Could not make the callback fixture executable')
        system.sys_icache_invalidate.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
        system.sys_icache_invalidate.restype = None
        system.sys_icache_invalidate(address, len(code))
        yield address

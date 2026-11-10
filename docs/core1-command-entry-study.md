# CORE1 command entry: handler versus logging formatter

2026-11-09. Static findings from the same bmc0 v1.08 payload identified in the loader
map. This does not establish a reachable host command for loading arbitrary DSP code.

The firmware contains a `13CUMDWRxSysCmd` RTTI name. `tools/core1_rtti.py` follows
aligned references to that name, its type-info record and a zero-offset vtable group:

| Item | CORE1 runtime address |
|---|---|
| RTTI name | `0x61174c4f` |
| Type info | `0x611728e4` |
| Candidate vtable group | `0x61178a84` |
| First Thumb callback | `0x0110bacd` |
| Second Thumb callback | `0x011355fd` |

The first callback is substantive: it extracts bits 15:8 from its second argument
(`r1`) and branches on command values. The second callback is a bare return. Its
incoming caller/transport path still needs recovery, so these are callback candidates
linked by RTTI rather than a demonstrated externally accessible API.

## Recovered dispatch fragment

At code address `0x0110bacc`, let `command = (word >> 8) & 255` and `argument = word >> 16`:

| Command | Observed target or action |
|---|---|
| `0x51` | Calls `0x0112c15a` with object address `0x20084770`, then `0x01134966` |
| `0x52` | Passes argument bits 12:0 and a boolean indicating any bits 15:13 to `0x01134970` |
| `0x54` | Passes the 16-bit argument to `0x0111a836` |
| `0x58` | Passes word bits 23:16 to `0x0110c5a4` |
| `0x70` | Calls `0x0110d4cc`, then follows the `0x7b` path |
| `0x74` | Calls `0x0111a31e` with object address `0x200806e4` and the 16-bit argument |
| `0x75` | Calls `0x0111a5f4` with object address `0x200806e4` and the 16-bit argument |
| `0x7b` | Uses the low bit of a byte at `0x200804a4` in a call to `0x0110e48a`, then increments that byte |
| Other values | Return in this callback |

The callee names/meanings are not recovered here. These numeric commands are not
documented SysEx commands, UART frames or read/write endpoints, and must not be sent
blindly to an instrument.

## Why string references alone are insufficient

The nearby “Test Mode Request,” “Restart Sound Engine,” note and SysEx strings are used
by a different function at `0x61025c62`. It accepts an output buffer in `r0` and a word
in `r1`, formats the word's constituent fields through the formatting helper at
`0x61076adc`, and returns. The wrapper at `0x61025f94` allocates a buffer, calls this
formatter and then logs it. A log label therefore does not identify the code that
actually executes the labeled operation.

For example, the string for test-mode requests is referenced at `0x61025d6a`, whereas
the recovered RTTI callback above does not dispatch command `0x60`. Another handler or
routing layer may own that command. The bounded result is that this callback is not
evidence for a `0x60` development-entry API.

The “DSP Develop” string is installed as a UI object's title by code around
`0x61023800`. Its existence proves a development UI component, not an arbitrary program
upload command or a host-accessible debug shell.

## Reproduce

```sh
python3 tools/core1_rtti.py local/b0c1a.bin 13CUMDWRxSysCmd
python3 tools/core1.py local/b0c1a.bin --address 0x110bacc --size 0x58
python3 tools/core1.py local/b0c1a.bin --address 0x110bb88 --size 0x40
python3 tools/core1.py local/b0c1a.bin --address 0x61025c62 --size 0x30
```

The pointer tracing tool is bounded to image-backed Thumb candidates and 32 entries
per group; it is not a complete C++ ABI parser. No function was executed. No plugin,
firmware body or native disassembly is included in the repository.

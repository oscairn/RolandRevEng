# Relocated original voice bodies for Fantom resource layouts

2026-11-10. `tools/fantom_voice_plan.py` now builds the original 200-byte
stereo voice with explicit data, coefficient and input-address assignments
from each of the five recorded Fantom owners. An independent byte check
verifies the relocation; packet execution reproduces the original model's
outputs through ring wrap with nonzero canaries outside the six seeded cells.

These are executable **offline fragment bodies**, not load-ready instrument
programs. The builder emits no entry/return wrapper or output-IO stores and
assigns no body load address. It performs no device access. Runtime ownership,
safe initialization, chip precision/cadence and the external control path
remain unverified.

## Source context and typed resource substitution

`fantom_line_context.load_context` supplies the pinned image identity,
known owner descriptor, stock LINEDRIVE placement, reservations, input pair
and output-operand candidates. The CORE1 payload remains SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
The existing capacity check must pass before a custom body is generated.

| Owner | Selected DSP | Enum-0 data base | Enum-6 coefficient base | Input pair | Stock output candidates |
|---|---:|---|---|---|---|
| `610a1674` | 4 | `100` | `190` | `2000/2001` | `2002/2003` |
| `610a16bc` | 5 | `320` | `1f4` | `2005/2006` | `2007/2008` |
| `610a1704` | 5 | `3b6` | `208` | `2009/200a` | `200b/200c` |
| `610a174c` | 5 | `44c` | `21c` | `200d/200e` | `200f/2010` |
| `610a1d14` | 1 | `c0` | `e` | `20ee/20ef` | `20f0/20f1` |

Addresses and indices in this table are hexadecimal. The descriptors describe
occupied stock instances; they are not available custom allocations. A program
list's header DSP byte is not substituted for the selected manager DSP.

The builder inverse-decodes the three original profiles, adjusts their named
resource fields, and reassembles them:

- Add enum-0 base to data sources, targets, wet values, factor and scratch cells.
- Add enum-6 base to all six coefficient indices, retaining address tag `c000`.
- Assign both the prefix and tail the selected stock input pair, including when
  the inverse decoder omitted an implicit default pair.

For owner `610a1674`, original data target `80` becomes `180`; seed `21`
becomes `121`; coefficient 0 becomes tagged operand `c190` and coefficient
1 becomes `c191`. Scratch data indices `190/191` are separate from those
coefficient resources despite having the same untagged numeric indices.

The stock output candidates are reported only. The body still leaves its
results in functional main A/B after actual scratch stores and reloads.
Frequency, amplitude and gain affect seed/parameter values, not the compiled
body bytes. Live parameter scheduling and reseeding are not implemented.

## Independent byte-level verification

The verifier starts again from the original bytes, walks their packet headers
and locates only family-4 indexed transfer operands. It applies the expected
data/coefficient/input substitutions to those fields and compares the result
with the separately reassembled body. All **30 two-byte transfer fields** are
accounted for; the other **140 bytes** must remain identical. Controls, long
extensions and literals that resemble addresses are never globally patched.

The existing prefix includes the known `(0,2,4)` quantizer packet at offset
`e`. `header_study.layout()` still rejects that packet's miscellaneous layout.
The relocation walk is gated by the three exact supported profiles and reads
only its proven indexed-transfer field at `1c`; it does not reinterpret the
miscellaneous operation or weaken the general decoder. Tests retain that
rejection and protect the nearby long extension/literal positions.

The builder concatenates all logical slices before converting stored LE32
words. The 38-byte first boundary remains unaligned, and the complete body
is still exactly 200 bytes. Each plan records both logical and stored hashes.
The default DSP4-layout logical body hash is
`e550f733ce6979b74496d2c79900785508ac92ae35b256e5fca5f900b3909edc`.

## Six required initial data values

The read-before-write analysis follows packet memory order: current-packet
reads use the memory available before current-packet stores commit. It finds
exactly these relative first-frame inputs:

```text
21, 31, 41, 51, 61, 71   (hexadecimal)
```

These are the existing oscillator's six seed slots. The factor at `80` is
written by the prefix before the allpass reads it. Current outputs `60/70`
are written before the tail reads them, and scratch `90/91` is written
before its reload. No other initial data value is required by this functional
model. The manifest is rejected if its seed keys differ from that analysis.

Verification initializes every other ring cell to a nonzero, index-dependent
canary rather than clearing the ring. All five relocated versions match the
original zero-background voice exactly for 12,000 frames each: **120,000
stereo output values in total**, through five complete origin wraps and to
final origin 1760. Declared data-store destinations are checked during execution.
The allpass receives no IO dictionary; its profile consumes data while the
prefix/tail use the relocated stock input pair.

This establishes a six-value initialization dependency under the explicit
native-ring model. It does not establish a safe live write window, absence of
hidden hardware state, or permission to clear/modify another owner's data.
`whole_ring_clear_required_by_model=false` is deliberately narrower than a
hardware initialization claim.

## Value representations and generated artifacts

The manifest contains requested native-policy binary64 values, six separately
rounded CPU binary32 data-source rows and six coefficient-source rows. Each
CPU row includes its little-endian source bytes. Those bytes are **CPU source
buffers**, not a raw DSP storage format. The
[typed state-writer study](state-initialization-and-float-writers.md) records
the actual driver interfaces and the unresolved readback/conversion boundaries.
The model comparison here uses the requested native-policy seeds.

```sh
python3 tools/fantom_voice_plan.py local/b0c1a.bin local/voice-plan-dsp4 \
  --owner 0x610a1674 --frequency 440 --gain .5 --frames 12000
python3 -m unittest discover -s tests -p test_fantom_voice_plan.py -v
```

Use the existing pinned CORE1 artifact and Capstone-capable Python 3.13+
interpreter. The CLI verifies the selected model before creating a new output
directory. It writes only:

- `body-logical.bin`: original voice body in logical packet order.
- `body-stored.bin`: the same original body in stored-word order.
- `manifest.json`: identities, substitutions, source values, proof results and limits.

Existing output directories are refused. Hash/size inconsistencies are rejected
before creating files. Vendor programs are not exported or patched. Generated
plans for all five layouts remain under ignored `local/fantom-voice-plans/`.

`stock_placement.destination` describes the **stock 578-byte LINE program**,
not the start of this custom body. The manifest keeps `load_address`,
`entry_address` and `return_address` null, `wrapper_included=false`,
`output_io_writes_included=false`, and both runtime/hardware verification false.
The next deployment requirements are a verified task entry/return convention,
actual owner selection and coordination, output routing, typed seed writes and
readback, and measured chip timing/precision.

## Review

Qwen's bounded draft timed out at 240.2 seconds. Review found missing coefficient
tag bits, an omitted default-tail input substitution, skipped first transfers,
and confusion between a transfer port number and an operand's memory tag. Its
fallback around the rejected miscellaneous layout was also unsound. No unchecked
draft was adopted; the final builder and transfer-only verifier were implemented
and executed locally against all five contexts.

All 359 tests passed. Seven new tests cover field roles, protected non-address
bytes, wrong resource substitutions, all real owner layouts, parameter-only
changes, first-frame seed completeness, wrap/canary behavior, invalid inputs
and preservation of existing exports. The strict owner-type check was added
and those tests rerun after the complete-suite checkpoint.

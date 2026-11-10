# DRAM-IO owners, counter aliases and the global clear interface

Follow-up: [clear completion](clear-completion-interrupt-study.md) joins event17 to
IRQ80, stock priority/enable/mask setup and the handler's status acknowledgement.
It adds per-element portal-address evidence while preserving bulk-unit/domain and
safe-ownership limits below.

[Named diagnostics](memory-domain-labels-and-clear-count-boundary.md) additionally
call the false bank IDM and true bank EDM through their monitor labels. A duplicate
control-register read in that same display limits the corroboration; bulk-clear
count units and a physical hardware specification remain unproved.

2026-11-10. Offline follow-up to [the JUPITER-X comparison](jupiter-crossmodel-c1-study.md)
and [RAMCLR/native clearing](dramio-clear-records-and-native-state.md). This pass
connects the eleven JUPITER-X RAMCLR sources to actual constructor-selected manager
descriptors. It also recovers separate stock mute-counter and global clear register
contracts. Neither contract proves RAMCLR sweep timing or a safe selective reset.

Inputs retain their previous identities: JUPITER-X C1A container SHA-256
`9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b`, Fantom bmc0
header-stripped CORE1 SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`, and ZENOLOGY
arm64 SHA-256 `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
JUPITER-X uses the same validated split-member analysis view as the preceding study;
its synthetic hash is not presented as a vendor-image hash. Addresses are CORE1
runtime addresses except the explicitly identified native table/functions. Unprefixed
register/program constants in code formatting are hexadecimal; bit and instance counts
are decimal.

## Constructors settle the primary owner assignment

JUPITER-X constructor `6102e5f8` installs manager vtable address point `6127a604`,
whose RTTI name is `10CBmcDspMgr`. It constructs nine manager objects at
`200a1890 + i*14` and stores descriptor `610c0d58 + i*48` at each manager+8.
The dataflow at `6102e67c..696` computes i*9*8 = i*72 bytes; the loop bounds i<9
at `6102e6b8`. Both object and descriptor strides here are hexadecimal.

A second loop at `6102e6c0..76e` constructs two managers at `200a1b04 + i*14`,
storing descriptors `610c0fe0 + i*48`. Its bound is i<2. These are compiled
constructor assignments, assuming normal constructor completion, not runtime
snapshots or proof that every later algorithm retains these descriptors.

Each descriptor's `+10` first DRAM-IO index and `+11` count select its source from
RAMCLR's eleven-entry list. Its `+c` reservation pointer agrees with that selected
source's base/capacity. The instance ordinal is **not** the selection index:

| Constructor group / instance (decimal) | Descriptor | DSP | RAMCLR index (decimal) | Enum-11 base / length | Enum-2 base / length |
|---|---|---:|---:|---|---|
| nine / 0 | `610c0d58` | 4 | 0 | `400000 / 23000` | `000 / 23` |
| nine / 1 | `610c0da0` | 4 | 2 | `446000 / 23000` | `134 / 23` |
| nine / 2 | `610c0de8` | 4 | 3 | `469000 / 23000` | `157 / 23` |
| nine / 3 | `610c0e30` | 4 | 4 | `48c000 / 23000` | `17a / 23` |
| nine / 4 | `610c0e78` | 4 | 5 | `4af000 / 23000` | `19d / 23` |
| nine / 5 | `610c0ec0` | 4 | 1 | `423000 / 23000` | `09a / 23` |
| nine / 6 | `610c0f08` | 4 | 6 | `4d2000 / 23000` | `1c0 / 23` |
| nine / 7 | `610c0f50` | 4 | 7 | `4f5000 / 23000` | `1e3 / 23` |
| nine / 8 | `610c0f98` | 4 | 8 | `518000 / 23000` | `206 / 23` |
| two / 0 | `610c0fe0` | 5 | 9 | `700000 / 2d000` | `000 / 3c` |
| two / 1 | `610c1028` | 5 | 10 | `72d000 / 2d000` | `03c / 3c` |

For every selected source, first-word low23 equals enum11.base + record_index*stride,
and second-word high12 equals enum2.base. The first nine have 23 records and stride
`1900`; the last two have 22 records and stride `2100`. Thus both stride families
now have actual resource owners. High12 remains a source-slot **candidate**, because
matching descriptor values does not independently establish the peripheral action.

A numerical-pointer search also finds alternative descriptors such as `610c1320`
sharing the first enum-11 range, and `610c1438` with its base but zero length.
Those matches alone cannot choose the active context. The constructor assignments
above provide the extra evidence; this is not a claim that those are the only
possible later owners or that aliases do not exist.

## Mute-counter interface: 20 bits and distinct aliases

Fantom assertion-linked setter `0113071c` checks signed DSP index <6, address bits
0..2 clear, count <`100000`, then address bit 3 clear. Consequently admitted positive
record addresses are 16-byte aligned and counts are 20-bit unsigned values. There
is no explicit negative-DSP guard in this body; the intended valid DSP range must
not be inferred solely from its signed upper-bound comparison.

The setter derives offset `(record_address >> 3)*8 + 4`, then writes the count
**three times** to that address. It finally reads `41100000`. For DSP d=0..5:

| Bool / operation | Aperture base |
|---|---|
| false setter | `41448000 + d*100000` |
| true setter | `4144c000 + d*100000` |
| false getter | `41448000 + d*100000` |
| true getter | `41444000 + d*100000` |

Getter `011307a6` requires only eight-byte alignment, waits for bit31 of
`41100008` to clear, reads the second-word position and extracts low20 with UBFX
at `011307f2` / `01130800`. These are concrete stock counter ports and argument
checks. The setter's alias writes are not a CPU read/modify/write of the entire
original program word; preservation of other fields is not established by this
body alone. Counter progression, decrement interval and its relationship to the
RAMCLR records' address stride remain unknown.

Manager wrapper `01133c2a` additionally restricts symbol enum to 11 and walks the
symbol's reference records, choosing only DRAM-IO references with the tested flags,
resolving segment-relative program addresses before calling the driver. Calling
that driver directly would omit this owner/symbol selection. No live caller or
counter-write generator is provided.

## A separate whole-resource clear interface

Native `CSimDspMgr` vtable export `009e53f8` has address point `009e5408`.
Its consecutive virtual offsets `1c8/1d0/1d8/1e0` resolve to exported methods
SetDramIOMuteCounter (`000fcf64`), GetDramIOMuteCounter (`000fd000`),
ClearIdmEdmMemory (`000fd0ac`) and IsClearIdmEdmMemoryBusy (`000fd0b0`).
Corresponding Fantom 32-bit manager slots `e4/e8/ec/f0` at address point `6117647c`
resolve to `01133c2b/01133d8d/01133e55/01133e69`. The first two have independent
assertion names. The latter wrappers' argument reshuffling also matches the named
native signatures. This is vtable/ABI corroboration of the interface identity,
rather than a firmware assertion directly naming the otherwise unnamed driver.

At `01133e54`, the wrapper drops manager-this and forwards the four arguments
`(domain_bool, start, count, completion_bool)` to driver `01130814`.
Busy wrapper `01133e68` similarly forwards the bool to `01130806`.
The driver's observed contract is:

1. Select `41100040/44` for true, `41100050/54` for false. Poll control bit31;
   while busy, call the shared wait routine with raw count `28` and completion 1.
2. If completion is nonzero, clear bit0 in shared flags at `200847f8`.
3. Write start to the selected first register and
   `c0000000 | (completion << 28) | count` to its control register.
4. Completion false returns after issuing that command. Completion true polls
   flag bit0, clears it after observation and writes `c0000000` to the selected
   control register afterward.

There is no explicit start/count clamp, mask or bounds check in this driver before
that OR. Native parameter types/stock call values do not establish arbitrary input
safety. A no-wait return is not completion. Both bool domains share that same completion bit. The body has no ownership lock or timeout.

Driver initialization at `0112f496..49a` registers callback Thumb pointer
`0112f445` for firmware event `17`. Callback `0112f444` ORs bit0 into `200847f8`.
This connects the compiled completion flag writer and registration. The event
identifier is not established here as NVIC IRQ23, and the complete peripheral
interrupt/mask path is not claimed recovered by this pass.

## Real global callers differ between the products

Fantom entry `6102a230` sets r6=1. At `6102a3b4..3c4` it stores that value as the
stack completion argument, sets bool true, start 0, and count `1<<23`, then invokes
manager slot ec. JUPITER-X entry `61028940` sets the same constant, but its call
at `610289b8..9c8` uses count `1<<22`.

| Product | Call | Bool | Start | Count, in unproved address units | Completion |
|---|---|---:|---:|---:|---:|
| Fantom | `6102a3c4` | 1 | 0 | 8,388,608 | 1 |
| JUPITER-X | `610289c8` | 1 | 0 | 4,194,304 | 1 |

These are actual compiled whole-resource initialization calls, not a reset limited
to one effect descriptor. The interface name and large counts support an EDM-related
interpretation, but size agreement alone does not prove the bool-domain mapping,
address unit or physical clearing effect. Counts are not labeled bytes or samples.
They do not make this call appropriate inside an active custom-effect transition.

The native `DramioWr` / `DramioRd` routines separately calculate a double-array
index `(queued_address - origin) & 3fffff` at `0016d288..290` and `0016d2b4..2bc`.
This shows origin-relative native addressing. It does not establish how the hardware
RAMCLR address field changes with time or that the global clear command uses that
same origin/unit. The shared timer's raw waits are also a different mechanism.

## Reproduce and remaining proof

```sh
python3 tools/dramio_owner_study.py
python3 -m unittest discover -s tests -p test_dramio_owner_study.py -v
python3 tools/core1.py local/b0c1a.bin --address 0x113071c --size 0xea
python3 tools/core1.py local/b0c1a.bin --address 0x1130814 --size 0x7e
python3 tools/core1.py local/b0c1a.bin --address 0x6102a3b4 --size 0x12
```

Use the existing Capstone-capable interpreter. The read-only report pins the input
identities, checks constructor and control/caller instruction anchors, verifies the
native manager slots, and reports all eleven owners with `execution_ready: false`.
It neither emits a target command nor executes a clear. Three tests cover descriptor
index/instance separation, bounds/capacity rejection, unknown artifacts, all eleven
real owners and the differing global count constants. Two run without artifacts.
No Qwen draft was needed for these direct dataflow/table checks.

Still missing: independent high12 source/action semantics, actual DRAM-IO cadence,
bool-domain/address-unit identity, complete interrupt delivery and owner-coordinated
selective-clear bounds. Therefore the `1900/2100` stride families still do not prove
exact hardware history coverage, and no runnable engine/reset recipe is supplied.

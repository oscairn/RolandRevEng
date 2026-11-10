# IDM/EDM names from a stock diagnostic, with a control-label defect

There is now a semantic anchor for the two Boolean banks: the stock Fantom
diagnostic prints monitor `41100058` as **IDM_MON** and `41100048` as **EDM_MON**.
Joining those monitor banks to the already traced access/clear selectors gives
the firmware's naming convention **false → IDM, true → EDM**. This rests on
explicit diagnostic text and its argument dataflow, not the large initialization
counts. However, that same diagnostic reads one control register twice under two
different names. Its labels are software evidence, not a validated hardware
register specification. Bulk-clear count units remain unresolved.

This follows [the clear interface](dramio-owners-and-clear-interface.md) and
[completion study](clear-completion-interrupt-study.md). It does not repeat the
IRQ80 or per-element progression proof. This pass used offline Capstone only;
REA was unavailable and no setup retry, target execution or device access occurred.

## Explicit monitor names and the contradictory control values

Fantom BMC0 CORE1 payload SHA-256 is
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
In function `61018260`, literal `61018604` supplies peripheral base `41100000`.
The following loads and format arguments are direct observations:

| Load | Captured register | Value passed to formatter | Format string address and label |
|---|---|---|---|
| `6101826c` | `41100054` → fp | fp → r1 at `610182ac` | `61018608`: `IDM_CTRL` |
| `61018270` | `41100054` → stack | stack → r1 at `610182d6` | `61018630`: `EDM_CTRL` |
| `61018274` | `41100058` → sl | sl → r1 at `610182bc` | `61018618`: `IDM_MON` |
| `61018278` | `41100048` → sb | sb → r1 at `610182e8` | `61018640`: `EDM_MON` |

Each format string is addressed with an `ADR r0` and passed to the same
formatter `610153e8`; the four calls are `610182b0`, `610182c2`, `610182d8`, and
`610182ee`. The monitor lines also pass the corresponding retained value from
the screen object as their second numeric argument. There is no reversed branch
or intervening reassignment that swaps the captured monitor values.

The named-monitor join to the previously established Boolean register paths is:

| Driver Boolean | Selector/control pair | Monitor in same bank | Diagnostic name |
|---:|---|---|---|
| 0 / false | `41100050 / 41100054` | `41100058` | IDM |
| 1 / true | `41100040 / 41100044` | `41100048` | EDM |

**Observation:** the monitor names unambiguously distinguish the banks in the
compiled diagnostic. **Inference:** these are the intended IDM/EDM names for the
driver's Boolean parameter. **Limitation:** the controls cannot independently
corroborate that inference: both control labels receive `41100054`, and the
screen never reads `41100044` for either control label. The likely explanation
is a copied control-load error, but that cause and the physical register names
have not been validated on hardware. Keep the discrepancy visible instead of
silently repairing the firmware's text or reads in a derived map.

The same diagnostic prefix and named-monitor assignment occur in the official
peer firmware. All three peers also retain the duplicate-54 control reads:

| Image | Function runtime address | Original C1A file offset, `sdram1.bin` | Checked length |
|---|---|---|---:|
| JUPITER-X v3.03 | `61011a7c` | `50a9c` | `a4` |
| MC-101 v1.82 | `61008970` | `45990` | `a4` |
| SH-4d v2.00 | `6100e974` | `4f994` | `a4` |

The JUPITER-X and MC-101 windows are byte-identical, SHA-256
`9a2d2fdf3170eed3dc2baabbe2a6fc8b89ea5933e28ee5dfec11822554f24c9e`.
The SH-4d window SHA-256 is
`c950a08db363c2c4e35f261bb5cad671490f1bc149af244cc86a8d4953a9a00a`.
The four `ADR` targets and their actual strings were checked in each original
member mapping. Container hashes and extraction provenance remain those in the
[JUPITER-X](jupiter-crossmodel-c1-study.md),
[MC-101](mc101-v182-core1-comparison.md), and
[SH-4d](sh4d-and-tr8s-firmware-study.md) studies. `qspi_c1.parse_c1` verifies outer
CRC and preserves the individual 32-byte member prefixes in the source-offset
calculation. These are shared-code observations, not independent hardware tests
or a correction of the control-label defect.

## Why the named native interface does not settle clear units

The pinned ZENOLOGY arm64 artifact SHA-256 is
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Its exported native endpoints are:

| Export | Address | Observed implementation |
|---|---|---|
| `CSimDspMgr::ClearIdmEdmMemory` | `000fd0ac` | `RET` |
| `CSimDspMgr::IsClearIdmEdmMemoryBusy` | `000fd0b0` | Return zero |
| `CSimDspMgr::WriteIdmEdmMemoryFloat` | `000fd0b8` | `RET` |
| `CSimDspMgr::ReadIdmEdmMemoryFloat` | `000fd0bc` | `RET` |

These endpoints provide no backing-memory selection or clear loop to compare
against the firmware count. For example, the implemented native fixed writer
converts input data, preserves the Boolean/start/count arguments and invokes
virtual slot `1e8` at `000fd1dc..1f8`, whose base-table target is the float writer
stub. The fixed reader similarly invokes slot `200` at `000fd248..264`, whose
base target is the float reader stub. This does not exclude every hypothetical
derived override; it means these named base implementations do not supply the
missing semantics. Existing native RAMCLR loops are separate operations with
their own masks and ranges.

The tempting `CEZUtilIDMEMSum` / `IDMEM Check Sum` diagnostic is also a separate
domain. Its firmware UI calls `61021320` at `6107db54`. That helper sets source
base `01100000` and reads successive CPU instruction-memory halfwords, with
per-block and aggregate checksums. It does not call the IDM/EDM portal methods
or select either `41100040/50` bank. Its native `CalcSum` endpoint at `003e9968`
is itself a `RET` stub. The similar name is not evidence about DSP IDM units.

## Bounded caller search and the remaining count contract

The native/firmware manager table correspondence places clear at firmware slot
`ec`, write float/fixed/raw at `f4/f8/fc`, and read float/fixed/raw at
`100/104/108`. A halfword-aligned search of the actual ITCM/ERAM spans for the specific
`LDR.W Rt,[Rn,#imm12]` unsigned-immediate form excludes PC-relative literals.
No candidate may straddle the unmapped runtime gap. It finds only `6102a3be` for slot `ec`, the already documented stock global clear
call. It finds no non-PC candidates for `f4`, `fc`, `104`, or `108`. The five `f8`
hits access an object field. The three `100` hits include an NVIC enable-register
read (`0110247e`) and two unclassified encoding matches (`0110b330/0110b786`);
none was established as a portal call. This is a candidate search for one instruction form,
not proof that the methods have no callers: register-offset loads, different
encodings, derived tables, indirect routing and dead/data bytes remain outside
that conclusion. In particular, PC-relative loads with immediate `108` must not
be mistaken for calls through virtual slot108.

The existing actual global and startup clear sites pass low-field constants
without an explicit named unit or a read-back comparison to a known indexed
range. Calling their counts bytes, samples, physical words, an inclusive end
address or an exact owner-history extent would add an unsupported assumption.
The monitor labels improve the software naming of the Boolean domain, but do
not change this count boundary. No live clear command or admission of a safe
selective reset follows from this study.

## Reproduce

```sh
python3 tools/memory_domain_study.py local/b0c1a.bin local/zen_arm64
python3 -m unittest discover -s tests -p test_memory_domain_study.py -v
python3 tools/core1.py local/b0c1a.bin --address 0x61018260 --size 0xa4
python3 tools/core1.py local/b0c1a.bin --address 0x61021320 --size 0x62
```

Use the existing Capstone-capable interpreter. The read-only checker pins both
artifact hashes, checks the label/load/formatter argument anchors, decodes each
actual `ADR` string target, retains both contradictory control lines, checks the
native endpoint stubs, reproduces the bounded load-candidate search, and reports
source spans/hashes. Three tests cover PC-literal exclusion, unknown-build
rejection and the actual corpus result including its discrepancy. Peer offsets
above were additionally checked against the original mapped members.

Answered at software-diagnostic level: the bank names false/IDM and true/EDM.
Still unresolved: physical-name validation, bulk-clear count unit and exact
hardware extent, wrap behavior, and owner-coordinated selective reset safety.

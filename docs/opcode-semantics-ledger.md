# DSP control semantics ledger

2026-11-10. This index consolidates the **bounded semantic proofs** scattered
across the studies. It is not a general instruction-set specification. The unit
of admission is the exact header/control/extension/operand context checked by the
linked recognizer, not a 16-bit word in isolation. No listed form has run on BMC
hardware in this research. The main [packet/loader map](BMC%20DSP%20packet%20and%20loader%20map.md)
records the separate access and engine requirements.

`A/B` mean incoming functional main values; `I0..I7` mean functional input ports.
These names do not establish physical registers or readiness/latency. Arithmetic
equalities compare independently traced native expressions; they do not establish
rounding, saturation, accumulator width or fused evaluation on silicon.

## Independently checked arithmetic contexts

| Control or base/extension pair | Functional result in the checked context | Evidence and scope |
|---|---|---|
| `0401 / 4501` short pair | A/B × I1 | [Gain study](alu-controls-study.md), EH tail |
| `0403 / 4503` short pair | A/B × I3 | Gain study, 12 effect tails / 24 channel chains |
| `0407 / 4507` short pair | A/B × I7 | [Stereo taps](stereo-tap-accumulation-study.md), TS808 gain stage; asymmetric B examples also in gain study |
| `080b / 13c0` | A = I0×I3 + I1×I7 | [Dry/wet MAC](dry-wet-mac-study.md), FETDRIVE and LINEDRIVE exact six-packet family |
| `490b / 53c0` | B = I4×I3 + I5×I7 | Same dry/wet family |
| `080b / 1280` | A = A×I3 + I1×I2 | [Further MAC controls](mac-controls-and-issue-study.md), LFCOMP exact four-packet family |
| `490b / 5280` | B = B×I3 + I5×I2 | Same LFCOMP family |
| `0e0b / 22c1` | A = I1 + (I2−A)×I3 | Further MAC controls, two LINEDRIVE four-stage allpass chains |
| `0e0b / 12c2` | A = I2 + (I1−A)×I3 | Same allpass chains; subtraction signs independently checked |
| `044f / 0000` | A = A + I1×I7 | Stereo taps, first TS808 state term |
| `454f / 0004` | B = B + I5×I7 | Stereo taps, first TS808 state term |
| `048f / 0000` | A = A + I2×I7 | Stereo taps, second TS808 state term |
| `458f / 0004` | B = B + I6×I7 | Stereo taps, second TS808 state term |

For the first gain row the slash separates two **short controls**. In long rows,
it separates a base control from its extension. Headers and shared pool layout
determine which interpretation applies. Read the linked context before using a row.

The [tap-feedback variation](tap-feedback-variation-study.md) adds a different kind
of constraint. Two later TS808 contexts contain short `2403/6507`, then long
`044b/0002` + `454f/0006`, followed by `044b/0000` + `454f/0004`. Complete native
expressions distinguish auxiliary products `P=W×G`, first sums `U=P+state1×F`
and final sums `V=U+state2×H`, while main-port stores retain unscaled W.
These are whole-context roles: ports3/7 carry equal F/H in those examples, so
their source selection is **indistinguishable**, and no isolated extension-bit
or physical auxiliary-register meaning is admitted. The explicit alternative
hypotheses and counterexamples belong to the result, not just a footnote.

## Transfers, payloads and ordering

The [transfer-provenance study](transfer-spaces-study.md) and arithmetic studies
check contextual indexed loads/stores, including main A/B loads `0feN/4feN`,
main stores `8feN/cfeN`, and observed input-port loads. N is an even pool-byte
reference in those family-4 forms. Address words must be interpreted in their
decoded role; extensions and literals can share the same bit patterns.

Tag0 accesses the checked circular data path. Tag2 has another native circular
path; it is not globally physical host IO. Tag4 has a separate direct/window
CBMCDrm-backed path, not globally coefficient RAM. TagC live coefficient records
are constructor-proved resources. None of these contextual facts is a universal
hardware memory-map specification.

Main-port stores in the admitted mixed packets capture **incoming** main values.
A concurrently loaded coefficient is consumed by following arithmetic in the
checked examples. Base-word order is not an issue schedule. The tap variation also
shows native compiler hoisting: a product may precede a store of its input, so
unchanged register/alias provenance is required instead of matching equal expressions.

## Explicitly unresolved forms

| Form or feature | Current boundary |
|---|---|
| `00aN`, `00f8`, `0bc3`, `28bb` | [Condition/return study](condition-fields-and-implicit-return-study.md) anchors field inputs and predicates, not condition bits, return storage or transfer timing |
| `20a0/20a4/20a5/30a0/30a2` | [Exceptional-op study](special-ops-and-exp-study.md) excludes misleading literal aliases; whole exponential windows are not single-op semantics |
| `3074`, `2d64/0c3b`, remaining oscillator forms | [Oscillator comparison](oscillator-layout-candidates.md#cross-context-reuse-of-3074) finds 119 short `3074` contexts and literal/store bindings. The `2d64/0c3b` extension owner and oscillator recurrence remain open |
| `ff70/ff71/ff75` and entry wrappers | Stock mutability/placement is mapped; safe standalone execution and universal stop/run meanings are not proved |
| OSC `0c30 / 1410 / 8ee0 / 3c10 / 8ee1` window | [Phase study](oscillator-phase-study.md) binds the stored phase rule and owned frequency field. Individual exceptional state and port effects remain open |
| DRAM-IO records, bulk clearing | Owners, addresses and completion paths are mapped; cadence, exact extent/count units and selective-reset safety remain open |
| Arbitrary scheduling, numeric behavior | No hardware timing, hazard, precision or clipping calibration exists |

## Existing code generation

[Supported generation](supported-code-generation.md) exposes fixed fragment profiles in `bmc_subset.py` for stereo input, dry/wet gain, the
dry/wet tail with scratch transfers, and four-stage allpass. Their
resource and packet ordering restrictions remain in force. Stereo taps and the
feedback variation are semantic studies, not new emitter templates. No entry/exit
wrapper, allocator, general register decoder or custom synth engine follows from
the ledger. Live coefficient smoothing is a separate
[CORE1 manager interface](coefficient-envelope-and-completion-study.md), not a
DSP arithmetic opcode or a program-literal write.


## Executable offline subset

The [functional fragment interpreter](fragment-emulator.md) now executes only the
same exact stereo input, dry/wet, scratch, allpass and VSOD coefficient-prefix contexts accepted by the inverse decoder. It steps
packet bytes with old-port arithmetic/stores, next-packet loads and copied trace
snapshots. [Corpus validation](fragment-emulator-validation.md) checks the actual
stock spans and native proofs independently. The additional
[`coefficient_shift4` profile](fragment-emulator.md#stored-fixed-point-coefficient-prefix)
executes `0812/1500`, `fdd4` and the port-7 store under the native
numeric policy. Other arithmetic entries above
remain study results, without executable admission. Binary64 reference behavior
is not calibrated silicon precision or timing. The
[next-program inventory](emulator-next-program-targets.md) keeps complete-program
prefix, suffix, history and wrapper gaps explicit.


## Native prefix oracle and state context

The [LINE shaping study](line-prefix-shaping-study.md) checks exact native
signed64/fixed32 conversion, shift9 wrapping, sign/clamp, fused smoothing and
rational arithmetic. These are native reference kernels, **not isolated DSP
opcode assignments** for the containing packets. The shaping study admits no additional DSP controls. The [state study](line-state-and-history-study.md)
recovers a native ring origin and conditional cross-call history relationships,
not a hardware circular-addressing rule.

[Counted literal groups](line-prefix-parameter-study.md) explain actual rational
parameter duplicates through a declared operation; the missing input-mix group
relation remains unproved after a [bounded static inventory](line-prefix-global-groups.md).
The [JUPITER-X comparison](emulator-next-program-targets.md#jupiter-x-carries-an-asymmetric-instance-of-4822--1940)
establishes unequal stored literals for the exact `4822 / 1940` form in a separate
program. Its native setup locates the list. DSP values and port timing remain open.
The [weighted-sum comparison](emulator-next-program-targets.md#weighted-sum-ports-across-trecho-bitcrush-and-the-reverbs)
ties `4812 / 1500` to the next main-B store in TRECHO and `2424 / 0004` to an
`A × literal + B` result in port 2 in BRHL. The `4822 / 1940` candidate keeps
the same nonliteral bits as `4812 / 1500`. UPLIFT EXCITER's `3464 / 0002` ties
port 1 and the previous accumulator to a port-3 result. LINE uses `3467 / 0004`,
with B in the candidate addend position. The LINE packet sequence remains
outside strict execution.

The [VMCP and RING comparisons](line-prefix-shaping-study.md#vmcp-and-ring-separate-9ed9-from-fixed-point-conversion)
support a bipolar clamp for `9ed9` in two store-bracketed contexts. VMCP's
shift-by-2 and shift-by-4 reference windows align separately with `bc12` and
`bcd4`. The precise register and exceptional-state effects remain open.
The [stock context inventory](line-prefix-shaping-study.md#stock-contexts-of-9c59)
finds the same `1405`, `9c59`, `9ed9` sequence at all 58 exact hits.
An intermediate result for `9c59` remains open.

The [fixed-point shift comparisons](line-prefix-shaping-study.md#fixed-point-shifts-in-vmcp-vsod-formant-and-gassph)
match `bcd4` to port-3 input across VMCP and both VSOD variants. The base
VSOD `fdd4` form has a matched port-7 load and result store. FORMANT uses
`bcd2` in a separate port-3, shift-by-two context. GASSPH pairs `fdd2` with a
native shift by two and a port-7 result store.

The [conditional LINE render](fragment-emulator.md#conditional-line-reference-pipeline)
is a host oracle plus supported fragments, with explicit fixture state and
software timing. It does not skip unknown words to manufacture complete program
execution.

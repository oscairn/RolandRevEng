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

The [Fantom ARM32 control checkpoint](fantom-eqvg-control-study.md) verifies
selected original CPU math, setters and manager completion in private memory.
Its four active types, fallback, float32 rounding and pre-arm flag clearing differ
from desktop assumptions. It adds no BMC opcode or physical timing evidence.

The [manager processing checkpoint](coefficient-manager-processing-study.md)
executes bounded original host/simulation code for interpolation and completion.
It adds no DSP opcode or physical timing evidence; task primitives are controlled
and native literal conversion stays outside the fixture.

The [EqVg checkpoint](eqvg-filter-generation-study.md) checks five-coefficient
producers and stock interpolation decisions without new opcode admission. Native
setters and descriptor reads independently establish consumer ordering; 48
immediate filter changes match full audio/state over 12,000 frames under each
explicit output-literal precision policy. Manager processing has separate bounded
checks; actual task ownership and BMC calibration remain open.

The [EqFaCal checkpoint](fdrv-cubic-waveshaping-study.md#three-coefficient-filter-generation-and-ui-dispatch-2026-11-11)
checks generated coefficients, setter reordering and native UI calls without new
opcode admission. Input/resampling/cascade controls now receive cutoff/type/gain
updates. Nonrepresentable source doubles are handled through explicit precision
policies: either evaluate verified-bin-compatible source values, or compare both
model and owned native fixture after software quantization. Neither establishes
the physical DSP converter's rounding or arithmetic precision.

The [FDRV setter checkpoint](fdrv-cubic-waveshaping-study.md#setter-derived-live-updates-2026-11-11)
adds descriptor/control provenance and dynamic coefficient tests, without adding
an opcode profile. In particular the final filter's repeated a fields
`4ea/4ed/536/539` have one declared four-record write group. An
[independent FETDRIVE check](fragment-emulator.md#independent-fetdrive-cross-check-2026-11-11)
matches native mixed/shaped cutpoints but retains the prefix source/alias gap.
Fixed32 truncation plus LSL 9 has gain 512 and nominal scaled grid 2^-23; the native
constructor scale and encoded DSP value produce distinguishable outputs.

The [complete FDRV arithmetic checkpoint](fdrv-cubic-waveshaping-study.md#complete-arithmetic-and-output-milestone-2026-11-11)
adds long literal filter contexts `0ca4/4da7`, `0ca8/4dab`, `0c24/4d27`,
literal products `2420/6523`, literal accumulation `1426/5529`, additions
`0c02/4d06`, live products `1443/5543` and dry/wet accumulation `08c1/48c5`.
Crucially, `1464/5567` under header `420a` fuses the product with incoming I2/I6;
the same words under cascade header `5f0a` are plain products. Exact profile
admission protects that distinction. Complete final audio/ring/cache comparisons
are native-policy evidence, not proof of silicon precision or `00f8` semantics.

The [cascade checkpoint](fdrv-cubic-waveshaping-study.md#cascaded-history-filter-milestone-2026-11-11)
adds contextual short products `14a8/55ab` and `1464/5567`, plus long
`1424/5527` with extensions `0001/0005`. Repeated `1428/552b` accumulates the
other terms inside the same exact 164-byte profile. Prefetched future state cannot
affect the current outputs. [V-STAGE unseen contexts](vstage-firmware-hardware-study.md#core1-and-candidate-dsp-comparison-2026-11-11)
remain inventory observations with no new semantic admission.

The [post-cubic mix checkpoint](fdrv-cubic-waveshaping-study.md#post-cubic-history-mix-milestone-2026-11-11)
admits paired literal half gain `04a4/45a7`, quarter accumulations
`0468/456b` and `2466/6569`, live gain `2483/6583`, and fixed post gain
`24a0/65a3` only inside the exact 110-byte profile. Raw stores precede gain,
loads become visible next packet, and native/encoded scale precision stays explicit.

The [resampling/drive checkpoint](fdrv-cubic-waveshaping-study.md#connected-resampling-and-drive-milestone-2026-11-11)
adds bounded short/long roles for `1428/552b`, long `0424/4527` with extensions
`0001/0005`, and short literal gain `0426/4529`. Arithmetic and history stores
are independently checked with nonzero tap weights. Fantom uses literal `100000`
where ZENOLOGY uses `0656d2`; the native-reference precision distinction is explicit.
These words execute only inside the exact 122-byte profile, extending the chain
through cubic shaping; they are not a general ALU decoder.

The [four-section FDRV checkpoint](fdrv-state-variable-filter.md#four-section-filter-bank-milestone-2026-11-11)
adds exact terminal short-packet contexts for the existing recombination words
and a store-extended profile. No new arithmetic word is admitted. The 902-byte
composed chain matches 336,000 native-prefix values before resampling arithmetic;
the whole effect and silicon semantics remain unresolved.

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
| `1c42 / 5d46` short pair, then `044b/0000` + `454f/0004` long pair | In the exact FDRV context, sum I1+I2 and I5+I6, store incoming I1/I5, then accumulate the sums into A/B with a shared coefficient | [Auxiliary/add-MAC study](auxiliary-save-restore-and-add-mac.md), strict 84-byte profile; coefficient-port ambiguity retained |
| FDRV `66..f8` filter context | Two coupled state updates, a weighted output, and balanced port-2/port-6 saves/restores | [State-variable filter](fdrv-state-variable-filter.md), strict 184-byte profile; no word-only decoding or physical stack-depth claim |

| FDRV `378..3ec` cubic context plus authored preload | Four `x×(x²+3−abs(3x))` curves, with old-value stores and final reloads | [Cubic study](fdrv-cubic-waveshaping-study.md), strict 126-byte profile; six new short multiplies and two exact literal-minus-magnitude forms, no universal masked-class admission |

| FDRV `33c..378` interpolation/clipping context plus authored preload/store | Two half-sample averages followed by clipping, two direct clips and unclipped history stores | [Clipped-half study](fdrv-cubic-waveshaping-study.md#stereo-half-sample-interpolation-and-clipping), exact 80-byte profile; no universal long-form or limiter decoding |

| FDRV input `0..4c`, plus authored mixed stores | Per channel, input×C5 followed by two ordered FMAs; raw/history stores and coissued prefetches | [Input stage](fdrv-state-variable-filter.md#completed-input-to-first-filter-stage-2026-11-11), exact 86-byte `stereo_prefilter`; combined 270-byte stage checked against native execution, no general opcode admission |

| FDRV f8..1aa second-filter/recombination context plus authored preloads | Second stereo filter then fma(wet,g,fma(-dry,g,dry)); old g survives coissued future loads | [Second-filter milestone](fdrv-state-variable-filter.md#second-filter-and-recombination-milestone-2026-11-11), exact 216-byte profile; FMSUB sign checked by native execution, with no word-only admission |

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

The [label-target writer](label-target-encoding-study.md) independently proves
byte-target right-shift-by-one before counted program-field writes. Five parent
words match this scaling, but no counted descriptor binds those words to the
candidate controls. This is host-manager encoding evidence, not admission of
`00aN` or a CALL/RETURN execution rule.
| OSC `0c30 / 1410 / 8ee0 / 3c10 / 8ee1` window | [Phase study](oscillator-phase-study.md) binds the stored phase rule and owned frequency field. Individual exceptional state and port effects remain open |
| `bedb` | [Late phaser stores](operand-variants-and-macro-boundaries.md#late-phaser-clamp-stores-and-native-execution) prove a bipolar-clamped port-3 result in STPS/TVPS contexts and separate it from FETDRIVE division. Exact input selection and other state effects remain open |
| DRAM-IO records, bulk clearing | Owners, addresses and completion paths are mapped; cadence, exact extent/count units and selective-reset safety remain open |
| Arbitrary scheduling, numeric behavior | No hardware timing, hazard, precision or clipping calibration exists |

The [short-add context inventory](short-add-context-candidates.md) adds fifteen
family-1 candidates across nine classes. TRANSIENT's short `5d72` four-byte
operand is bound to its native decay default, while long `5d72` and miscellaneous
`5d50` remain distinct forms. Native additions in four other classes strengthen
the hypothesis, but source-port and co-issued effects prevent isolated admission.

## Existing code generation

[Supported generation](supported-code-generation.md) exposes fixed fragment profiles in `bmc_subset.py` for stereo input, dry/wet gain, the
dry/wet tail with scratch transfers, and four-stage allpass. Their
resource and packet ordering restrictions remain in force. Stereo taps and the
feedback variation are semantic studies, not new emitter templates. No entry/exit
wrapper, allocator, general register decoder or complete on-device synth engine follows from
the ledger. Live coefficient smoothing is a separate
[CORE1 manager interface](coefficient-envelope-and-completion-study.md), not a
DSP arithmetic opcode or a program-literal write.


## Executable offline subset

The 84-byte `register_add_mac_pair` profile now admits the exact state-add/MAC
context above. It supplies its own input data loads, preserves the shared-factor
constraint and checks binary32/native-FMA behavior. It executes no auxiliary
save/restore word. The cubic and clipped-half windows have their own separate exact profiles.

The [FDRV cubic window](fdrv-cubic-waveshaping-study.md) has an exact 126-byte
profile, four constructor-bound source/result relations and directly executed
native arithmetic. Its upstream interpolation/clipping window now has a separate
80-byte profile. Both retain complete-context admission; arbitrary short words,
miscellaneous forms and full-effect execution remain unproved.

The 184-byte `state_variable_pair` profile now executes the first FDRV filter
block including its producers and one balanced auxiliary save/restore per port.
Its reference preserves binary64 states, binary32 coefficients, native FMA and
the verified `FNMSUB` sign. The native callback comparison covers all valid
cursor pairs and ring wrap. Admission of the separate cubic and clipped-half
profiles does not generalize the remaining filter or producer contexts.

The [functional fragment interpreter](fragment-emulator.md) now executes only the
exact stereo-input, mix/scratch, allpass, VSOD coefficient-prefix, add/MAC,
state-variable, cubic and clipped-half contexts accepted by the inverse decoder. It steps
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

The [OSC sine study](oscillator-sine-study.md) checks the native phase fold,
seven polynomial literals and three waveform stores. Direct native execution
agrees bit for bit at 525 phases, including narrow sign/fold boundary intervals.
Four Fantom placements retain the context. The `e037` load is a fixed-input
candidate for the native pi scale in this window. Exceptional state and a
general constant-bank mapping remain open; no strict OSC profile is admitted.

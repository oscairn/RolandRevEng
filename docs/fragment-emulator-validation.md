# Stock-fragment validation of the offline emulator

Follow-up: [auxiliary saves and add/MAC](auxiliary-save-restore-and-add-mac.md)
documents another exact byte-executed profile, with native-paired and five Fantom
body comparisons, all-port traces and 1,024 direct native arithmetic comparisons.
The original dry/wet/allpass checks below retain their existing numeric policy.

The [complete first filter block](fdrv-state-variable-filter.md) adds a 184-byte
profile and compares 105,232 native prefix/state/output values, including a
12,000-frame ring-wrap run. This validates a reusable component, not complete
FDRV effect or hardware execution.

The corpus tests compare the emulator with independently recovered native
equations for four actual stock fragments: the FETDRIVE and LINEDRIVE dry/wet
tails, plus both LINEDRIVE four-stage allpass regions. The tests extract those
logical bytes from the pinned local artifact; they do not obtain the input by
calling the fragment emitter. No plugin, native audio processing, firmware or
device is executed.

All five tests passed against the actual reviewed implementation, with no skips.
They made 33 pure Python fragment calls: twelve individual-vector calls, twelve
sequential purity calls and nine calls composing the actual adjacent LINEDRIVE
regions. The native identity/evidence check also passed. These are software
validation results, not observations of hardware or native plugin audio.

## Source and evidence gates

The input is the prepared ZENOLOGY arm64 artifact SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
`parse.program()` selects the primary render bank using the existing retained
class/program metadata, converts its LE32 storage words to logical byte order,
and only then slices the fragment. The tests verify full native identity,
stored program location, logical program length/hash and fragment hash.

| Class / region | Render storage base in native file | Logical offset | Logical length |
|---|---|---|---:|
| FETDRIVE tail | `8372f4` | `16a` | 60 bytes |
| LINEDRIVE tail | `7b47f4` | `1e2` | 60 bytes |
| LINEDRIVE allpass A | `7b47f4` | `13e` | 82 bytes |
| LINEDRIVE allpass B | `7b47f4` | `190` | 82 bytes |

These offsets describe logical slices within whole converted render programs,
not independently aligned stored fragments. FETDRIVE's full logical program is
`1ca` bytes, SHA-256
`f9bba6a4925d42d331321ef4978f9d2f53b35b251c5074eef72e119ec3670689`.
LINEDRIVE's is `242` bytes, SHA-256
`a7306c45ee503e60061261f9fa0fde3f8dfc708e6c245b3868e917e6a7d3ea02`.

| Fragment | SHA-256 of logical bytes |
|---|---|
| FETDRIVE tail | `b3f2705a2b17a1a14069732abed9601c7f573d42a4d62e08cd70412493dbc424` |
| LINEDRIVE tail | `ea486c0fd1b373ad63cb605bf403876b5377bef41aecde0d68b550353e5b4638` |
| LINEDRIVE allpass A | `3093df0fae326f90368be9f7e01bf4bff4a5196bdf46517296b29d39a6c6cda3` |
| LINEDRIVE allpass B | `b75c1844217c33115f7dadbabf7c2d2d1f382e4ad5ab48b46ea3efc38357338f` |

Before numerical execution, `mac_study.study()` must independently report both
tail native polynomials as matched. Their native processing functions span
`2f7de4..2f81c4` and `2df874..2dfd94`. The
[dry/wet study](dry-wet-mac-study.md) documents coefficient-record and audio
pointer provenance, wet-value cut points, and full polynomial comparison.

`mac_controls_study.study()` must verify both allpass chains, all six native
stores per chain, and their fully decoded branch-free native windows
`2dfad8..2dfbc8` and `2dfbd8..2dfcc8`. The
[MAC/store-order study](mac-controls-and-issue-study.md) supplies that evidence.
The numerical expectations below are authored directly from those equations;
they do not call emulator arithmetic helpers or the emitter.

## Independent numerical and trace expectations

For each tail, the test assigns distinct signed dyadic values to left/right
input, left/right wet state, dry/wet coefficients, post gain and master gain:

```text
mL = L*dry + WL*wet
mR = R*dry + WR*wet
outL = (mL*post)*master
outR = (mR*post)*master
```

It compares all eight final ports and every before/after port snapshot at
packet offsets `0,10,20,34,44,54` decimal. In particular, packet34 computes the
right mix with the old dry coefficient before loading post gain; packet44
consumes post before loading master; packet54 consumes master. Checking only
the final output could miss a post/master load-timing error because those two
gains commute. The tails must produce no data-memory writes.

For each allpass region, seven independent source values are named
`x,a,b,k,c,d,e`. The direct recurrence is:

```text
u0 = a + (b-x)*k
u1 = b + (c-u0)*k
u2 = c + (d-u1)*k
u3 = d + (e-u2)*k
```

All seven before/after snapshots are checked, including the newly loaded state
input and held factor in ports1/2/3. Every write address and value is checked:

| Packet offset, decimal | Data write(s) | Main value after packet |
|---:|---|---|
| 0 | none | x |
| 10 | previous = x | x |
| 24 | none | u0 |
| 34 | stage0 = u0 | u1 |
| 48 | stage1 = u1 | u2 |
| 62 | stage2 = u2 | u3 |
| 72 | output = u3, copy = u3 | u3 |

This distinguishes the incoming-state stores from stores of the newly computed
value. The vectors require x/u0/u1/u2/u3 to differ. Target locations initially
contain unrelated sentinels, and an unused data location must remain unchanged.
The allpass factor comes from its actual **data-memory source**, not the
coefficient mapping; the coefficient input mapping is empty for these chains.

Three deterministic asymmetric vectors are used per fragment. Values are small
dyadic fractions, with enough representable precision for the selected short
calculations, so exact Python-float equality is appropriate for these fixtures.
This is an original software test choice; it is not a hardware precision claim.

Each execution must leave input data, coefficient and IO dictionaries unchanged
and return a distinct updated data mapping. A further three-call sequence per
fragment carries copied returned memory, explicitly updates source values for
each call, compares the full resulting mapping, and verifies earlier results
and trace snapshots remain unchanged after later calls. That sequence tests
API purity and state isolation; it does not infer the broader stock program's
delay-state update cadence or assemble a complete running effect.

A further composition test uses the actual adjacent LINEDRIVE regions
`13e → 190 → 1e2`. The two allpass output targets, DM[`29`] and DM[`2a`], are
the following tail's two wet sources. Returned memory is passed directly from
allpass A to allpass B to the tail, with no oracle values written into those
target locations. The final mix is independently calculated from the two u3
equations. This verifies a real stored-value/read boundary while retaining the
fragment API's fresh port state at each invocation; all needed ports are loaded
before consumption inside each admitted fragment.

A bounded no-tools Qwen review suggested checking cross-invocation state
propagation. Its claimed same-allpass target/source aliases were incorrect:
the admitted chain has thirteen distinct source/target addresses. The useful
narrower suggestion became the actual allpass→tail memory test above. Its
objections to fixed offsets and per-packet traces do not apply to these pinned
byte families and the agreed trace API; its proposed hardware-precision edge
coverage is outside this functional model. Expected numerical values are
computed from the equations, rather than copied into large literal tables.

## Run and interpret the results

```sh
python3 -m unittest discover -s tests -p test_fragment_emulator_corpus.py -v
```

Use the existing Capstone-capable interpreter and ignored local `zen_arm64`,
`pairs.json` and `exports_dem.txt`, or set `BMC_CORPUS_DIR` to their directory.
Without that corpus the artifact-dependent checks skip explicitly. The emulator
is a required tracked dependency: with the corpus prepared, a missing emulator
module fails the execution tests rather than silently skipping them.

Passing these checks establishes agreement with the admitted equations for
these exact fragment families and fixtures. It does not establish native
plugin audio equivalence, bit-exact BMC arithmetic, fused rounding, saturation,
cycle timing, arbitrary packet scheduling, resource ownership, a complete
effect engine or a device execution wrapper.

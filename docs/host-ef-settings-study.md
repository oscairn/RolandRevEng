# Host 0xEF settings traffic: who sends it, who checks for replies

2026-11-13, glm-overnight-2 run 4. Static cross-check of the 2026-11-12 unit
measurements against the pinned host binary, extending
[host-byte1-study](host-byte1-study.md), [host-status9-study](host-status9-study.md)
and [host-status9-readers-study](host-status9-readers-study.md). Inputs:
pinned `mi078` ELF (SHA-256
`90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`) and the
saved strace captures in ignored local storage
(`local/fantom-unit-2026-11-12/link-and-panel-captures/*.trace.raw`). Every
claim below is **verified** (reproduced by `tools/host_ef_study.py` and
`tests/test_host_ef_study.py`) unless marked **inferred**. No device access,
no execution of vendor code.

## Question

The unit captures show Roland's app sending settings and level parameters to
destination 0xEF ([host link measurements](fantom-host-link-measurements.md):
"which BMC answers as 0xE1, or 0xEF" is open). This note closes the *host*
half: which `mi078` code sends the measured 0xEF frames, and whether any host
receive path is prepared to consume a reply sourced 0xEF.

## Send side: 46 route sites, two parameter senders plus a service sender

- All 391 direct calls of the outer route dispatcher `00be4270` carry the
  route immediate in `w0` immediately before the call; **46** have `mov w0,
  #0xef` there. (`static_report` in the tool; matches run 1's census of
  391 total / 46 to 0xEF at route-argument level).
- The 46 sites sit in 25 enclosing functions. Of those, exactly two
  construct both a kind-7 parameter block (wrapper `00be2b98` around
  constructor `00be3e38`) and the kind-8 companion (`00be2bf8`):
  `0xc01ec0` and `0xc02010`. These are the measured senders.
- One function, `0xc170a0` (sample/operation service, `00c0f9d0` family),
  constructs a kind-9 service envelope (wrapper `00be2c60` around
  `00be2968`) with selector 0x0E and routes it to 0xEF; this matches the
  follow-up study's selector-0x0E row ("`00c17170` supplies command 6 and
  route ef").
- Three functions (`0xc249c8`, `0xc256d0`, `0xc25738`) construct only a
  kind-8 for 0xEF; the rest construct kind-7 only.
- Byte-for-byte, the slider trace's pair is
  `0e 00 ef 0e | 00 00 00 07 vv 00 0a | 05` (kind 7, selector 0x0E; byte 11
  counts a 5-byte inline payload `00 00 00 07 vv`; the trailing `00 0a` are
  stale bytes past the count) then
  `10 00 ef 00 | 0e 00 00 00 00 00 77 | 07` (kind 8, 7-byte inline payload
  `0e 00 … 77`). 388 such pairs in the slider trace; the Local Switch trace
  has the same pair with selector 1 and parameter `cf` (37 pairs). The
  kind-8 companion's inline payload begins with the kind-7 selector
  (0x0E or 0x01), supporting the earlier **inferred** reading that it
  closes/commits the parameter block.

## Companion pairing is not back-to-back on the wire

The kind-8 companion is emitted by a *separate* route call after the kind-7
one, and unrelated frames (MIDI-clock kind 3, panel kind 6) may be
interleaved between the two: in the slider trace 10 of the 388 kind-7 frames
are followed by another kind first (gap 2, never more). Any future host
implementation must not assume adjacency. (Verified from the reconstructed
write stream; the pairing count with interleaving allowed is 388/388 and
37/37.)

## Receive side: no host path is prepared for a reply sourced 0xEF

- The pinned image has exactly eight `cmp #0xe1`, six `cmp #0xe2` and eight
  `cmp #0xef` sites (`compare_census`). Classified by context:
  - Three sites compare a **received message's copied source byte** against
    0xE1: `0xbe9fdc` (kind-9 selector-6 callback `00be9fa0`), `0xc0f610`
    (selector-0d handler `00c0f5d0`) and `0xc0fe58` (selector-0e callback
    `00c0fe18`); all load `ldrb w0, [sp, #0x29]` from the stack-copied
    message first. These are the only source-byte checks on replies.
  - Four sites compare **request destinations** the caller chose: the
    version client `00cf9c40` distinguishes 0xE1/0xE2 (`0xcf9cbc`/`0xcf9cc4`,
    `ldrb w1, [x19, #1]`) and its planner `0xcfa1ac`/`0xcfa1b8` compare the
    route argument in `w2`. These match the follow-up study's "distinct
    logical peer selectors" reading.
  - Two sites are range classifiers on computed values, not frame bytes:
    `0xb899d8` (a binary-search chain whose branches materialize w2 =
    0x3c..0xb40) and `0xb44b90`/`0xb45210` (code-range classification after
    `blr` calls).
  - **No site compares any value against 0xEF.** The eight `cmp #0xef`
    sites are: a range-classifier bound (`0xb894b8`, sibling bounds
    0x3b/0x4f/0x77/0x9f/0x1df), a computed-code check (`0xbf1f44` on `w3`
    after `blr`), a shift/flag computation (`0xc345e4`, `0xd6bfec`),
    MIDI-status parsing (`0xce8264` inside a byte-stream parser whose next
    compare is `#0xf0`; `0xe88eb0`/`0xeaa884` check for a 0xEF,0xBB
    byte pair, a UTF-8 BOM probe, in file/decoding contexts), and a
    settings-id range bound (`0xef5dec`, siblings 0xcf/0xdb/0xe0).
- Therefore: a reply sourced 0xEF would match no recovered host receiver.
  The BMC-side answer to 0xEF is not consumed by any host code path this
  study could find — consistent with the settings traffic being fire-and-
  forget at the application layer. **Inferred:** whatever answers 0xEF on
  the BMC side never needs to report back through `mi078` for the settings
  the captures exercised.

## What the captures add on the read side

Reconstructing every `read` in the four traces: the slider trace read 9
kind-9 status frames (source 0xE1, destination 0x60, selector 9, 112-byte
payload), the Local Switch trace 448 kind-9 plus 12 kind-3 (source 0x02,
destination 0x61) and 10 kind-6 (source 0x02, destination 0x60) frames, the
at-rest traces no reads at all. **No capture ever read a frame sourced 0xEF
or 0xE2** (byte-1 sets: {0xE1}, {0x02, 0xE1} across the traces). This bounds
the question: the responder to 0xEF (BMC side) is invisible on this link's
read direction for these operations.

## What is established and what is not

Established (static, verified): the 46 route sites and their functions; the
two parameter senders and their exact frame bytes; the selector-0x0E
service sender at `0xc170a0`; the complete `cmp` census and the fact that no
site tests 0xEF; the three reply handlers' source checks against 0xE1; the
capture counts including the interleaved companion pairing.

Not established: which BMC or CORE service *answers* 0xEF on the wire (the
peer side remains the missing edge documented in
[host-core1-bridge-followup](host-core1-bridge-followup.md) section 4); what
the BMC does with kind-7 selector-0x0E/0x01 blocks (the parameter 0x07 in
block 0x0E binding is still open); whether a 0xEF-sourced reply would be
dropped silently or hit one of the unrecovered routes (bounded: no *recovered
* receiver, but the input worker's kind dispatch has paths beyond the ones
traced in runs 2–3); the meaning of kind-8 companion bytes 2..5.

## Reproduce

```sh
python3 tools/host_ef_study.py local/mi078            # static census (JSON)
python3 tools/host_ef_study.py local/mi078 \
    --captures local/fantom-unit-2026-11-12/link-and-panel-captures
BMC_CORPUS_DIR=<main>/local python -m unittest discover -s tests \
    -p test_host_ef_study.py -v
```
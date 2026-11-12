# Roland BMC research handoff

Prepared 2026-11-11 for a fresh agent after Jacob requested a low-token stopping
point. The full objective remains incomplete: offline BMC ISA/emulation/custom
engine tooling for Fantom-07, firmware-supported unknowns, and documented hardware
requirements. Jacob plans to obtain a Fantom-07, not a Jupiter-X.

## Verified checkpoint

Research commit: `179ebee6f389cc864922db25f956dbaf20137f5b`, pushed and checked
against the remote `main`. The later handoff commit changes documentation only.
Repository: `https://github.com/oscairn/RolandRevEng`, public, MIT.

- [Mapping status](bmc-mapping-status.md): 19 exact DSP sequence profiles, not a
  complete ISA, general compiler or cycle/bit-accurate emulator.
- [FDRV arithmetic](fdrv-cubic-waveshaping-study.md): 11 composed fragments,
  1,692 bytes, 104 packets, native-policy stereo/ring/cache replay.
- [OSC bias/fold](osc-bias-wrap-study.md): latest admitted profile, 52 bytes,
  checked through 8,460 native cutpoints and four Fantom placements.
- [Negative-bias study](negative-short-add-study.md): six native arithmetic
  chains, 8,430 cutpoints, 13 matching Fantom neighborhoods and four uses under
  unresolved header `5e09`. Each effect has two matching native adds; neither is
  uniquely assigned to short `5d52`. No profile added.
- Latest focused verification: 23 tests pass; four pure tests pass without the
  corpus, four skip. Detailed results: `local/negative-short-add/test-focused.txt`
  and `report-native.json`. No physical instrument was accessed or flashed.

## Next work, in order

1. Prove the mixed-packet operation families and source/port dependencies around
   `5d52`: earlier `1c90`/`0d90`, `ded4`, `9450`, `d550`/`d554`, the clipped
   inputs and all coissued effects. Matching numeric defaults alone is insufficient.
2. If that proof supports a complete sequence, add a strict assembly/disassembly
   profile and packet interpreter support. Check original native cutpoints,
   asymmetric/negative inputs, old-value stores, relocations and the full memory
   write set. Otherwise retain the concrete ambiguity; never manufacture an
   opcode from a passing curve or header-rank fit.
3. Continue the [host receiver](fantom-host-receiver-study.md) leads: queued
   kind2 SysEx emitter/route08, route0a consumers, missing host/CORE0 peer,
   host-to-CORE1 translation and physical effect-slot ownership.
4. Recover a source-bound engine entry/return and loading contract, owner-correct
   state allocation and scheduling. Separate offline facts from hardware tests.
   Precision/saturation, latency, interrupt timing, physical routing and recovery
   still need hardware evidence. Existing fragments are not loadable Fantom plugins.

## New lead from the handoff pass: hypothesis only

No production decoder or arithmetic implementation changed in this pass.
`local/mixed-bias-layout/controls.json` inventories the selected controls in the
desktop primary render programs. `handoff-lead.json` records this candidate rule:

```python
from itertools import combinations_with_replacement
choices = [s for s in combinations_with_replacement(range(5), 4)
           if sum(t < 2 for t in s) <= 2
           or (sum(t < 2 for t in s) == 3 and s[-1] == 2)]
# Hypothesis: choices[(header >> 8) - 0x40]
```

It produces 57 entries and matches all six already recorded four-operation
anchors: `47=0044`, `4e=0144`, `58=0444`, `5f=1144`, `69=1444`, `78=4444`.
It predicts `4b=0124`, `5a=1122`, `5c=1124`, `62=1224`. This suggests that
`1c90` in the `5a` packet could be miscellaneous, rather than an ordinary short
add. The rule is fitted to known anchors; it has **not** been validated across
the corpus or independently proved. Do not extrapolate it to `b1` or expand
`header_study.families()` from this fit alone.

A useful trap for the next pass: the proposed `62=1224` interpretation would put
GASSDLY's indexed-looking `6fe4` in a short arithmetic slot. Its ordinary low-six
reference would select three bytes at relative `23c`, value
`1.4139995574951172`. Native load `2fa1c4` reads object+`b8`, default `1.414`,
but its actual constructor representative points to **`22b`**, not `23c`.
`check_constructor_literal()` therefore correctly rejects a direct binding to
`23c`. The earlier packet also contains this value; a shared representative is
possible, but its ownership/update group must be proved. Do not erase this failed
check or claim that similar values establish an operand binding.

Independent leads from the control inventory: standalone `9450` is already
classified family2 in VMCP and SUST; `d550` appears in known family2 contexts in
COMP/MS_COMP/PHONO. `1e50` and `5f50` each also occur in miscellaneous contexts,
so word-only interpretation remains unsafe. Native temporary register numbers
are not DSP port numbers, and an intermediate need not be stored to memory to
represent a functional port value.

## Local environment and continuation commands

Project: `/Users/jacob/Projects/Open Synth Platform/bmc-research`.
Use `/Users/jacob/.pyenv/versions/3.13.7/bin/python` and
`PYTHONPATH=local/fantom-python:tools:tests`.

```sh
git status --short
git log -3 --oneline
PYTHONPATH=local/fantom-python:tools:tests python3.13 -m unittest test_negative_short_add_study test_short_add_context_study test_header_study test_osc_bias_wrap -v
PYTHONPATH=local/fantom-python:tools python3.13 tools/negative_short_add_study.py --core1 local/b0c1a.bin --execute-native
```

The native test requires macOS ARM64 and private executable-memory permission;
use subprocess fixtures so failures cannot terminate the agent. Image identities
and operand contexts must be checked before executing original slices. Reuse
`limit_control_study.native_context`, `weighted_mix_study` binding checks,
`condition_return_study.preserved` and `native_callback_fixture`.

Pinned desktop `local/zen_arm64` SHA-256:
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Pinned Fantom `local/b0c1a.bin` stripped payload SHA-256:
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
Vendor artifacts, raw disassembly and worker output stay in ignored `local/`.

Jacob authorizes Qwen through the existing Mac Studio OMP setup to save tokens;
independently verify every result. Reuse the bounded no-tools runner at
`local/negative-short-add/run-qwen.py` with a new scratch output directory and
the existing `local/omp-qwen.lock`. Its last opcode review was rejected for
confusing native temporaries with DSP ports. All subprocesses launched in this
handoff pass have exited; do not assume old workers are alive from state files.

Code belongs in the project. Obsidian receives Markdown only under
`/Users/jacob/Documents/ObsidianVault/Projects/Oscairn/Roland`. The current note
manifest is located by `local/obsidian-location.json`; preserve user edits with
expected-hash guards, backups and atomic writes. Git pushes are normal, non-force,
to the existing origin; verify `git ls-remote` directly afterward.

Before any question/input/approval prompt run
`/Users/jacob/.codex/bin/prompt-ding`. It currently fails with
`AudioQueueStart(-66680)`; report the failure. REA was unavailable in the earlier
work; existing Capstone/native/Unicorn fallbacks are reproducible evidence, not
REA Evidence records. Do not repeat completed setup diagnostics unnecessarily.

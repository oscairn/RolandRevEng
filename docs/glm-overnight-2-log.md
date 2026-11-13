# glm-overnight-2 run log

## Run 1 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane. Explain the measured conflict
  between the unit's wire captures (every frame `mi078` writes on
  `/dev/ttyGS0` carries source byte 1 `0x00`) and the static record (some
  constructors store `0x60` there), an open question in
  `bmc-addressing-and-loader-open-questions.md`. The queue's section 1 asks for
  host-side dispatch work with actual call/data references, and this item
  cross-checks the 2026-11-12 measurements against host code without touching
  encryption, keys or device access.
- **Files added:** `docs/host-byte1-study.md`, `tools/host_byte1_study.py`,
  `tests/test_host_byte1_study.py`. Detailed census JSON stays in ignored
  `local/host-byte1-summary.json` (main checkout local; the worktree has no
  `local/`).
- **Verified:** with `tools/host_byte1_study.py` against pinned `mi078`
  (SHA-256 `9051…9bb7`): 391 direct route calls to `00be4270`/`00be4418`; 214
  stamp an immediate into message byte 1, 177 leave the base-initializer
  default 0. Routes exercised by the captures leave it 0: 45 of 46 sites to
  0xEF (one 0x60 stamp at `0x8d58b0`), all 11 to 0x75, and the kind-3
  forwarding path at `00c2c9a0` to 0xE1. The 99 stamping 0xE1 sites use
  0x60/0x62/0x63/0x64 and belong to services those captures did not exercise.
  Send path (`00be1120` → `00be2510` → `00be24e8` → `00bdf988`) copies bytes
  unchanged; nothing rewrites byte 1 between queue and `write`. All four saved
  strace traces re-frame with byte 1 `0x00` in every written frame (196, 176,
  1041, 2505 frames).
- **Tests:** `BMC_CORPUS_DIR=<main>/local python -m unittest discover -s tests
  -p test_host_byte1_study.py -v` → 4 passed (34.6 s, pinned image required);
  skips cleanly without the corpus. Existing `test_bmc_ipc.py` (4 tests)
  still passes.
- **Remains unknown:** which subsystems the 0x62-to-0xE1 (76 sites, e.g.
  `0xa573a8`) and 0x60-to-0x0E/0x61 stamps belong to; the CORE1 peer's handling
  of byte 1; whether any stamping site's frames appear under other UI actions
  (captures did not exercise them). The scanner models straight-line blocks
  only; byte-1 stores inside helper routines then routing are counted as
  no-store.
- **Best next item for run 2:** the queue's next section-1 item after dispatch
  mapping: identify where the measured destinations 0xE1/0xEF/0x75 are answered
  on the BMC side — specifically which CORE1 (or CORE0) service receives
  frames routed to 0xEF, using `core1-service-startup-mmio.md` and the
  receiver constructors, or, if that stalls, the section-3 item tracing which
  context owns `2016..2019` routing writes against the measured audio-link
  note. Do not take instruction-semantics items (another series works section
  2).
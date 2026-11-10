# Evidence boundaries

The repository contains research conclusions, aggregate verification results, artifact
hashes and recovered interface addresses. It excludes Roland firmware/plugin binaries,
raw DSP program images, extracted coefficient tables, native disassembly and boot-ROM
dumps. Those stay local even when the remote repository is private.

`summary.json` is the aggregate result from the offline corpus checks. The CORE0 header
and bmc0 CORE1 API JSON files contain metadata and addresses, not decryption keys or ROM
contents. Addresses apply only to the identified build.

Run `python3 tools/analyze.py` with the user's local artifacts to regenerate the full
`analysis.json` and `coefficient_widths.json`. These detailed outputs are ignored by Git.
Additional studies write their detailed output under ignored `local/`.

The coefficient counts retain the earlier adjacent-symbol search for reproducibility.
Those are candidate associations, not proof that a symbol belongs to its proposed
program. The expanded operand study exposes one foreign-table conflict; both the
record-level output and aggregate JSON now state this limitation explicitly.

# Fantom-07 CORE0 key recovery and validated decryption

2026-11-12 local date. **B6 ROM table material recovered from Jacob's Fantom-07
successfully decrypts both v1.08 BMC CORE0 payloads.** Each complete plaintext
CRC32 exactly matches its update header. This note contains no key bytes.

## Hardware observations

The [bounded diagnostic](fantom-core1-bounded-rom-reader.md) was installed and
queried over external USB MIDI. Every request produced two consistent replies,
as in the preceding marker trial; the duplication's cause remains unknown.

1. The constant marker returned through the new ITCM reader body.
2. Channel7 snapshot: global `80000000`; A/B/source/destination all zero;
   CPUID `410fc241` (Cortex-M4); CCR `00000200` (data cache disabled).
3. The one-word DMA self-test returned its exact pattern with successful guards.
4. The two ROM words at `01200000` were `01060000,012000d1`.
5. Six words at `012034c0` returned successfully through channel7. The client
   saved the raw 24-byte entry in a new mode-0600 file after checking replies.
6. A final snapshot showed channel7 A/B/source/destination zero again, with
   global control unchanged. USB MIDI remained responsive.

This establishes the tested path and small ROM windows, without a full ROM
dump. It does not establish a cross-core ownership lock or arbitrary memory
access. No modified CORE0 image was flashed. Initial Ethernet SSH attempts timed
out because the adapter was unplugged. After Jacob reconnected it, root SSH
authenticated with the same pinned host key, the service was active, mi078 was
running and the application/startup/Dropbear hashes were unchanged. The saved
installer log confirmed `ROM DIAGNOSTIC bmc0 CORE1` CHECK OK.

## Validation

Reverse each of the raw entry's three eight-byte groups for the 3DES key.
Reverse each eight-byte ciphertext block before 3DES-ECB decryption and reverse
each output block afterward. This agrees with the packing convention in the
pinned [MC-101 reference decryptor](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/tools/decrypt_c0a.py).
The local implementation uses direct block reversals and never prints material
or puts it on the command line.

| Payload | Plaintext bytes | Header and computed CRC32 | Plaintext SHA256 |
|---|---:|---|---|
| bmc0 MI078 C0A | 1,527,472 | `c1ae85c5` | `2233c991b1e70eccd1156ec0f48df843e1b96fbca92de3b8a2099dda3a982420` |
| bmc1 MI078 C0A | 1,503,344 | `46096a9f` | `b8fc33839488715590e69465eb437b3fe8e91e752817e9a029c0d036e64120ed` |

Both start with word `680148ae`, the expected startup instructions, and contain
the ARMCC scatter-loader signature at payload offset `3e8`. The two full CRC
matches are stronger validation than a plausible instruction prefix alone.
The same material works on both Fantom images; other products are untested.

## Local files and reproduction

Files are under ignored `local/fantom-live-recovery/`:

* `fantom-bmc0-b6-entry.bin`: raw 24-byte entry, mode0600. Do not commit.
* `fantom-bmc0-b6-entry.bin.json`: status/hash report without entry bytes.
* `bmc0_MI078_C0A.decrypted.bin`, `bmc1_MI078_C0A.decrypted.bin`: validated
  plaintext payloads, mode0600. These are analysis artifacts, not update files.
* `core0-decryption-first-check.json`: input/output identities and CRC results.
* `rom-reader-marker-live-01.json`, `rom-reader-dma7-live-01.json`,
  `rom-reader-selftest-live-01.json`, `rom-reader-vectors-live-01.json`,
  `rom-reader-dma7-after-reads.json`: staged hardware observations.

The corrected `tools/fantom_c0a_decrypt.py` accepts a local entry file, rejects
incomplete blocks and unsupported crypto forms, and requires the plaintext CRC
before creating output. It never overwrites existing files. For an original
extracted C0A member, from the repo:

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python3 tools/fantom_c0a_decrypt.py \
  --input local/bmc0_MI078_C0A_up.bin \
  --key-file local/fantom-live-recovery/fantom-bmc0-b6-entry.bin \
  --output local/fantom-live-recovery/bmc0-core0-analysis.bin
```

Use a new output name. The supported crypto control is `b6020001`; other slots
or modes are not guessed. Four tests passed: synthetic packing/round-trip,
wrong material/corruption/truncation/mode rejection, CRC-before-write and
overwrite protection, and both actual Fantom hashes/startup/scatter signatures.
The previous draft's first-word-only validation and hex command-line argument
were replaced; its original contents are backed up locally.

Both previously opaque CORE0 programs are now available for offline analysis.
The next scope is the CORE0 side of the USB/MIDI–CORE1 bridge and loader lifecycle,
including duplicate replies and engine setup. Full DSP ISA coverage, complete
BMC emulation and safe arbitrary engine replacement remain separate tasks.
Raw material and decrypted vendor binaries have not been published.

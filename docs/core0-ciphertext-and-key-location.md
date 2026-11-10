# CORE0 ciphertext comparison and the reported ROM key location

2026-11-10. Offline follow-up to Jacob's request to find a CORE0 key, its location
or another route into the Fantom. No key bytes were recovered by this comparison.
No encrypted image was decrypted and no target memory or device was accessed.

## A concrete reported location, with a product boundary

The pinned [MC-101 decryptor](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/tools/decrypt_c0a.py)
reads a separate on-chip boot-ROM dump. It uses table base `012023b0`, 24 bytes
per entry, and index `b6` from the update header. The resulting entry is
**`012034c0..012034d7`**. Its code derives the 3DES key from six little-endian
words with the documented hardware packing; no literal master key is embedded
in that script. The referenced ROM file is absent from the retained checkout.

This is an author-reported **MC-101 BMC/ESC2** key-table location. It is a useful
Fantom candidate, not a verified Fantom silicon map or key identity. These are
BMC addresses, not i.MX8M `/dev/mem` addresses, external flash offsets or offsets
inside a C0A update. The byte range cannot be read through the already studied
CORE1 MMIO window merely because both use numeric addresses.

The [MC-101 ROM report](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/docs/boot_rom_analysis.md)
places that mask ROM at `01200000`, size `4000`, and identifies its image by
SHA-256 `742b1dd61d07509d8c72a1c7bcf3a44b9707e72d31543e3256415eb4307e60d5`.
No such ROM file was found in the retained project artifacts. External NOR
contents are a different artifact from the on-chip mask ROM.

## The six CORE0 images share substantial ciphertext

All six inspected `App1_Main` containers have crypto control `b6020001`.
Header agreement alone is weak evidence for shared key material, so the new
checker compares actual aligned eight-byte payload blocks as well. It starts
at the validated **`60`** payload offset, stops at the declared payload length,
deduplicates blocks and excludes all-zero/all-FF blocks. Headers and trailers
do not enter these counts.

| Image | Declared payload bytes, decimal | Distinct nontrivial blocks | Distinct blocks shared with Fantom bmc0 |
|---|---:|---:|---:|
| Fantom bmc0 | 1,527,472 | 148,654 | 148,654 (self) |
| Fantom bmc1 | 1,503,344 | 144,562 | 14,335 |
| MC-101 v1.82 | 3,499,440 | 299,952 | 10,597 |
| JUPITER-X v3.03 | 8,176,656 | 343,931 | 15,985 |
| SH-4d v2.00 | 8,781,760 | 410,613 | 14,858 |
| TR-8S v3.00 | 2,535,360 | 224,919 | 8,124 |

Input SHA-256 values are pinned in `tools/core0_ciphertext_study.py`; official
download provenance is in the preceding MC-101, JUPITER-X and SH-4d/TR-8S studies.
The MC-101 C0A component extracted from the retained official tar is
`ebdb8d987232a31972c881065254419187d586d73bb1c808e681b5dd278d8cf6`.

**Inference:** these exact overlaps support a shared encryption transformation
more strongly than the common index alone. Under the reported deterministic ECB
layout, a recovered MC-101 key is worth testing against Fantom. The overlaps
are not a recovered key, a proof of identical ROM revisions, or a substitute for
actually decrypting and validating a Fantom image. Block similarity does not
justify blind key guesses or treating readable constants as key bytes.

The old 14,351-block Fantom estimate is not reused: the corrected bounded
comparison produces 14,335 distinct nontrivial shared blocks under the rules above.

## What would establish a usable key

The missing artifact is actual key material or the applicable boot-ROM bytes,
obtained through an established BMC-side access path. A candidate should first
be checked with the reported block/word packing against a known image, then
validated on Fantom using multiple independent plaintext structures and any
confirmed checksum/integrity rules. A single plausible Thumb instruction or
matching four-byte prefix is insufficient. Runtime `.data` may differ from
pristine decrypted update data, so a live RAM dump is not automatically a
flashable reconstruction.

Reading already decrypted CORE0 runtime code could also answer the external-peer
question without obtaining the master key first. That still requires an actual
BMC memory-access route and correct map; the existing CORE-local MMIO service
does not establish such a route into `60000000` or `01200000`.

The on-chip ROM, the two BMC firmware domains, i.MX Linux recovery encryption,
wave/content encryption and signing/public keys are separate questions. A Linux
`update_fntm0` passphrase would not automatically decrypt a BMC C0A image.
The retained stock script container (SHA-256
`ef69453ca9dfa7af7cff043e43bcbc5598fc07fe4e445e55e13e03d812103013`)
has a v4 symmetric OpenPGP packet declaring AES-256, salted/iterated SHA-1 S2K,
salt `145955decdd1e5b6` and encoded count **`ff`** (65,011,712 input bytes),
followed by tag 18. This was checked directly without decryption. The old `c8`
count-byte wording was incorrect; the S2K count is not independent hash rounds.
These metadata do not reveal the plaintext, consumer, passphrase or install policy.
See the [embedded material scan](embedded-rom-key-material-scan.md) and
[readable provider-reference study](core0-rom-provider-reference-study.md) for
their bounded negative results. Other ROM revisions, transformed constants and
unrecognized compression remain unresolved.
The [access-route audit](fantom-access-route-audit.md) records the stock factory
shell endpoint and the unresolved gates on console, USB and source-backed boot leads.

## Reproduce

```sh
python3 tools/core0_ciphertext_study.py
python3 -m unittest discover -s tests -p test_core0_ciphertext_study.py -v
```

The report contains aggregate counts, artifact identities and reported-address
arithmetic only. It writes an ignored local JSON report and neither derives nor
prints key bytes. Three tests cover exact payload/trailer boundaries, block
deduplication and exclusions, invalid metadata/index rejection, all six actual
containers and explicit refusal to claim key recovery or Fantom ROM validation.
Two tests run without vendor files. Crypto libraries are installed locally, but
their availability is not evidence that a key was found.

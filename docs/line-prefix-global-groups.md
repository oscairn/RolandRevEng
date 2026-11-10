# Static prefix-group inventory across the paired images

2026-11-10. No matching count-2-or-more static descriptor was found containing
both prefix byte offsets `14/17` or `24/27` in the inventory below. There is
therefore no positive group candidate from this scan to trace to LINE or a generic
MFX input-mode parent. **This is not proof that the fields are never written,
fixed constants or unrelated.** Runtime-built descriptors and independent writes
remain open.

This follows the [checked LINE parameter study](line-prefix-parameter-study.md),
which recovered actual counted writes and positive rational groups. No new opcode,
alias, timing or interpreter admission is made here. No target/device execution,
download, firmware change or model-only interpretation was used.

## Reproducible search boundary

`prefix_group_inventory.py` scans the complete file-backed bytes of two pinned
images, using their observed ABI pointer alignment and descriptor pointer/count
positions:

| Image | Pointer alignment / width | Array pointer / count byte | Descriptor-shaped candidates | Prefix-pair matches |
|---|---|---|---:|---:|
| Prepared ZENOLOGY arm64 | 8 / 8 bytes | `+10 / +18` | 665 | 0 |
| Fantom bmc0 CORE1 | 4 / 4 bytes | `+8 / +c` | 616 | 0 |

Offsets are hexadecimal. The artifact digests remain:

* Native: `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
* CORE1 payload: `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.

The count is the actual unsigned byte, covering every value **2 through 255**,
not only the earlier narrow parser's count limit. Each array must be aligned to
four bytes and entirely backed by a contiguous source range. CORE1 pointers are
mapped through the checked ITCM/ERAM reader; arrays cannot be manufactured by
joining an unmapped address gap. Every declared record must have the observed
literal-width byte 2, 3 or 4 at record+8 and the established 12-byte stride.

The scan tests pair membership across the **whole declared array**, including
nonadjacent members and unrelated intervening fields. Other metadata bits are
retained without assigning them a meaning. Matching candidates outside the prior
LP64 parser's narrower admission would remain visible as unverified candidates;
they are not silently dropped. No absolute/relative address equality or LINE
ownership is inferred from a table shape.

The word between the initial descriptor field and its array pointer was not used
as a type filter. It happens to be 1 for all qualifying candidates in both images.
These totals describe structural candidates only; they are not counts of executable
operations, verified parameter callers or ISA coverage.

## Positive and negative controls

Both native rational count-4 groups from the preceding study occur in the scanned
inventory and are independently accepted by its checked descriptor parser:

| Symbol | Declared relative fields | Count |
|---|---|---:|
| `a16df8` | `ec,f0,118,11c` | 4 |
| `a16e18` | `e6,e9,112,115` | 4 |

The artifact-free test constructs a count-3 descriptor containing `14`, an unrelated
field and `17`. It is found despite nonadjacency. Reducing the count to 1 or 2
removes the match, so the reader cannot look past the declared extent and infer a
group from adjacent storage. Tests also check truncated arrays, a large count,
unaligned pointers, invalid width metadata and discontinuous ARM address mapping.
Metadata outside the narrow LP64 parser's supported segment form remains reported
as an unverified matching candidate rather than becoming an admission or a hidden
negative.

All three inventory tests passed, including the actual-image scan. The separate
literal-call tracer regression also passes after rejecting intervening native
branches/returns; the original three LINE literal callsites are unchanged.

## What remains unresolved

There is no matching **static descriptor candidate in this defined inventory** to
which a LINE/generic-parent ownership edge can now be attached. The earlier
count-1 records do not become count-2 groups, and another class's records cannot
be applied to LINE based on matching offsets.

Excluded possibilities include runtime-built/patched descriptors, multiple
independent count-1 writes with the same requested value, packed/other layouts,
encoded pointers, other width forms, unbacked runtime data and other builds. A source/generator
fixed-constant rule or an external write path could still explain the duplicate
defaults. The negative result alone establishes none of those explanations and
does not close the outgoing port-state/store-timing gap.

```sh
python tools/prefix_group_inventory.py local/zen_arm64 local/b0c1a.bin > local/prefix-group-inventory.json
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests -p test_prefix_group_inventory.py -v
```

Original inputs are unchanged. Detailed candidate metadata remains ignored/local;
the repository contains only the read-only selector, tests and derived findings.

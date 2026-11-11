# State initialization through stock float writers

2026-11-10. Offline Capstone analysis joins the native sample ring to **memory
enum 0** and recovers the Fantom per-DSP writer for that enum. The CPU supplies
binary32 through the stock typed aperture. A custom raw BMC number codec is
therefore not a prerequisite for preparing this candidate initialization path.
The hardware conversion, active-owner allocation, addressing cadence and safe
call context remain unverified. No device writes or firmware execution occurred.

`tools/data_seed_interface_study.py` pins both artifacts and checks the actual
instruction, vtable, dispatch and aperture-table anchors:

- Fantom BMC0 CORE1 payload: `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
- ZENOLOGY arm64: `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.

## Native ring identity

Named `CSimDspMgr::WriteDspMemoryFloat` at `fbfcc` resolves the symbol and
calls core vtable slot `40`, then stores a double at the returned pointer
(`fc060..074`). `CSimDSP4_Core` installs address point `a14e60` in its
constructor (`16bb8c..094`); slot `40` points to `GetMemoryAdrs` at `16c3ec`.
Its byte dispatch table at `7ae3fb` sends enum 0 to `16c418` and enum 1 to
`16c434`. Both return a double element at `(logical_index-origin)&7ff`.
Enum 0 selects core+`10`; enum 1 selects core+`18`.

Core+`10` is the exact ring pointer path used by the
[native state study](line-state-and-history-study.md) and the explicit callback
fixtures: wrapper+8 → manager+18 → core+10 → ring+18. This identifies the
native storage enum; it does not identify a physical IDM/EDM bank or prove that
Fantom hardware advances its origin on the same schedule.

The native writer takes a double; the firmware writer below takes a float.
Do not transfer CPU ABIs or native binary64 storage bytes between them. The
native write body also does not retain its supplied integer offset, whereas
the firmware explicitly adds that offset. Use the recovered firmware behavior
when designing a future hardware caller, rather than assuming complete parity.

## Firmware per-DSP typed writer

Manager slot `84` at vtable `6117647c` selects Thumb pointer `01132e69`.
The body at `01132e68` is assertion-named
`CBmcDspMgr::WriteDspMemoryFloat(const _DataSym*,int,float)`:

| Input | Manager ABI | Driver ABI at `011300ac` |
|---|---|---|
| Owner | r0 = actual manager object | r0 = descriptor DSP index |
| Memory | r1 = actual `_DataSym` | r1 = symbol kind byte `+10` |
| Position | r2 = signed extra element offset | r2 = resolved index plus offset |
| Value | s0 = binary32 | s0 = binary32 |

`ParseDspMemoryWordAdrs` at `01131968` resolves enum 0 through descriptor+`20`.
When that reservation group exists, it checks the symbol segment, relative
index and relocation flag, then adds the selected reservation base. As in
the earlier resource study, the later **extra offset is not bounded against
the selected owner's length**. Driver capacity checks protect the whole bank,
not ownership within it. Absolute/no-group forms do not allocate resources.

The driver looks up base table `0113aac0` and capacity table `0113aaf0`,
requires a nonzero aperture and index strictly less than capacity, then issues
`VSTR s0` at `base+4*index` (`011300f2..fa`). It checks signed DSP<7 and unsigned
kind<12; no explicit negative-DSP guard appears. A future caller must validate
DSP 0..6 itself. There is no completion wait, readback or owner locking in this
short successful body.

| DSP | Enum-0 float aperture | Enum-1 float aperture | Elements per bank |
|---:|---|---|---:|
| 0 | `41400000` | `41410000` | 2048 |
| 1 | `41500000` | `41510000` | 2048 |
| 2 | `41600000` | `41610000` | 2048 |
| 3 | `41700000` | `41710000` | 2048 |
| 4 | `41800000` | `41810000` | 2048 |
| 5 | `41900000` | `41910000` | 2048 |
| 6/MDSP | `41200000` | `41210000` | 2048 |

The corresponding fixed and raw write apertures are float base+`2000` and
base+`4000`, using their separate capacity tables. This does not establish a
float-to-fixed relationship or raw stored representation.

**Readback limitation:** all three per-DSP readers explicitly reject enums
0 and 1 before their ordinary table accesses. The branch sites are `011302a8`
(float), `01130388` (fixed) and `0113041c` (raw). A nonzero raw aperture-table
entry is therefore not proof that the stock raw reader supports this ring.
Do not bypass the check or substitute a guessed read service.

## Separate global IDM/EDM portal

The [named-domain study](memory-domain-labels-and-clear-count-boundary.md)
describes a different interface. Its float driver `01130892` accepts
`r0=Boolean bank, r1=start, r2=count, r3=float32 input array`. Zero count
returns before peripheral access. For each element it checks `41100034`
bit31, optionally calls the existing timer wait with count 0/completion 1,
writes `start+i` to selector `41100040` or `41100050`, and transfers source
`+4*i` through `41158000` or `41158010`. Fixed/raw variants use +4/+8.

Manager slots `f4/f8/fc` are thin write adapters; `100/104/108` are readers.
The adapter's CPU array pointer arrives on the incoming stack and is reloaded
from `[sp+8]` after its two-register push. These calls drop the manager pointer
but do not translate an owner-relative `_DataSym` themselves.

This portal provides another binary32 CPU interface, but **no checked join
maps its Boolean/start address to the enum-0 per-DSP ring**. The native global
float endpoints are stubs. The existing CORE-local MMIO handler also does not
supply that mapping, ownership, safe serialization or a verified host ingress.
It is not an established loader path for the oscillator.

## Applying this to the original oscillator

The [120-byte oscillator](original-bmc-allpass-oscillator.md) publishes six
logical seeds and two coefficients. `float_sources(initial_data)` reports
each requested seed, its rounded CPU binary32 value, little-endian CPU bytes
and rounding error. It accepts finite values and logical indices 0..2047;
it rejects binary32 overflow and preserves signed zero. Those bytes are a
**CPU source buffer description**, not raw DSP RAM bytes or device commands.

Keeping every later operation under the existing native-policy packet model,
changing only the six initial values to binary32 produced these differences
from binary64 seeding over 12,000 frames at amplitude .25:

| Requested pitch | Maximum output difference | RMS difference |
|---:|---:|---:|
| 440 Hz | `6.7324744390528934e-9` | `3.6677457684238167e-9` |
| 9600 Hz | `5.929301521989672e-9` | `3.9732528227014456e-9` |

This is a source-rounding experiment, not a BMC conversion or stability test.
The checked regression runs both cases through ring wrap and confirms only
five initial sine calls. The normal oscillator retains its original binary64
reference seeds and its existing explicit limitations.

Next hardware-facing requirements are an actually owned enum-0 reservation,
initialization while that owner is quiescent, observed address/origin behavior,
a verified readback path, entry/return framing and output routing. The typed
writer narrows the initialization problem; it does not make the engine load-ready.

The [Fantom voice resource plans](fantom-voice-resource-plans.md) now bind six
seed values and six coefficient sources to each recorded owner layout. A
read-before-write analysis and nonseed canaries establish that the functional
model needs only those six initial data cells. This supplies no live-write
window, whole-bank-clear permission or hidden-hardware-state initialization.

## Reproduce and Qwen review

```sh
python3 tools/data_seed_interface_study.py local/b0c1a.bin local/zen_arm64
python3 -m unittest discover -s tests -p test_data_seed_interface_study.py -v
```

Use the existing Capstone-capable interpreter. Four tests cover explicit CPU
rounding, invalid sources, two packet-oscillator rounding experiments, and the
pinned enum/ring/aperture/read-rejection evidence. Artifacts stay ignored/local.

Qwen returned a bounded portal review in 92 seconds. Independent review accepted
its main ABI/stride/float-transfer findings. It incorrectly associated the float
writer's timer object with another literal, treated a zero word as a proven
vtable terminator, and claimed no direct calls despite the visible adapter
branches. Those details were rejected. The enum-0 native/per-DSP join and the
checker above were independently derived and tested locally.

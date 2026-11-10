# CORE1 outbound words, shared rings and backpressure

2026-11-10. Read-only static follow-up to [task context](core1-task-context-and-host-peer.md)
and [service reply construction](core1-service-startup-mmio.md). Input is Fantom
bmc0 header-stripped CORE1, SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
Addresses are its CORE1 runtime addresses; numbers in code formatting are hex.
No target code, plugin, updater, device or exploit was executed. These are file/
Capstone observations, not runtime observations or REA Evidence.

The new result closes a **CORE1-local outbound edge**: the MMIO reply builder
feeds type-3 packet words into a software queue and TXDT, then a 64-word shared
ring. It does not close the external peer or Linux frame conversion. The shared
ring's nominal free count includes its reserved slot, and the caller can spin
when it fills. Neither queue acceptance nor a signal is a DSP/remote acknowledgement.

## Two directions in one shared region

The scatter record at `6123fca8` copies 56 header bytes from `0113cf08` to
`e0043000`; all fourteen initial words are zero. Another record zero-fills
`e0043038..e00433f3`. Actual reader/writer bodies independently select:

| Role in CORE1 | Word array | Write index | Read index | Other observed fields relative to `e0043000` |
|---|---|---|---|---|
| Incoming, reader `01125f68` | `e0043038`, 64 words | `+0c` | `+10` | `+14/+18/+1c` statistic accessors |
| Outgoing, writer `01125eac` | `e0043138`, 64 words | `+24` | `+28` | `+2c` peak occupancy, `+30` failed attempts, `+34` successful enqueues |

Startup calls `01125ffc` and `0112600e` at `01102a1e/22`, resetting their indices
and setting `+20/+08` respectively to 1. This is a compiled initialization path,
not a snapshot of a ready peer. The other producer/consumer and its memory map
are still outside this trace; these addresses alone do not identify CORE0 or i.MX.

Outgoing enqueue computes `(write+1)&63` and rejects equality with read. Thus
**63**, not 64, words can be pending. A failed attempt increments `+30`, returns
zero and does not store the word. Success stores at the old write position,
publishes the new write index, increments `+34`, updates peak occupancy and issues
`SEV` before returning one. The failure statistic counts attempts, not necessarily
lost messages: one pending word can generate many failures before succeeding.
`SEV` is not an observed peer acknowledgement or proof of peer scheduling.

`01125f3e` returns **64 minus occupancy**, so it returns 1 when enqueue is already
blocked by the sentinel slot. Treating that return as available payload capacity
would overstate capacity by one. `tools/core1_transmit_study.py::ring_metrics`
separates this reported count from actual admissible slots for quiescent indices.

Incoming dequeue increments/stores read index before loading/copying the selected
word, then masks the index to six bits and stores it again. A live mid-operation
snapshot can therefore expose a transient index 64; the pure metric helper accepts
only quiescent 0..63 inputs. This observation is not a concurrency-correctness
proof or a claim that arbitrary snapshots are coherent. No memory-order or
multi-producer guarantee is inferred from these source-order operations.

## Software output queue and TXDT callback

Single-word entry `0111efb0` disables interrupts, invokes enqueue `0111f4d8`,
signals software task 2 and unconditionally enables interrupts before returning.
It does not preserve an arbitrary incoming PRIMASK. Queue state is `2008203c`,
data `20095f0c`, physical size 512 words, usable size 511. Verified initial-data
expansion gives its six metadata words `(0,0,512,512,0,0)`. The counters' nominal
512 is not proof of 512 simultaneously admissible words.

On full, `0111f50c..51c` calls the logger, increments the failure field and
returns without storing the new word if the logger returns. Signalling task 2
does not undo that rejection. No universal lossless contract is established.
The multiword packetizer below uses this same enqueue without checking a success
return; arbitrary bursts are not proved safe merely because an outer call returns.

Startup `0110334e` calls registrar wrapper `0111ef96`. It binds task 2 / TXDT to
Thumb callback `0111ee69`, priority argument decimal 18. The existing registrar
maps task 2 to **NVIC IRQ230**, vector `011003d8`, handler `0110213c`, callback
slot `20084960`, priority byte `90`. This is a software interrupt callback, not an
OS thread. Actual preemption also depends on grouping, implemented bits and masks.

The callback dequeues through `0111f51e`. Several outgoing kinds consult the
byte-returning gate `01101a06`; a false result takes the next-dequeue path without
offering that word to the shared ring. The tested byte is at `20080094`; startup
and runtime conditions for enabling this policy are not recovered here.

Four full-ring retry loops start at `0111eee6`, `0111ef10`, `0111ef5a` and
`0111ef84`. Each increments a local retry statistic, reloads the pending word,
calls `01125eac`, compares zero and branches back. These exact loops contain
**no sleep, WFE, yield, timeout or cancellation check**. Progress depends on the
other consumer and permitted interrupt behavior. This does not prove permanent
deadlock, starvation or a specific scheduling failure on an instrument.

## Actual service-reply edge and outgoing tags

MMIO reply builder call `6102d42a` reaches far veneer `6107773e`, which loads
Thumb pointer `0111f0bf` and branches through it. Wrapper `0111f0be` supplies
**type 3** to packetizer `0111efc2`, preserving the byte buffer and length.
That packetizer creates first bytes **`34/35/36/37`**: body groups of three bytes,
then final groups of one/two/three bytes. These are not the incoming assembler's
`14/15/16/17` tags and not Linux outer-envelope kinds or destination identifiers.

At `0111f042/48`, a body word is enqueued through `0111f4d8` and task 2 signalled.
The final paths use the same enqueue and schedule. TXDT's type-3 path can also
reassemble/log the payload before attempting the shared-ring write. It retains
the original queued word for that attempt; the local reassembly does not prove
a different word is transmitted. No Linux ttyGS0 reply, peer acknowledgement or
safe MMIO request bound follows from this local edge. The independently documented
MMIO reply-stack discrepancy remains unresolved; no request generator is supplied.

## Reproduce and remaining evidence

```sh
python3 tools/core1_transmit_study.py local/b0c1a.bin > local/core1-transmit-study.json
python3 -m unittest discover -s tests -p test_core1_transmit_study.py -v
```

Use the existing Capstone-capable interpreter. Three tests check all 4,096
quiescent shared-ring index pairs, invalid indices, unsupported-image rejection
and the real callback/queue/reply anchors. The tool emits metadata only and never
opens a device or creates wire commands. It is build-specific, not a general
inter-core ABI emulator; bmc1 equivalence was not asserted in this pass.

An end-to-end loader still needs the actual external producer/consumer, correlated
traffic, proven queue ownership and manager coordination. Success at each enqueue,
serializer completion, peer receipt, clear/DMA completion and DSP execution must
remain separate events in that design.

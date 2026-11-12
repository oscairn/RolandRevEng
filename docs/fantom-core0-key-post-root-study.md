# CORE0 key search after live Linux root access

2026-11-12. **No BMC CORE0 key recovered in this pass.** The Linux updater
passphrase is independently verified in
[the Linux updater study](fantom-linux-updater-decryption.md); it does not decrypt
the BMC App1_Main container. This pass used live read-only inventory and offline
analysis. No BMC command, GPIO change, raw bus/memory probe or firmware write
was performed.

## Newly available artifacts

Artifacts and disassembly remain ignored under `local/fantom-live-recovery/`.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Recovery ext4 payload | 240734208 | `d74ac3b3216540e9cd0c64f15f5a635d9d5f5bcd309096be85e4fce6f2c100c9` |
| Recovery `/home/root/bin/uprecv` | 10432 | `bf94fd2c84d379a417fbd31106394dae6db22f92a1c2c2cd6a2266757cac458d` |
| Installed tickgen.ko | 23152 | `5a2e516f10d113e7f4a2f2b2df2a96364f54e4a4f429f9671d5ea7f687e0c7cb` |
| Boot partition tee.bin | 320696 | `9c2c7753350b42f2b351903daf7f4d85c97cc1651f22457bc43e0773c98c7aa7` |
| Boot partition boot.scr | 601 | `9bda09f95ebda06044a3eef04c098025f4e12222ab3e8cb695b96c1cc6973909` |

The complete raw ext4 payload has no occurrence of the documented MC-101 ROM
vector pair `(01060000,012000d1)` encoded little-endian. uprecv, tickgen.ko and
tee.bin also have no literal occurrences of that pair or `012023b0`, `012034c0`,
`40020400`. Reports: `core0-recovery-rom-scan.json` and
`core0-new-artifact-anchors.json`. This bounded scan does not recognize other ROM
revisions, compressed objects, transformed constants or arbitrary key bytes.

## The recovered updater helper is a status receiver

ARM64 uprecv main is `400df8`. It opens `/dev/ttymxc3` via `400c94`, flags 902,
sets numeric speed 1000000, and reads one byte at `401094`. High-bit bytes update
the status; low-bit bytes supply the accompanying value. Status values map to:

| Status | Display |
|---|---|
| 80 | Insert Memory to External (board2) |
| 81 | Running Update |
| 82 | Update (board2) Error, with value |
| 83 | Update (board2) End, with value |
| 84 | Update (board2) No File |

The sole write call at `400f2c` targets stdout (fd 1). This helper does not send
UART memory-read requests or decrypt the BMC image. It explains the board-2 UI
status transport, not a ROM-access protocol. The helper was never executed here.

## Installed USB receive callback identified

The live loaded out-of-tree tickgen module imports gserial_set_func. Relocations
at module .text `a98/a9c/aa0` establish registration of its `sync_func` (`758`);
exit calls the setter with NULL at `bc0`. sync_func accumulates 12-byte IPC
prefixes and skips length-prefixed variable data. Its clock/status branch
handles F8, F2, FA, FB and FC through registered callbacks.

Its mmap path uses an allocated Linux page, not a BMC ROM mapping. The inspected
init and memory callbacks do not establish a BMC key-read service.

This resolves the earlier missing callback-caller question in the
[GS1 assessment](fantom-live-shell-trial.md). The retained GPL u_serial calls one
global callback without a port check. If that implementation matches the deployed
kernel, GS1 shell bytes would enter the same stateful parser as BMC IPC. Merely
separating ttyGS numbers would not isolate that kernel parser. No GS1 test was run.

## Existing live access and remaining route

The user reported an empty /proc/mtd and no mtd/spidev/uio/rpmsg nodes. Live
inventory exposes UART0..3, I2C0..2 and the custom i2c-slave-2 node. Read-only
GPIO labels identify front-panel keys, LCD/touch, USB VBUS and other board pins;
no labelled BMC ROM/boot-control path was established. Anonymous GPIOs remain
unresolved and were not driven.

The pinned upstream [MC-101 setup](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/README.md)
requires **patching CORE1** before its dumper can read memory. Its
[ROM report](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/docs/boot_rom_analysis.md)
describes extraction through the BMC DMA engine. This is not a stock Fantom
command. Its model-specific hook addresses, spare ITCM/SRAM and DMA-channel
availability must not be assumed on Fantom.

The next concrete route is a Fantom-specific, bounded CORE1 ROM reader, initially
checking vectors then reading only the reported `01200000..01203fff` range.
Its hook/return ABI, output route, scratch ownership, DMA ownership and boot/update
recovery need validation before installation. The existing stock CORE1 MMIO
service is limited to `41100000 + masked_offset`; it cannot directly read that
ROM range. Its known reply-stack discrepancy is not a safe substitute.

If a genuine applicable ROM is obtained, candidate slot B6 is at offset 34c0,
length 24. Derive its key with the documented word packing and validate actual
Fantom plaintext/integrity before claiming compatibility. The two published
MC-101 ROM hashes conflict, as recorded in the earlier key-location study.
No patched BMC image was built or installed in this pass.

## Live UART follow-up after persistent SSH installation

The live driver maps tty index 3 (`/dev/ttymxc3`, Linux UART4) to i.MX MMIO
`30a60000`, IRQ34. fuser reported no owner on UART0, UART2 or UART4; mi078 was
running. The live UART4 device-tree node is enabled. The retained matching board
source assigns RXD/TXD only, with no RTS/CTS declaration. These are Linux-side
facts, not identification of the BMC-side UART register block or boot straps.

A five-second passive UART4 capture used the stock helper's speed, 1000000 baud,
8N1, no hardware/software flow control and no echo. The descriptor was opened
read-only with NOCTTY/NONBLOCK. No data writes, break or monitor commands were
issued. Original termios settings were restored and checked before closing.
The driver counters were tx=0/rx=0 both before and after, and zero bytes arrived.
Ignored evidence: `local/fantom-live-recovery/{passive_uart4.py,uart4-passive-capture.json}`.

The line is therefore idle during the observed normal operation; this does not
prove that it lacks an unprompted or boot-only monitor. The verified stock use is
the update-status protocol described above. The MC-101 ROM report's UART ISP
read commands require hardware-selected mode 10, not ordinary QSPI boot. No
Fantom entry sequence or BMC-side UART identity has been established, so those
opcodes were not sent to the running synth.

The UART could be a return channel for a future dumper once its BMC register/clock
mapping is proven. It is not yet a demonstrated stock ROM-read route. A bounded
CORE1 dump package still requires the model-specific hook, DMA/scratch ownership,
request/output transport and recovery validation listed above. Persistent SSH is
now verified after reboot, removing the repeated Linux bootstrap requirement.

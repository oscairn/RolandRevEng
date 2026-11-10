# Fantom access routes: stock endpoint, source gates and artifact limits

Follow-up: [factory intro/dispatch](factory-gate-and-ui-dispatch-study.md) traces
the actual UI loop and separate test groups. Mode 3 preserves the intro page;
known 0/1/2 transitions leave it. No activation route into mode 3 is established.

2026-11-10. Offline inspection only: no target binaries/scripts executed, device
opened, network scanned, update changed or firmware installed. Addresses below are
ELF virtual addresses in the pinned v1.08 executables. REA providers were unavailable;
ELF parsing, Capstone 5.0.7 and source/archive reads supplied the static evidence.

The strongest new lead is a stock `qctest` call to a login shell on its inherited
terminal. Its activation condition is **not solved**: the handler requires mode 3,
but the identified direct mode-setter callers supply only 0, 1 and 2. This is a
specific endpoint to investigate, not a demonstrated way to obtain a root shell.

## Route assessment

| Route | Established evidence | Missing proof / consequence |
|---|---|---|
| Factory-test terminal | Stock `go.sh` launches `qctest` through `xterm` when GPIO138 reads 1; its main can call `execl("/bin/sh", "sh", "-l", NULL)` | Mode-3 activation, effective UID, usable input/terminal state and actual startup invocation unobserved |
| Linux serial console | Stock DTB chooses UART2/`ttymxc1`, 115200, address `0x30890000` | Installed getty, credentials, exposed pads and electrical levels absent; kernel console is not itself a login service |
| SD boot script | Retained U-Boot source supports `boot.scr` before `Image` on selected MMC device | Autodetection can select the actual boot device; deployed bootloader, saved environment and recovery image missing |
| Fastboot / SPL USB SDP | Retained defconfig enables relevant commands/features | Deployed configuration, physical port, boot entry and authentication/fuses unknown |
| Network shell | DTB enables Ethernet controller; qctest references `/home/root/net.sh` | No installed rootfs, network configuration, SSH/telnet service or `net.sh` implementation available |
| I2C control channel | Custom Roland kernel slave driver and actual `mi078` opener/callback recovered | Four-byte application transport, with no shell dispatcher or physical peer identity established |
| Prepared update shells | Modified archives contain proposed shell commands | Acceptance, execution, root privileges, external USB reachability and safe recovery untested; GS0 conflicts with application IPC |

No JTAG/SWD pad or ROM-boot recipe follows from these artifacts. Board photos,
schematics and matching silicon/security configuration are still required.

## Stock qctest shell endpoint and exact gate

`qctest`'s ELF entry sets the main pointer to `0x402ce8` before calling
`__libc_start_main`. Main creates a worker with entry `0x406150`, then polls global
`0x45a2c8` at `0x402f10..402f38`, sleeping while it is zero. Once nonzero:

| Address | Decoded operation / data |
|---|---|
| `402f3c` | `mov x3, #0` |
| `402f40/44` | `adrp x0, 42d000; add x2, x0, #670` → `"-l"` |
| `402f48/4c` | `adrp x0, 42d000; add x1, x0, #678` → `"sh"` |
| `402f50/54` | `adrp x0, 42d000; add x0, x0, #680` → `"/bin/sh"` |
| `402f58` | `bl 4024e0`; ELF PLT relocation identifies `execl` |
| `402ccc..402cd8` | Materializes `45a2c8`, loads `w1=1`, stores it to that flag |

The flag-setting function is `0x402c94`; its only direct B/BL caller in `.text`
is `0x408014`. It is a cleanup/exit request, not proof that the flag is set at
normal startup. The caller is inside a handler identified through RTTI/vtable as
`CPageDmyVer`:

* Switch dispatch at `407fb0/407fb4` selects code `0x3e`.
* `407fd0..407fe0` reads `0x456edc`, compares it with **3**, and bypasses this
  path when unequal.
* `407fe4..408004` reads the byte at `0x456ed8` and formats
  `/home/root/net.sh %3d` into a buffer using `sprintf`.
* `408010` calls `system` on that buffer **before** `408014` requests the exit
  that enables main's shell call. The behavior of `net.sh` is unknown; its absence
  is established only for the inspected `_DATA_FNTM0` archive, not the installed disk.

The switch-name table at `0x456930` is indexed by decoded switch code in
`0x40534c..40538c` and `0x409d20..409d60`. Slot `+0x3e*8` names
`SW_DRV_ID_ENTER`. `SW_DRV_ID_EXIT` is code **0x37**, not 0x3e. The decoder at
`0x405728..40575c` computes `((message[2] & 7) << 7) | (message[1] & 127)`.

The gate's file-backed initial mode at `0x456edc` is **-1** (`ff ff ff ff`).
The identified setter at `0x40751c` stores its incoming `w1` to that address at
`0x407538`. A complete aligned `.text` scan for direct B/BL to this setter finds:

| Call site | Incoming value instruction | Value |
|---|---|---:|
| `4080d0` | `4080c8: mov w1, #0` | 0 |
| `408104` | `4080fc: mov w1, #1` | 1 |
| `408238` | `408230: mov w1, #2` | 2 |

No direct setter caller assigning 3 was identified. This does not rule out an
indirect call, alias/computed store or a different installed build. UI sequences
visible in this handler select other modes; they must not be presented as a shell
activation recipe. The page's setting display is likewise conditional on mode 3.

A bounded follow-up checked addresses independently of those setter calls. Across
the complete decoded `.text`, **110** ADRP instructions materialize page `456000`;
all have an immediately following ADD from that page register. Four materialize
the exact mode address:

| ADRP / ADD | Memory operation | Interpretation |
|---|---|---|
| `40752c / 407530` | `407538: str w1, [x0]` | The known setter, using the saved argument |
| `407d90 / 407d94` | `407d98: ldr w0, [x0]` | Setting-display gate |
| `407f1c / 407f20` | `407f24: ldr w0, [x0]` | Value-adjustment gate |
| `407fd0 / 407fd4` | `407fd8: ldr w0, [x0]` | ENTER/exit gate |

Four adjacent-base materializations address `456ed8`: loads at `407dc8`,
`407f48`, `407fec`, and the one-byte store at `407f5c`. That store does not reach
the mode four bytes later. Nearby page references include six to `456e48` and 23
to `456ea8`. The former initialization writes six eight-byte pointer slots from
`456e48` through `456e98` in 16-byte strides. The latter is an indexed table whose
file-backed entries are `(456c98,6), (456cf8,21), (456e48,6)` in 16-byte records;
these observed pointer/count slots end at `456ed7`. Neither static layout nor those
initialization stores overlaps the mode. The page-object initializer `4072d4`
constructs the object at `5e3f60`, not this mode address. Other adjacent immediate
bases are `456ee0` (one reference), `456ee8` (nine), `456ef0`, `456ef8` and
`456f00` (one each); their inspected accesses do not overlap `456edc`.

No ADR or MOV immediate materializes an address in `456e80..456f07` in `.text`.
No byte-aligned raw 64-bit pointer value to `456ed8`, `456edc` or setter `40751c`
occurs anywhere in the ELF, and no relocation writes within `456e80..456f07`. These
negative checks cover those literal/materialization forms, not every possible
computed address. Indexed table accesses, spilled pointers, cross-function aliases,
bulk-copy destinations and arbitrary indirect dispatch were not exhaustively
resolved. Consequently this pass establishes **one concrete mode writer in the
recognized references**, not an all-writers proof and not universal unreachability
of mode 3. No concrete alternative writer or mode-3 activation edge was found.

The page object is constructed: RTTI name `11CPageDmyVer` is at `42f828`, its
vtable address point is `42f790`, and slot `+28` points to handler `407eb0`.
Constructor `408270` installs that address point; static initializer `407318`
is in the init array at `455b60`. This closes object construction, not mode-3
reachability or every virtual UI dispatch edge.

Unlike the prepared GS0 scripts, the main shell call does not redirect its file
descriptors to GS0. It inherits qctest's terminal and UID; stock `go.sh` provides
an xterm path. Root-like directory names and `XDG_RUNTIME_DIR=/run/user/0` are
not a measurement of effective privileges. Terminal cleanup/input usability is
also unobserved. The minimum remaining proof is a source/static writer of mode 3
or a controlled observation of that state and its inputs, followed by confirmation
of the inherited terminal/UID and `net.sh` side effect.

Reproduce the bounded static checks with Python 3.13.7, installed `capstone` and
`pyelftools` (no target execution):

```sh
python tools/qctest_shell_study.py local/qctest
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests -p test_qctest_shell_study.py -v
```

The checker pins the artifact, checks the endpoint/gate instructions, resolves
the PLT imports, scans direct setter callers and preserves the unresolved status.
It does not recover arbitrary writers or emulate the UI.

## Source-backed boot routes: selected MMC is not necessarily removable SD

The retained GPL U-Boot tree has Roland/MI078 customizations despite retaining EVK
directory names. `board/freescale/imx8mm_evk/imx8mm_evk.c:699..755` samples update,
develop, tempo, write and menu GPIOs, then sets environment strings using
`value ? "1" : "0"`. **There is no inversion in this code.** It records inputs;
the inspected function does not itself implement the recovery/update decision.

`include/configs/imx8mm_evk.h` defaults to `script=boot.scr`,
`console=ttymxc1,115200`, `mmcautodetect=yes`, and MMC environment device 1.
Its boot command attempts a script before `Image` on `${mmcdev}:${mmcpart}`.
However `board_late_init` calls `board_late_mmc_env_init()`; in
`board/freescale/common/mmc.c` that routine replaces `mmcdev` with
`mmc_get_env_dev()` when autodetection is enabled. The implementation in
`arch/arm/mach-imx/mmc_env.c` derives SD/MMC instance from BootROM software info.
Thus the source default **does not prove** normal eMMC boots will execute a
removable-card `boot.scr`. Saved environment, board override, actual boot device
and deployed build must be resolved first.

`configs/imx8mm_evk_defconfig` enables MMC environment, Fastboot and SPL USB SDP
features, but a source defconfig is not evidence of deployed entry/access policy.
No fuse state, HAB openness, unsigned-code acceptance, available USB connector or
physical UART voltage can be inferred from it. No installed U-Boot binary, saved
environment, complete rootfs or recovery image was recovered in this scoped audit.

## A custom I2C channel really exists, without a shell claim

The retained kernel contains `drivers/i2c/i2c-slave-rx.c`, copyright Roland
Corporation 2020. It exposes `i2c-slave-%d` character devices, registers compatible
`slave-rxtx`, and uses four-byte FIFO frames; a received high-bit byte resets frame
collection. The MI078 DTS enables I2C3 at 100kHz and a slave node at address
`0x08 | I2C_OWN_SLAVE_ADDRESS`. These are custom board/control paths, not absence
of Roland code in a generic NXP tarball.

The actual application connects this driver:

| mi078 address | Observation |
|---|---|
| `4374e8..43750c` | Initializes object `4106758` with `/dev/i2c-slave-2` at `1313e60` |
| `bdeef0`, call `bdef08` | Loads that object's path and opens it with flags 2 (`O_RDWR`), storing fd at object+8 |
| `bdef50`, `bdefb0` | Worker opens that object and reads four bytes |
| `bdf008` | After validation `bdeda8`, invokes callback stored at `4106778` |
| `bdf140`, `440f90` | Thread setup creates worker `bdef50`; application startup calls setup |
| `cff844` → `bdf130` | Registers callback `cfead0` at `4106778` |
| `cfead0` | Queues the four-byte word through mutex/condition-protected global `d55e8a0` |

An adjacent registration at `cff834` also uses `cfead0` on another thread object.
Shared queue ingress does not prove physical I2C peer identity or a shell-command
protocol. The inspected driver and callback have no shell execution path. This
is a separate control-plane lead for ownership/message decoding, not a remote login.

Stock `go.sh` loads `g_serial` without a port-count override. The retained
`drivers/usb/gadget/legacy/serial.c` defaults to ACM and `n_ports=1`; no available
second `ttyGS1` login is established. The stock DTB has USB1 host and USB2 peripheral,
but physical connector/peer wiring remains unknown. UART2 is the chosen console;
other enabled UARTs/comments do not establish a free external debug header.

## What the prepared archives prove, and recovery limits

The stock app archive has 440 members / 346 regular files. It contains `go.sh`,
`mi078`, `qctest`, the DTB, application assets, factory content and several utility
scripts. It does **not** contain an installed `/etc` tree, login database, getty,
SSH/telnet configuration, `net.sh`, bootloader, saved environment or recovery image.
This bounded absence cannot establish those components are absent on the instrument.

Both prepared `_DATA_FNTM0` copies have the same modified `go.sh` proposing a
GS0 shell loop. They do not demonstrate update acceptance or actual shell startup.
The persistent-shell package retains the original encrypted `update_fntm0`;
the other contains a 393-byte plaintext replacement. The execution/decryption
contract for that replacement is unproven. The normal application's GS0 IPC
ownership is established separately in [the transport study](host-transport-study.md).

An update failure/hash rejection is not a proven safe rollback. Without the actual
recovery writer/partition behavior, atomicity and ordering remain unknown. Before
testing a persistent change, a stock restore image plus a verified recovery/boot
entry and its write boundaries are needed; neither prepared package supplies that
proof. No such testing was performed in this audit.

## Source identity and retained provenance

The stock update retained from earlier research is `sys_v108.zip`, 274624040 bytes,
SHA-256 `2edf37f2543ece10319079a8626edce93d6062511143a959ff3a961dbfdff939`.
The current pass compared stock archive members with the analysis binaries; it did
not redownload the update. Vendor artifacts stay ignored/local.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Stock `_DATA_FNTM0` | 385464320 | `cfbf9bf1134746096ba26561e2d0f32528b251f9b59ae5e574523fcdfd11643a` |
| Stock `go.sh` | 1547 | `e51155f468927d69792cd9612d8bc676f8b2ee41901d769112c134c83b126964` |
| Stock MI078 DTB | 40714 | `ffe1b637abf981b1e0adae2684b25cd47f952925e14b66a2e5a35ccaf725904a` |
| Stock `mi078` | 61181491 | `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7` |
| Stock `qctest` | 304912 | `d87316806a54548920773b026f0b4d332b702450e1c1e7c317f5dc46ebfa29a6` |
| Original encrypted `update_fntm0` | 1607 | `ef69453ca9dfa7af7cff043e43bcbc5598fc07fe4e445e55e13e03d812103013` |
| Modified `_DATA_FNTM0` (both prepared packages) | 385464320 | `b32d0b363d67ec83ae1d8e47b709419475dfb896050c4c10e2500d43dd09ef0c` |
| Modified `go.sh` | 1547 | `96e816d5336966ef48ec6c669534597f842746f62ade7f55774036a15fd3b0fb` |
| Plaintext prepared `update_fntm0` | 393 | `345b2caf021466f348018cb93dbaecb95d64fbe1d169d13df032353352a5aae8` |
| Retained GPL `uboot.tgz` | 19814891 | `2ab1095d7e3855c3f6da80f42af41a441583fe9202ab9eb70f0666c26dd64bb4` |
| Retained GPL `linux.tgz` | 168881839 | `61dae0585fb220400dd821ea21770910031d6ef3c2ccd7fd7fee1b1d86596b57` |
| Retained GPL `imxboot.tgz` | 163812 | `643f8462dfc339c2d0ad6a16340531f3204802ffc2445d34984130392b83e5f3` |

The GPL tars were retained under the earlier `fantom_dl` extraction, now preserved
under `local/upstream/fantom-retained-gpl` with a manifest. The outer official-source
ZIP was not located in the bounded local search, so its prior stated checksum and
the complete download-to-tar chain were not independently verified here. MI078 DTS,
board customizations and Roland driver support family relevance; exact deployed
kernel/U-Boot build equivalence is still unknown.

## Supersession map for older vault notes

This report and the linked transport study take precedence over the following
historical claims. The audit did not edit the vault. Hashes identify the exact
notes read before the coordinating worker's correction pass.

| Note / SHA-256 at audit | Claims requiring supersession |
|---|---|
| `BMC chips.md` / `4c6170c21ff855332fcd955ed79b3ce3e46bfea792d8ac509357df31d92112aa` | ASCII UART4→CORE0 transport; unconditional clock/DAC initialization inferred from strings; prepared shell boots/owns BMC I/O. Use actual GS0 dataflow; startup timing and shell operation remain unobserved. |
| `Fantom-0 research.md` / `1f4c57ca67ceb9ee1e6e4d3d57247930ec237efd78513ef14200663003275228` | Guaranteed removable-SD script; inverted GPIO values; source defaults prove open HAB/unsigned boot, physical UART voltage/pads or deployed Fastboot; no custom Roland I2C source. Correct with autodetection, raw values and actual custom driver; hardware/security state unknown. |
| `Fantom-07 rootshell update.md` / `a0c7c687ef99426fb39dbefbf2f0a3656ba52d932862dbeefb857a07a883632d` | Prepared shell validated, USB COMPUTER endpoint assignment, spare GS0, hash-failure safety, exact recovery flow/key location. Prepared artifacts alone prove none of those; restore/write behavior is missing. |
| `Fantom-0 update_fntm0 passphrase.md` / `9432ff3c9cfd0f6df81be0628cf4ce503b4cc17574bf79a5fa1319b35cb4fc81` | Unsupported key-at-rest/plain-string certainty and brute-force timing estimates. This route audit recovers no key or installed recovery/rootfs; use the separate cryptographic study for measured packet/KDF facts. |

No operational credentials or vendor bytes are included in this report or checker.

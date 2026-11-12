OSCAIRN FANTOM-0 PERSISTENT SSH INSTALLER
Experimental development tool; not affiliated with Roland.

REQUIRES ROLAND SYSTEM VERSION 1.08 BEFORE INSTALLATION.
Check MENU -> SYSTEM -> INFO first. This package does not upgrade the keyboard
to 1.08. Other system versions are not supported by this installer.

IMPORTANT: After Update (board1) End, power OFF, remove the drive and reboot
normally. DO NOT plug this drive into EXT DEVICE for board2. There is no board2
payload in this SSH-only package.

WHAT YOU NEED

- A Fantom-07 running the shared Fantom-0 v1.08 application. The application
  hash is checked before installation. Fantom-06/08 have not been hardware-tested.
- A Fantom-formatted USB flash drive. Back up files before formatting a drive.
- A USB Ethernet adapter and a connection to your computer's local network.
  The adapter tested on the keyboard is a Realtek RTL8153. A hub is optional.
- An OpenSSH client on your computer (included with macOS).

This provides key-only root SSH on port 2222 over USB Ethernet. It does not
provide a serial shell through USB TO COMPUTER. Your private key stays on your
computer; only its PUBLIC key goes onto the flash drive.

1. PREPARE A KEY

If you already have an Ed25519 key pair, reuse its .pub file and matching private
key instead of generating another pair. Do not overwrite an existing key pair.
Otherwise, on macOS/Linux:

  mkdir -p "$HOME/.ssh"
  ssh-keygen -t ed25519 -f "$HOME/.ssh/fantom_ed25519" -C fantom-ssh

The two resulting files have different jobs:

  fantom_ed25519       PRIVATE key: keep on the computer; never copy to the drive.
  fantom_ed25519.pub   PUBLIC key: copy this one to the drive.

A passphrase chosen during key generation protects the computer's private key;
it is not a Fantom root password.

2. PREPARE THE FLASH DRIVE

Extract the ZIP. Copy the contents of the extracted folder, not the ZIP or the
folder itself, to the drive's root. Add the public key under the EXACT name:

  FANTOM_SSH_AUTHORIZED_KEYS

There is no .pub or .txt extension on that destination filename. For example,
replace YOUR_USB with the drive's actual volume name on macOS:

  cp "$HOME/.ssh/fantom_ed25519.pub" "/Volumes/YOUR_USB/FANTOM_SSH_AUTHORIZED_KEYS"

The required root layout is:

  USB drive/
    update_fntm0
    dropbearmulti
    FANTOM_SSH_AUTHORIZED_KEYS

README.txt, SHA256SUMS and the license files may remain alongside these files.
Do not leave an older update_fntm0, _DATA_FNTM0 or FNTM0_UPA.BIN at the drive's
root. Back up old files on your computer and replace/remove them before copying
this package. Never mix this installer with a full Roland firmware update.

The distributed ZIP contains NO authentication key. The installer requires the
public-key file even on a reinstall. Multiple plain ssh-ed25519 public-key lines
are accepted, up to 16 KiB total. RSA keys, certificates, private keys and
advanced authorized_keys options are rejected. If you reuse another key pair,
use that pair's private-key filename in the SSH command below.

Optional integrity check, from the extracted package folder on macOS:

  shasum -a 256 -c SHA256SUMS

The checksum list covers the distributed files, not the public key you add.

3. INSTALL THIS SSH-ONLY PACKAGE

Save your edits and turn the Fantom off. Insert the drive into USB MEMORY.
Hold WRITE while powering on, until the board1 update screen appears.
Wait for installation to finish. The installer prints:

  OSCAIRN SSH INSTALL OK: key-only SSH on USB networking, port 2222

The stock wrapper then displays Update (board1) End. It may clear the installer
text quickly. End alone does not prove success: the wrapper also displays it
when its child installer fails. A successful SSH login after restarting is the
functional confirmation. If INSTALL FAILED appears, note the error and correct
it before trying again; missing/invalid key and binary files are rejected before
Linux target files are changed.

Once board1 has finished, power off, remove the drive, then boot normally with
no buttons held. DO NOT move this drive to EXT DEVICE. There is no board2 payload
in this SSH-only package. The full two-stage Roland update procedure is different.
Never interrupt installation while files are being written.

4. CONNECT

Connect the USB Ethernet adapter to USB MEMORY, directly or through a hub, and
connect its Ethernet cable to the same LAN as your computer. DHCP is handled by
the keyboard. Find its address in your router's DHCP leases; do not assume a
fixed IP address. Replace KEYBOARD_IP in this command:

  ssh -p 2222 -i "$HOME/.ssh/fantom_ed25519" root@KEYBOARD_IP

On the first connection, SSH asks you to verify a host-key fingerprint. If you
have a local root console, display the keyboard's fingerprint with:

  /home/root/bin/oscairn-dropbearmulti dropbearkey -y -f /home/root/.oscairn-ssh/host_ed25519

Verify the fingerprint before accepting it. It should remain the same after
normal reboots and reinstalls. A prompt for your key's passphrase refers to the
private-key passphrase you chose on the computer. Password login on the keyboard
is disabled; an ordinary root password will not authenticate.

Reboot normally and reconnect once to confirm automatic startup. No update drive
is needed for normal use. If login fails, check the keyboard's current IP,
USB MEMORY connection, adapter support and the matching private/public key pair.

PERSISTENCE, POPUP AND KEY CHANGES

The public-key list and device-specific host key are stored under
/home/root/.oscairn-ssh with root-only permissions. The host key is generated on
the keyboard during installation, never distributed. Reinstalling replaces the
entire authorized public-key list, so include every key you want to retain.

This revision also removes the earlier OSCAIRN on-screen shell popup when it
recognizes that exact startup-script version. A backup is saved as
/home/root/.oscairn-ssh/go.sh.with-popup. The change takes effect at the next boot;
it does not close a window already open. Stock and unfamiliar startup scripts
are left alone. SSH remains managed by systemd and udev, independently of go.sh.

No synth application, BMC firmware, factory content, partition layout or root
password is changed. A later full stock update may override custom files; that
has not been tested.

VALIDATION AND LIMITS

Key-only root SSH and automatic startup after a real reboot have been verified
on Fantom-07. The encrypted installer was decrypted by the keyboard's GPG 1.4.7,
and live installation was tested. Installation through the physical USB MEMORY/board1 update screen has also
been verified on Fantom-07: the saved recovery log reported INSTALL OK, and root
SSH with the same host key returned after normal startup. The startup script was
clean and no popup-shell process was present. Popup removal was separately tested
against the original probe script; unfamiliar startup scripts remain unchanged.
Fantom-06/08 and other USB network adapters have not been hardware-tested.
Interrupted writes can leave a partial installation. Keep any existing local
root-access method until you have verified reboot-time SSH.

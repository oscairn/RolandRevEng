OSCAIRN FANTOM-0 SSH INSTALLER -- experimental

Requires the verified Fantom-06/07/08 v1.08 Linux application.
This installs key-only root SSH over a USB network adapter, port 2222.
USB TO COMPUTER serial access is not provided.

1. Generate an Ed25519 key on your computer:
   ssh-keygen -t ed25519 -f ~/.ssh/fantom_ed25519
2. Copy ONLY fantom_ed25519.pub to the flash drive root, renamed:
   FANTOM_SSH_AUTHORIZED_KEYS
   Multiple plain ssh-ed25519 public-key lines are accepted. Private keys,
   certificates, RSA keys and authorized_keys options are not accepted.
3. Copy this package's update_fntm0 and dropbearmulti to the flash drive root.
   Use a Fantom-formatted flash drive. Remove the previous update_fntm0,
   _DATA_FNTM0 and FNTM0_UPA.BIN from its root first; keep backups on your computer.
   This package intentionally contains no BMC or full application update.
4. With the Fantom off, put the drive in USB MEMORY. Hold WRITE and power on.
   The install must print OSCAIRN SSH INSTALL OK, then Update (board1) End.
   End alone is not proof of success: the stock recovery wrapper ignores errors.
   If FAILED appears, record the error. Do not insert the drive into EXT DEVICE.
5. Once this SSH-only install has finished (board1 End, no writes active), power
   off, remove the drive and boot normally. There is no board2 payload in this
   installer; leave EXT DEVICE empty. This differs from a full Roland update.
6. Connect a USB Ethernet adapter to USB MEMORY (a hub can retain the keyboard).
   DHCP is handled by the keyboard. Find its IP in your router's leases, then:
   ssh -p 2222 -i ~/.ssh/fantom_ed25519 root@KEYBOARD_IP
   Check the host-key fingerprint through your local root shell before accepting.

The public key and host key persist under /home/root/.oscairn-ssh. The host key
is generated on the keyboard during installation and retained on reinstalls.
The server starts/stops with USB network devices using systemd and udev.
No password, stock go.sh, mi078, factory content, partition or BMC image is changed.
No private key is distributed. Reinstall with a new public-key file to replace
the authorized key list. Back up the computer's private key securely.

The experimental installer writes Linux files; interrupted writes can leave an
incomplete installation. Retain working on-screen root access until boot-time
SSH is tested. A later stock update may remove/override custom files; this has
not been tested. This is a development modification, not a Roland-supported tool.

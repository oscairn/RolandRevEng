#!/bin/sh
set -eu
STATE=/home/root/.oscairn-ssh
case "${1:-}" in ''|*[!a-zA-Z0-9_.:-]*) exit 1;; esac
DEVICE=$(readlink -f "/sys/class/net/$1/device")
case "$DEVICE" in */usb*/*) ;; *) exit 1;; esac
test -s "$STATE/authorized_keys"
test -s "$STATE/host_ed25519"
exec /home/root/bin/oscairn-dropbearmulti dropbear -F -E -s -j -k \
    -l "$1" -p 2222 -D "$STATE" -r "$STATE/host_ed25519" \
    -P "/run/oscairn-ssh-$1.pid"

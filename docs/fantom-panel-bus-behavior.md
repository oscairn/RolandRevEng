# Fantom-07 panel bus behavior

2026-11-12. How the panel's I2C link to the i.MX (`/dev/i2c-slave-2`, I2C3, the i.MX as slave
0x08) behaves, from Roland's GPL driver source and from the owner's FANTOM-07. Each claim is
marked **measured** (seen on the unit), **GPL source** (Roland's published kernel source),
**static** (read from Roland's programs as files) or **inferred**.

> **Not pure stock firmware.** One BMC ran a modified diagnostic CORE1 build during these
> measurements (see [the CORE1 diagnostics note](fantom-core0-key-recovery.md)). The panel bus
> does not pass through the BMCs, but the lamps and start words do.

## The driver (GPL source)

Roland's driver is `drivers/i2c/i2c-slave-rx.c` ("I2C slave mode communication", Roland 2020;
driver name `i2c-slave-coms`, compatible `slave-rxtx`, built in by `CONFIG_I2C_SLAVE_RX`). The
i.MX controller's slave mode in `drivers/i2c/busses/i2c-imx.c` (`i2c_imx_reg_slave`,
`i2c_imx_unreg_slave`, `i2c_imx_slave_isr`) is Roland's addition to NXP's 4.19.35 driver.

- **`open` registers the slave, `release` unregisters it** (`i2cdev_open`, `i2cdev_close`). While
  nobody holds the device, the i.MX does not acknowledge 0x08 and the panel's writes are NACKed.
  Open flags make no difference. A successful open discards anything queued.
- **One holder only.** A second open fails with `EFAULT` (the controller returns `-EBUSY`).
- **A second open is dangerous.** `i2c_slave_register` in `drivers/i2c/i2c-core-slave.c` stores the
  callback before asking the adapter, then clears it on refusal: the refused open wipes the
  current holder's callback, and the panel's next byte calls a null pointer in the interrupt
  handler. By the code that is a kernel panic. Not tried deliberately.
- **`ioctl(fd, 0, 0)` waits** (`wait_event_interruptible`) until a whole message is queued, and
  returns 0 whether a message or a signal woke it. Any other request gives `ENOTTY`.
- **`read` returns one 4-byte message** per call, or 0 when the queue is empty. It never blocks
  and ignores the count, so a buffer under 4 bytes is overrun. The queue holds 255 messages and
  drops the newest past that (logging `Rx fifo over flow`).
- **No `poll`** (always ready) and `O_NONBLOCK` is ignored.
- **`write` corrupts the receive queue:** it copies into the receive ring at the transmit index.
  Roland's programs never write (static). Never write.
- **Framing:** bit 7 set marks a message's first byte; bytes 1 to 3 have bit 7 clear. I2C
  transaction boundaries are ignored. The driver interprets nothing else.

## Measured on the unit

- **The panel reports only while something holds the device.** With nobody holding it, the panel
  bus took no interrupts.
- **A prompt takeover keeps it reporting.** Opened within about a second of Roland's app letting
  go, the panel went on sending with nothing sent to the instrument: 2,736 slider messages in a
  minute, 863 of them in the first 20 seconds.
- **A gap of about a minute silences it until the next power-on.** Left unheld that long, the
  panel bus stayed silent (no interrupts) on every later open. A reader killed and opened again
  seconds to minutes later also got nothing until a reboot. Reopening immediately after a kill was
  not tried.
- **The start word did not revive it.** Roland's app sends the panel two kind-0 words through
  0x75 on the host link when it starts (static). Sent from Linux in the silent state, singly and
  together, in several tries, they brought no message back.
- Inferred: the panel's own processor stops addressing 0x08 after its writes are refused for long
  enough, and something other than the start words (perhaps the BMC side at power-on) re-arms it.
  The panel firmware is not in the GPL release, so the source cannot settle this.
- **Reading as Roland's programs do works:** open read-write, `ioctl(fd, 0, 0)`, then `read` 4
  bytes until it returns 0. A `SIGALRM` with a handler did not end the wait; the driver says any
  unblocked signal would, so it was most likely blocked in, or delivered to another thread than,
  the waiting one (inferred).
- One experiment's open returned `EFAULT` ("Bad address"), which by the driver means something
  else held the device at that moment. The local record does not say what held it.

## The control map, confirmed on the unit

The panel word layout and the control IDs were read from Roland's test tool and app (static) and
recorded in Oscairn's panel map. On the unit, with Oscairn's panel dump (measured):

- Sliders 1 to 8 are analog IDs 9 to 16, control knobs 1 to 8 analog IDs 17 to 24, all 0 to 127.
- The lever (pitch bend 7, modulation 8) and WHEEL1 and WHEEL2 (5 and 6) run 0 to 1023.
- E1 to E6 and the VALUE dial are encoders, with steps of up to ±6 per message.
- The 16 pads are switches 88 to 103, in the order pad 2, 3, 4, 1, 5, 8, 6, 7, 11, 10, 9, 12, 16,
  13, 15, 14 (Oscairn's pad numbering, taken from the bottom left; to be checked).
- **SAMPLING is switch 23 and PAD MODE switch 22**, as confirmed during the owner's panel tour.
  The dump of that tour was decoded with a map that had them the other way round; Oscairn's map
  file still read 22 = sampling and 23 = padMode when this note was written.
- The four pedal-jack sense switches are 35 to 38.
- One slider chattered by one step at rest (8,519 messages from slider 4 in 3.5 minutes).
- **WRITE, MENU and TEMPO are GPIO keys only** (`gpio-keys`, `/dev/input/event1`; key codes 157,
  139 and 152). The panel bus never carried them.

## Open

- What re-arms a silenced panel short of a power cycle.
- Whether the panel ever reads from the i.MX (the driver answers a read with `0x8B` when nothing
  is queued).
- Who sends the lever, wheels and HOLD jack: the panel's processor or a BMC (the panel word's
  source bits say; not checked for those controls).

# Fantom-07 i.MX interfaces and links to the sound chips

2026-11-12. An inventory of every interface the Fantom-0's i.MX8M Mini device tree enables, and
what it says about the wires between the i.MX and the BMCs. Read from Roland's published GPL
kernel source, `arch/arm64/boot/dts/freescale/fsl-imx8mm-mi078.dts` and its `.dtsi`, compared
with NXP's `fsl-imx8mm-evk.dts` in the same tree and with the running unit's device tree (the
survey of 2026-11-12). Each claim is marked **GPL source**, **measured** (seen on the unit),
**static** (Roland's programs read as files) or **inferred**. The main claims were spot-checked
against the `.dts`; the running tree matched the source on every status, GPIO and SAI property
compared.

## Links to the sound chips the tree establishes

1. **SAI1, four wires** (GPL source; measured as a working audio link): TX data 0 (i.MX to BMCs),
   RX data 0 (BMCs to i.MX), bit clock and frame sync, the clocks driven by the BMC side
   (`sound-bmc`, codec as bit clock and frame master). 16 slots of 32 bits, left-justified. No
   MCLK wire: its pad is commented out. Roland cut NXP's eight-lane pin group down to these four
   pads. See [the audio link note](fantom-audio-link-measurements.md).
2. **The USB device link** (GPL source; measured): `usbotg2` (`32e50000`) with
   `dr_mode = "peripheral"`, the `g_serial` gadget `/dev/ttyGS0`, configured by its host at high
   speed the moment `g_serial` loads at boot. NXP's EVK has this controller disabled; Roland made
   it device-only. Inferred: its host is a BMC. See [the host link note](fantom-host-link-measurements.md).
3. **UART3 and UART4, enabled and idle** (GPL source; measured):
   - UART3 (`30880000`) is enabled with RTS/CTS on the ECSPI1 pads and no named consumer.
   - UART4 (`30a60000`) is enabled, two wires, no named consumer, with a misleading `/* console */`
     comment. NXP's EVK does not enable UART4: Roland added it.
   - **Their receive counters were zero since boot** on the unit all evening
     (`/proc/tty/driver/IMX-uart`, `rx:0` for both; their interrupt lines also at 0), including
     across Roland's app starting. No process held either port.
   - Inferred: candidate links to a BMC or another processor, unused by stock Linux software. The
     pinmux proves the pads are muxed, not where the traces go.

## The rest of what is enabled

| Interface | What it is | Basis |
|---|---|---|
| I2C1, 400 kHz | ROHM BD71847 PMIC at 0x4B | GPL source |
| I2C2, 400 kHz | Goodix touch controller at 0x14 | GPL source; measured |
| I2C3, 100 kHz | the panel: i.MX as slave 0x08 (`slave-rxtx`); see [the panel bus note](fantom-panel-bus-behavior.md) | GPL source; measured |
| UART2 | the Linux console (`ttymxc1`) | GPL source; measured |
| USB1 (`32e40000`), host | the USB MEMORY port, VBUS on GPIO1_12 | GPL source; measured |
| FlexSPI | Micron MT25QU256 QSPI NOR | GPL source |
| uSDHC3, 8-bit | eMMC with the root filesystem | GPL source; measured |
| PWM3 | display backlight | GPL source; measured |
| LCDIF, MIPI-DSI | the 720 × 1280 panel | GPL source; measured |
| FEC1, RGMII | Ethernet MAC and PHY | GPL source |
| gpio-keys | WRITE, MENU, TEMPO on GPIO5_11 to 5_13; GPIO5_10 selects the factory test at boot | GPL source; measured |

## Leftovers from NXP's reference design

Enabled in the tree but, by the evidence, not part of the instrument (GPL source, inferred):

- **UART1** with RTS/CTS and a `/* BT */` comment, reset by GPIO2_6 (`modem-reset`), together with
  **uSDHC1** (SDIO, `WLAN_EN` on GPIO2_10, no Wi-Fi child node): the EVK's Wi-Fi/Bluetooth module
  wiring, kept. UART1 also had zero traffic (measured).
- **uSDHC2**, an SD socket with card detect: the instrument has no SD slot.
- **MICFIL**, the PDM microphone block: clocked and registered as ALSA card 0, but its pin group is
  commented out, so no pads; no interrupt since boot (measured).
- **FEC1** may be another (the EVK has the same Ethernet); whether a PHY is fitted was not checked.

Roland disabled (inside `#if 0`) the EVK's SAI3, SPDIF, PCIe, camera, IR receiver, WM8524 and AK
codecs and the PCA6416 expander.

## What the device tree cannot tell

- **Which BMC is on the far end** of SAI1, the USB device link, or either UART. Both BMCs sit
  behind one dummy codec; the tree has no per-chip nodes.
- **Any link between the two BMCs** (SPI, UART, GPIO, a shared bus). The i.MX tree only describes
  i.MX pins.
- **Which of UART3 and UART4 (if either) is routed** to a BMC, the panel processor or a test
  header.
- Anything about the BMCs' own clocks, crystals, flash or wave memory.

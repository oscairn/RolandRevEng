# RolandRevEng

Independent research into Roland BMC DSPs for future custom synth engines and
interoperability with [Oscairn](https://github.com/oscairn). The initial targets
are Fantom-0 v1.08 firmware and a locally supplied ZENOLOGY plugin.
This project is not affiliated with or endorsed by Roland.

## Current status

This combines experimental offline BMC research with live Fantom Linux-access
work. It does not yet provide a loadable custom engine, complete BMC emulator,
general assembler, BMC hardware driver or BMC firmware flasher.

- Fantom-07 Linux root and persistent, key-only SSH over USB Ethernet are verified,
  including automatic access after reboot. The [SSH-only installer](docs/fantom-persistent-ssh-update.md)
  accepts a reader-supplied public key and leaves BMC firmware unchanged.
  [Download the package](packages/fantom-07-persistent-ssh-update.zip) and follow
  the [instructions](tools/fantom_ssh/README.txt): **install Roland 1.08 first**;
  after board1 End, reboot normally and **do not move the drive to EXT DEVICE**.

- A strict packet interpreter and constrained emitter support **19 exact sequence
  profiles**, with original oscillator/filter voice examples.
- The complete FDRV arithmetic reference matches the pinned native callback's
  audio and persistent state in the documented tests. This is a software
  comparison, not a measurement of BMC silicon.
- Packet framing, selected instruction contexts, resource layouts, coefficient
  generation and parts of the ARM control/loader interface are documented.
- General opcode semantics, entry/return behavior, safe loading, runtime ownership,
  hardware precision and timing remain unresolved.

Start with the [mapping status](docs/bmc-mapping-status.md),
[packet and loader map](docs/BMC%20DSP%20packet%20and%20loader%20map.md),
[semantics ledger](docs/opcode-semantics-ledger.md) and
[research queue](docs/research-queue.md). Historical results and their original
limitations remain in the [work log](docs/work-log.md).

## Quickstart without vendor artifacts

Use **Python 3.13 or later**; the numerical references use `math.fma`.
The verified environment is macOS ARM64 with Python 3.13.7. Other platforms have
not been validated. Native execution fixtures require macOS ARM64 and permission
to allocate executable memory; corpus-dependent tests skip when inputs are absent.

```sh
git clone https://github.com/oscairn/RolandRevEng.git
cd RolandRevEng
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Generate and decode an original fragment, or render an original filtered voice:

```sh
mkdir -p local
python tools/bmc_subset.py assemble examples/dry-wet-tail.json local/my-tail.bin --stored
python tools/bmc_subset.py disassemble local/my-tail.bin --stored
python tools/bmc_filtered_voice.py local/filtered-voice.wav --frames 12000
```

These examples need no Roland binary and do not open a device. Outputs must be
new paths. The emitted fragment has no executable entry/return or hardware-loading
wrapper. See [supported code generation](docs/supported-code-generation.md),
[the fragment interpreter](docs/fragment-emulator.md) and
[the filtered voice](docs/original-bmc-filtered-voice.md) for their exact contracts.

## Optional local corpus

Supply your own firmware/plugin artifacts separately. None are distributed here.
Build-specific addresses and hashes are recorded in the studies and
[evidence/summary.json](evidence/summary.json); a different build requires fresh
analysis. Dependencies are pinned in [requirements.txt](requirements.txt).

On macOS, preparing a locally installed ZENOLOGY ARM64 image also requires Xcode
command-line tools (`xcrun dyld_info`) and `c++filt`:

```sh
python tools/prepare_zenology.py '/Library/Audio/Plug-Ins/VST3/Roland/ZENOLOGY.vst3/Contents/MacOS/ZENOLOGY' --out local
python tools/extract_zenology.py
```

`tools/analyze.py` additionally expects `local/b0c1a.bin` and `local/b1c1a.bin`:
the respective `bmc*_MI078_C1A_up.bin` members of the Fantom-0 v1.08 update,
with their first 32 container bytes removed. After preparing those inputs:

```sh
python tools/analyze.py
# Inspect one build-specific native DSP0 program:
python tools/bmc_dsp.py local/b0c1a.bin --stored --offset 0xc49b0 --length 0x13e4
# Inspect CORE1's scatter map and a loader routine:
python tools/core1.py local/b0c1a.bin
python tools/core1.py local/b0c1a.bin --address 0x112f582 --size 0x122
```

`BMC_CORPUS_DIR` can point readers that support it at an alternative prepared
corpus directory. Detailed generated reports such as `evidence/analysis.json`
and `evidence/coefficient_widths.json` are local outputs, excluded from Git.
Keep vendor images, native disassembly, extracted program/coefficient tables,
provider credentials and personal working notes in ignored local storage.

## License

Original code and documentation are available under the [MIT License](LICENSE).
The research includes firmware-derived interface descriptions and instruction
templates; this license grants only rights held by the contributors and does not
license Roland firmware, plugin binaries, samples, ROMs or trademarks.
See [evidence boundaries](evidence/README.md) for what is kept outside the repository.

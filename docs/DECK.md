# Running on the deck

The same program as `emulator/`, on the Pi, with nothing faked. This file is the
operational half: what is installed on the machine, how code gets there, and what
had to be true before any of it worked.

The design half is `emulator/README.md`. The parts are `hardware/`.

## Reaching it
```
ssh -i ~/.ssh/id_ed25519 biryuzabear@biryuzabear.local
```

`biryuzabear.local` is mDNS and has been seen resolving to a second machine on the
same network — if the host key ever fails to match, find the address with
`hostname -I` on the deck rather than removing the key.

## What the OS needed
Raspberry Pi 5, 2 GB, Debian 13 trixie, Python 3.13. Both buses were off in
`/boot/firmware/config.txt` as shipped, and the LED chain needs its overlay:

```
dtparam=spi=on
dtparam=i2c_arm=on
dtoverlay=ws2812-pio,gpio=21,num_leds=12
```

SPI and I²C came up without a reboot; the WS2812 overlay does need one. `num_leds`
must match the chain — set it short and the far end stays dark with nothing to say
so.

Everything Python comes from apt, so there is no venv and no
`externally-managed-environment` argument to have: `python3-gpiozero`,
`python3-spidev`, `python3-lgpio`, `python3-pil`, `python3-numpy`. The first three
ship with the OS. Also `i2c-tools` and `git`.

## What is installed in `~`
| Path | What |
|---|---|
| `~/tarotdeck/` | this repository, rsync'd from the laptop |
| `~/e-Paper/` | Waveshare's library — cloned to prove the panel, not used by the deck |
| `~/whisper.cpp/` | built from source; `build/bin/whisper-cli` and `models/ggml-base.en.bin` |

The deck runs Waveshare's driver out of `emulator/vendor/`, not out of `~/e-Paper`.
The vendored copy is the same code and is what the emulator exercises, so there is
one driver in play rather than two.

## Deploying
```
rsync -a --delete --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
  ./ biryuzabear@biryuzabear.local:~/tarotdeck/
```

The whole repository goes, not just `emulator/` — `readers.py` reads the training
set and `sources.py` reads the system prompt, both by relative path. It is about
10 MB without `.venv`.

`emulator/fonts/` is not in git and must be present locally before the rsync, or
the deck will have no typeface. The command to fetch it is in `emulator/README.md`.

## Running
```
cd ~/tarotdeck/emulator && sudo python3 run_deck.py
```

**Root is for `/dev/leds0`** and nothing else. The character device is
`root:root 0600`; a udev rule would remove the need, and has not been written.

`run_deck.py` refuses to start anywhere but a Pi, and `run.py` is still the way in
on a desk. Neither is a fork of the other — see `emulator/README.md` for the seam.

## What decides which backend
`emulator/board.py` reads `/proc/device-tree/model` once. Everything else imports
`IS_PI` from it, so there is exactly one guess in the tree:

| Module | On a desk | On the deck |
|---|---|---|
| `mockpins.py` | installs `MockFactory` | leaves gpiozero to find the real pins |
| `controls.py` | adds keyboard drivers for the mock pins | just the four devices |
| `leds.py` | model only, read by the window | model, and writes to `/dev/leds0` |
| `buzzer.py` | real pin call plus a synthesised tone | real pin call, and it is audible |
| entry point | `run.py`, with a window | `run_deck.py`, with none |

`board.home()` exists because the deck runs under sudo: `Path.home()` is then
`/root`, and Whisper is not installed there.

## Voice
`WhisperCppEars` in `ears.py`. `arecord` streams raw 16 kHz mono on stdout and a
thread drains it, which is what gives the lenses a live level and lets a take end
itself on silence. Transcription shells out to `whisper-cli` with `base.en`.

**The capture gain ships at zero.** ALSA's `Mic` control on this dongle is 0 of 16
out of the box, and a recording then comes out the right length, the right format,
and digitally silent. `ArecordMicrophone` raises it on every open rather than
trusting whatever the card last remembered. See `hardware/parts/usb-microphone.md`.

Measured on the deck: `base.en` transcribes 20 s of speech in **2.9 s**, of which
1.7 s is the encoder. `docs/RUNTIME.md` estimated 2–4 s.

## The reading model — not yet on the deck
`sources.for_mode` falls through to `MeaningsReader`, which needs no weights and is
about the cards actually drawn. That is what the deck is doing today.

Putting the fine-tune on it is unfinished work, and the obstacle was a format one:
our export is **MLX 8-bit**, which is Apple-only, while the Pi needs **GGUF** for
`llama.cpp`. That conversion is now done — the GGUF sits on the Drive beside the
MLX weights — and what remains is quantizing it to Q8_0 on the Pi, serving it, and
measuring what a reading costs. The steps are written out in
`tarot_model/exports/qwen3_5_0.8b_v2_q8/WHERE.md`.

## Bring-up scripts
`hardware/hwtest/` holds the two programs that proved the parts one at a time —
a playground for all of them at once, and the touch-pad stopwatch. They are not
part of the deck and nothing imports them.

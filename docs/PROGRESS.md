# Progress

## Done
- Tarot LLM fine-tuning pipeline (`tarot_model/`) — EN and RU adapters on Qwen3.5-0.8B
- All parts identified and written up in `hardware/BOM.md` + `hardware/parts/`
- Enclosure envelope and internal stack: `hardware/ENCLOSURE.md`
- Power budget and its limits: `hardware/POWER.md`
- Interaction and face layout: `docs/UI.md`
- Pin allocation drafted, e-Paper on wires rather than as a HAT:
  `hardware/PINOUT.md`
- OS chosen and its traps written down: `docs/OS.md`
- Memory budget for both models on 2 GB: `docs/RUNTIME.md`

## Dropped
- LED ring (40 mm, fits nowhere) · OLED (too small to earn its space) ·
  gyroscope (no use that isn't done better by something else)

## Runs on real hardware
First session on the assembled deck, 2026-08-25.

- **The e-paper works.** SPI and I²C enabled on the Pi (both were commented out
  in `/boot/firmware/config.txt`), Waveshare's library cloned, and the 3.7"
  panel ran a full cycle: `init` → `Clear` → `display_4Gray` → `sleep`. Text and
  a border came out on the panel. Debian 13 trixie, Python 3.13, everything from
  apt — `spidev`, `gpiozero` and `lgpio` ship with the OS, `python3-pil` and
  `python3-numpy` were added.
- **The deck runs off the battery.** Pi 5 and the panel both, with no cable at
  all. `EXT5V = 5.05 V` and `throttled=0x0` while refreshing the display.
- **Every input responds.** Rotary encoder counts both directions with no
  missed steps, both tick buttons fire and are distinguishable, the touch pad
  reads every tap. Nothing idles stuck.
- **Buzzer sounds** — five tones, 1–3 kHz, on software PWM. The transistor
  stage works. Hardware PWM not set up yet.
- **All twelve LEDs light**, chase and four colours, on the in-kernel
  `ws2812-pio` overlay with VCC at 3.3 V. `dtoverlay=ws2812-pio,gpio=21,num_leds=12`.
- **The microphone records speech** — but only after raising the ALSA capture
  gain, which ships at zero. See `hardware/parts/usb-microphone.md`.
- **PiSugar does not answer on I²C** — `i2cdetect -y 1` is empty, no `0x57`.
  Cause found, see `hardware/parts/pisugar.md`: two of the pogo pins do not
  reach.

## Unproven — mostly still on paper
Ordered by how much it could invalidate:

1. **Inference time.** Everything about the interaction assumes "it thinks for a
   moment, then answers." Estimated ~17 s for a 200-token reading at Q8_0, plus
   2–4 s to transcribe. Nothing measured on our hardware yet.
2. **Both models in 2 GB.** Fits at ~1.22 GB peak at Q8_0 — running one model at
   a time, with `-ub 64`. Architecture and sizes now check out on paper; see
   `docs/RUNTIME.md`.
3. **The e-paper as a usable UI.** The panel and driver now run — what is still
   untested is the fast mono refresh: `display_1Gray` loads the A2 waveform, but
   how ~0.3 s actually looks with text, and how many fast refreshes the panel
   takes before it needs a cleaning full one, is unknown. Only `display_4Gray`
   has been exercised.
4. **Current draw under real load**, measured with an inline USB-C meter.
5. **The chamfer.** Wall thickness, diffusion, and bleed between LEDs — one small
   test print answers all three.
6. **How thick a wall the touch sensor reads through.** A ladder of printed
   plates, 1 to 4 mm, in the real filament. Rides along on the same test print.

## Still open in the design
- Where the dictation control goes — the front face has no room left for it, so
  bottom edge or back
- How the transcribed question gets confirmed
- One lit chamfer or both
- Gear size, which collides with where the LED column starts
- Where the shuffle seed comes from. Right now it's plain `random.Random`
  (`emulator/tarot.py:59`) — no real-world entropy. The touch pad only gives a
  tap timestamp, which is too little entropy. Idea floated: hash the raw
  microphone PCM buffer of the question (before Whisper touches it) — mic
  self-noise and room acoustics in the low bits give real entropy, and the
  buffer already exists for transcription. Not decided, not designed —
  depends on whether the mic path exposes raw samples before Whisper
  consumes them.

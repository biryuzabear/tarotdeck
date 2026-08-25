# Emulator

Runs the deck on a desktop machine, with no Pi and no parts on hand. Everything
except the physical panel, contact bounce and the battery lives here.

**The same tree runs on the deck.** `run_deck.py` is the entry point there and
`board.py` decides which backend each seam takes; there is no second
implementation. How the machine itself is set up is `../docs/DECK.md`.

```
run.py              entry point on a desk — app in a thread, window on the main thread
run_deck.py         entry point on the Pi — no window, no keyboard, real pins
board.py            is this a Pi? the one place that asks
face.py             the device drawn to size — body, gears, LED lenses, pad
layout.py           where things sit on the panel; the face reads it for the LEDs
gravure.py          the alchemy-sigil and PCB-trace ornament
buzzer.py           real TonalBuzzer on a mock pin, plus an audible square wave
mockpins.py         the one mock pin factory everything shares
panel.py            the window: 280x480 portrait, four greys, flash, ghosting
fake_epdconfig.py   the eleven names, and the SPI stream decoded back to pixels
controls.py         real gpiozero devices on mock pins, driven from the keyboard
leds.py             the six-row vocabulary, and /dev/leds0 when there is one
session.py          the state machine; screens.py draws what it decides
pins.py             mirror of hardware/PINOUT.md
timings.py          refresh durations and the flash sequence — correct them here
vendor/             Waveshare's own epd3in7.py and epdconfig.py, unmodified
```

```
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python run.py
```

| Key | Control |
|---|---|
| `left` / `right` (or `up` / `down`) | right gear — turn |
| `z` | left gear, tick left — back |
| `x` | left gear, tick right — confirm |
| `space` | touch pad — tap to start dictation, tap again to stop |
| `esc` | quit |

## Pointing it at a model

With nothing set, the deck reads from `ScriptedReader`, which replays real answers
from the training set. To put a real model behind it:

```
# a llama-server on the loopback — what the device itself will run
TAROTDECK_LOCAL_URL=http://127.0.0.1:8080 ./.venv/bin/python run.py

# our own fine-tune, served from MLX — the real thing
M="$HOME/Library/CloudStorage/GoogleDrive-biryuzabear@gmail.com/My Drive/Projects/Tarot Device/qwen3_5_0.8b_v2_q8"
../.mlx/bin/python -m mlx_lm.server --model "$M" --port 8081 &
TAROTDECK_LOCAL_CHAT_URL=http://127.0.0.1:8081/v1 \
TAROTDECK_LOCAL_MODEL="$M" TAROTDECK_LOCAL_NAME="tarot v2 q8" ./.venv/bin/python run.py

# or Ollama, for anything else
TAROTDECK_LOCAL_CHAT_URL=http://localhost:11434/v1 \
TAROTDECK_LOCAL_MODEL=smollm2:1.7b ./.venv/bin/python run.py

# the networked program
OPENAI_API_KEY=... TAROTDECK_CLOUD_MODEL=gpt-4o-mini ./.venv/bin/python run.py
```

## Voice

With `sounddevice` and `mlx-whisper` installed the pad opens the real microphone and
Whisper transcribes the take; without them, or with `TAROTDECK_TYPED=1`, a fixed
question stands in. The info pane says which. Whisper is `base.en`, matching what
docs/RUNTIME.md picked for the Pi, and the weights are fetched once on first run.

macOS will ask for microphone access the first time, and until it is granted the
stream returns silence rather than an error — which the deck reports as "nothing was
said" rather than inventing a question.

The pad is push-to-start, push-to-stop, not hold. Measured on our own TTP223: a
held touch is dropped after **7.5 seconds**, not the ten to fifteen others report,
and once it has let go a resting finger is indistinguishable from no finger at all
— the recalibration folds it into the baseline and there is no signal left to read.
So the ceiling cannot be worked around, only stepped past, and toggling does that.
`controls.Tap` filters the chatter around a release: any edge re-arms a timer, and
a tap counts only after a second of quiet. A take also ends itself after 1.6 s of
quiet, or at the ten-second cap. The numbers are in
`../hardware/parts/touch-ttp223.md`.

The mode switch in Settings chooses which is asked. Nothing is chosen until the
cards are drawn, and if the endpoint is unreachable the deck falls back to the
scripted reader and says so in the info pane rather than pretending.

`TAROTDECK_SCALE=1.4` enlarges the window; at 1.0 the panel is one screen pixel
per panel pixel.

## The face
Drawn from the dimensions in [docs/UI.md](../docs/UI.md): a 76 x 126 mm body, the
panel's 47.32 x 81.12 mm of glass centred across the width with the driver board's
96.5 mm pushed to the bottom, gears in both top corners, mic slots between them,
the dictation pad at the bottom edge, and six 10 mm LEDs down each side at the
chamfer — twelve on the chain, in three mirrored rows. Everything is placed in millimetres and converted at 5.92 px/mm, so the
proportions on screen are the proportions in the hand.

**Portrait only.** The device is never held sideways. Everything is drawn at
280 x 480 and handed to `getbuffer` in that orientation, so the driver's
landscape branch — which rotates in software — is never taken.

**Three LED rows, six LEDs.** One row is two lenses, mirrored left and right,
always the same colour. They sit low on the face, level with the three menu rows,
each about 6.4 mm across because the gap beside the glass is only 7.17 mm.
`leds.py` speaks in rows and writes the doubled bytes.

**The screen is split.** The top informs — title, state, and a gravure ornament;
the bottom chooses — three rows, one per LED. `layout.py` holds the split so the
face can place the lenses against the same numbers.

**Card faces are not generated.** Real card art will be supplied. The gravure
vocabulary dresses the informing half of the menu instead — see
[docs/UI.md](../docs/UI.md) for what it draws and the two rules that keep it
legible at 150 dpi. `gravure.py` holds it.

**The buzzer clicks on every scroll step**, and plays a two-note chirp on confirm
and its reverse on back. `buzzer.py` calls the real `gpiozero.TonalBuzzer` on the
mock pin and separately synthesises a square wave through the mixer, so the pin
logic is genuine and the sound is only for the desk. Muting is in Settings.

**Scrolling does not repaint the screen.** The menu is drawn once, its rows
pitched to the 10 mm LED spacing, and moving the encoder only moves the lit LED.
That is the behaviour [docs/UI.md](../docs/UI.md) asks for — it costs no refresh
and spends no ghosting budget — and the emulator is what makes it checkable.

Fonts are **IBM Plex Mono**, fetched into `fonts/` and kept out of git. A serif
face at 150 dpi was thin and muddy on four grey levels; a mono face at a heavier
weight holds up. Restore them with:

```
base=https://github.com/IBM/plex/raw/master/packages/plex-mono/fonts/complete/ttf
for f in Regular Text SemiBold Bold; do curl -sfL -o fonts/IBMPlexMono-$f.ttf $base/IBMPlexMono-$f.ttf; done
```

**pygame-ce, not pygame.** Plain pygame 2.6.1 has a broken `font` module on
Python 3.14 — `cannot import name 'Font' from partially initialized module`.

## What gets faked

| Layer | How |
|---|---|
| e-Paper | fake transport under the **real** `epd3in7.py` |
| Encoder, buttons, touch | gpiozero `MockFactory` |
| Buzzer | gpiozero `MockPWMPin` — logic only, no sound |
| WS2812 chain | plain writes to a regular file |

### Text streams one word per fast refresh
0.3 s a word, which is about 200 words a minute — close to reading pace. It falls
out of the panel rather than being imposed on it: each word is one `display_1Gray`
call with the A2 waveform. This is the interaction most exposed to the 5-partials
rule below.

### The display seam — decided
`epd3in7.py` touches exactly **11 names** on `epdconfig`:

```
RST_PIN  DC_PIN  CS_PIN  BUSY_PIN
digital_write  digital_read  delay_ms
spi_writebyte  spi_writebyte2  module_init  module_exit
```

Supply an object with those — `digital_read` returning `0` so `ReadBusy()` does
not hang — and the real, unmodified driver runs on macOS. Verified: `init(0)`
returns 0, `getbuffer` yields 16800 bytes and `getbuffer_4Gray` 33600, and
`display_4Gray` completes. The shim must land before `epd3in7` is imported;
`epdconfig`'s own imports are lazy, so that is enough.

Chosen over a hand-written PNG fake because it exercises the real LUTs and real
bit-packing — what runs on the laptop is what ships.

`digital_read` reports busy for the length of the refresh rather than returning 0
immediately, so `ReadBusy()` blocks the app thread exactly as it would on glass.
The pacing is not simulated on top — it comes from the driver's own wait loop.

The shim watches the byte stream and rebuilds the image from it: plane `0x24` and
plane `0x26` combine two bits per pixel, verified to round-trip to exactly
`0, 128, 192, 255`. The LUT sent on `0x32` identifies the waveform, so the window
knows whether a refresh flashes:

| LUT | Used by | Flashes |
|---|---|---|
| `lut_4Gray_GC` | `display_4Gray`, `Clear(mode=0)` | yes |
| `lut_1Gray_DU` | `Clear(mode=1)` | no |
| `lut_1Gray_A2` | `display_1Gray` | no |
| `lut_1Gray_GC` | unused by the driver | yes |

Native buffer is portrait 280 x 480; landscape is recovered with `ROTATE_270`.

Waveshare's own `epdconfig` picks among `RaspberryPi`, `JetsonNano`, `SunriseX3`
hardcoded at import. On macOS there is no `/proc/cpuinfo`, so it falls through to
`JetsonNano()` and dies with `RuntimeError: Cannot find sysfs_software_spi.so`.

### Inputs
`gpiozero 2.0.1` installs on macOS with no Pi dependencies. `Button`,
`RotaryEncoder` and `TonalBuzzer` all work under `MockFactory`; pins are driven
with `factory.pin(n).drive_low()` / `.drive_high()`. Feeding the encoder a
quadrature sequence moves `enc.steps` correctly in both directions.

`MockFactory(revision='c04170')` makes it report a 5B with header J8 — undocumented
but real, and only matters if something reads `board_info`.

Pin numbers come from [PINOUT.md](../hardware/PINOUT.md) and must not be
duplicated here.

### LEDs
`/dev/leds0` is a character device written as 4 bytes per LED — `R, G, B, W`,
little-endian. Point the path at a regular file and mirror the three traps: a
1-byte write at offset 0 sets brightness rather than pixel 0, a short write
blanks every LED past its end, and the full `num_leds * 4` must always be sent.

## The waveform tables, decoded

Not vendor figures — read out of the four LUTs in `epd3in7.py` against the
SSD1677 datasheet, section 6.7. A LUT is 105 bytes: 50 of VS[nX-LUTm] (ten
groups, four phases, two bits each, five LUTs), 50 of TP/RP (phase lengths in
frames, plus a repeat count per group), and five that set the frame rate.

Sum the frames and the two published figures fall out exactly at **25 Hz**,
which is how the frame rate was pinned down — the datasheet does not decode
those five bytes.

| LUT | Frames | Time | What it looks like |
|---|---|---|---|
| `lut_4Gray_GC` | 76 | **3.04 s** | black 0.56 s, then 3x (white 0.32 / black 0.32), then 0.56 s while the image forms |
| `lut_1Gray_GC` | 38 | 1.52 s | one black inversion, 0.6 s, then settle. Driver never uses it |
| `lut_1Gray_DU` | 28 | 1.12 s | no inversion. Used by `Clear(mode=1)` |
| `lut_1Gray_A2` | 8 | **0.32 s** | no inversion, and no drive at all on pixels that don't change |

Waveshare's "3 s full, 0.3 s partial" are 3.04 and 0.32. The numbers are the
waveform, not a marketing round-off.

`waveform.py` parses whatever LUT the driver sends and hands the window both the
duration and the inversion sequence, so nothing about refresh timing is
hardcoded — change the driver's tables and the emulator follows.

### Why ghosting happens, from the table itself
The A2 waveform has one group, two phases, and its VS entries are **hold** for
every LUT except the two transitions that actually change: black-going pixels get
driven black, white-going pixels get driven white, and everything else is not
driven at all. There is no inversion, so nothing re-balances the charge that a
previous frame left behind.

That is the mechanism behind the "full refresh every few partials" rule, and it
is visible in the emulator: each fast refresh deposits a faint trace where ink
was erased, the traces accumulate, and a `lut_4Gray_GC` refresh wipes them.
`timings.GHOST_PER_FAST_REFRESH` sets how fast it builds — the rate is a guess,
the mechanism is not.

## Display fidelity rules
The emulator must enforce what the panel enforces, or the design will look right
on a Mac and fall apart on glass.

- **480 × 280** over an active area of 81.12 × 47.32 mm — 0.169 mm per dot,
  ≈150 dpi. A glyph 16 px tall is 2.7 mm on the case.
- **Four greys only** — GRAY1..GRAY4 = `0xff / 0xC0 / 0x80 / 0x00`. Quantize hard.
- **Partial refresh is mono.** No greys in it at all. Whatever redraws often has
  to be two-colour.
- **3.04 s full, 0.32 s partial** — derived above, and enforced through the
  driver's own busy loop rather than layered on top.
- Vendor limits: no more often than every 180 s, no more than 5 partials before a
  full one.
- Both orientations are accepted by `getbuffer`: 280 × 480 is taken as-is,
  480 × 280 is rotated in software.

## What cannot be faked — hardware only
- **Contact bounce.** gpiozero's mock does not implement it; `_set_bounce` is a
  stub marked `# XXX Need to implement this`. `bounce_time` is untestable here.
- SPI timing, the refresh flash, real contrast, ghosting.
- Perceived LED brightness — the kernel applies its own gamma table before the
  PIO.
- Whether the touch pad reads through the case wall.
- Battery draw.

## Not worth adopting
Checked and rejected: **omni-epd** (dormant since 2024-11; not on PyPI; won't
install on macOS — `spidev` needs `linux/spi/spidev.h`; its mock can't do gray4),
**EPD-Emulator** (maintained, but no `display_4Gray`/`getbuffer_4Gray` and its
`init()` takes no mode), **epdlib** (lists epd3in7 as unsupported), **inky/mock**
(Pimoroni panels only), **tkgpio** (pins `gpiozero<1.7`, drags in a broken
downgrade, needs `_tkinter`). The RPi.GPIO fakes are all abandoned and fake an
API that doesn't work on Pi 5 anyway.

No `epd_mock`, `fake_epd`, `waveshare-mock` or `epaper-simulator` exists on PyPI.

## Full-system emulation — not a thing
QEMU has no Pi 5 model and no work in progress: `raspi5` and `bcm2712` both
return zero hits in master. Even on modelled boards the GPIO blocks are register
facades with edge detection stubbed out, so a touch input could not be simulated.
RP1 is not emulated anywhere. Wokwi's "Raspberry Pi" means the Pico.

UTM on Apple Silicon is genuinely useful for the *software* half — Whisper, the
model runtime, packaging, systemd — but it is `-machine virt`: no header, no
`/dev/gpiochip*` at all. Use Debian or Ubuntu arm64 there; Raspberry Pi OS
expects the VideoCore bootloader, not UEFI.

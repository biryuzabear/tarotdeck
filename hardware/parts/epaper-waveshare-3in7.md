# Waveshare 3.7" e-Paper HAT

| | |
|---|---|
| SKU | Waveshare **18057** |
| Resolution | 480 × 280, 0.169 mm dot pitch |
| Colors | black/white + 4 grey levels |
| Driver IC | **SSD1677** — [datasheet](https://files.waveshare.com/upload/2/2a/SSD1677_1.0.pdf) |
| Interface | SPI |
| Voltage | 3.3 V / 5 V (onboard level translator); wiki says 5 V for power and signal |
| Refresh | full **3.04 s**, partial **0.32 s** — decoded from the driver's LUTs, see below |
| Driver board | 58 × 96.5 mm |
| Panel alone | 93.3 × 54.9 × 0.78 mm, active area 81.12 × 47.32 mm |
| Product page | https://www.waveshare.com/3.7inch-e-paper-hat.htm |
| Panel spec PDF | https://files.waveshare.com/upload/7/71/3.7inch_e-Paper_Specification.pdf |
| Wiki | https://www.waveshare.com/wiki/3.7inch_e-Paper_HAT_Manual |
| Driver library | https://github.com/waveshareteam/e-Paper — Python `waveshare_epd/epd3in7.py` |

## Pins used (of the 40-pin header)
| Signal | BCM | Board |
|---|---|---|
| DIN (MOSI) | 10 | 19 |
| CLK (SCLK) | 11 | 23 |
| CS (CE0) | 8 | 24 |
| DC | 25 | 22 |
| RST | 17 | 11 |
| BUSY | 24 | 18 |

Plus 3.3 V and GND. Six signals, eight wires. **There is no PWR pin** — see below.

## How it connects — decided: on wires, not as a HAT
The included **8-pin cable** goes to individual header pins. Nothing gets
soldered, nothing gets bought, and seating it as a HAT — which would cover the
whole 40-pin header — is avoided.

Two things follow: the rest of the header stays free for the encoder, LEDs, touch
and buzzer, and the driver board can be placed independently of the Pi inside the
enclosure. The wiki gives 8-pin wiring tables for Pi, Jetson, STM32, Arduino.

The 8 wires are VCC, GND, DIN, CLK, CS, DC, RST, BUSY.

## PWR (GPIO 18) — delete it from the driver
`epdconfig.py` drives a PWR pin on BCM 18. **This board has no such net.** The
[schematic](https://files.waveshare.com/upload/8/8e/3.7inch_e-Paper_Schematic.pdf)
contains no PWR anywhere; header H1 carries the 8 signals above and nothing more.
The driver is toggling a pin that goes nowhere.

The lines were added
[2023-04-21](https://github.com/waveshareteam/e-Paper/commit/6ec0aacc) for the
separate **E-Paper Driver HAT Rev2.3** — the board you plug bare panels into,
which really does gate panel VCC through a switch. `epdconfig.py` is shared
across every model, so the 3.7" inherited code for hardware it doesn't have.

`epd3in7.py` itself never mentions PWR. Remove `PWR_PIN = 18`, the
`gpiozero.LED(self.PWR_PIN)` line, the `.on()`/`.off()`/`.close()` calls in
`module_init`/`module_exit`, and the `elif pin == self.PWR_PIN` branches — and
GPIO 18 is free. Waveshare's own fix for real Rev2.3 boards is to tie PWR to
3.3 V, which confirms nothing depends on it being switched.

`epd.sleep()` is unaffected; that's the power saving that matters here.

Source: https://github.com/waveshareteam/e-Paper/issues/393

⚠️ Waveshare contradicts itself on the connector: the package list says "PH2.0
20cm 8Pin", the wiki FAQ says the 8-pin connectors on e-Paper HATs are 2.54 mm
pitch. Measure before cutting a hole for it.

## The panel detaches from the driver board
The panel plugs into a 24-pin 0.5 mm flip-lock FPC socket (J3) — connected, not
soldered. Panel alone is 0.78 mm thick. Not documented whether it's also
adhesive-bonded in production; the wiki warns the FPC tail is fragile.
[Schematic](https://files.waveshare.com/upload/8/8e/3.7inch_e-Paper_Schematic.pdf)

## Colour depth and waveforms — read the driver, not the wiki
Verified by reading `epd3in7.py` on master, not inferred.

**`1Gray` and `4Gray` are bit depths**, and the naming misleads:
- **1Gray** — one bit per pixel. Black or white. The "1" is bits, not greys.
- **4Gray** — two bits per pixel. Four levels: black, dark grey, light grey, white.

**A LUT is the waveform** — the voltage sequence that flips the particles. Four
are defined in the file, trading speed against cleanliness:

| LUT | Speed | Used by |
|---|---|---|
| `lut_4Gray_GC` | slow, ~3 s, four greys | `display_4Gray`, `Clear(mode=0)` |
| `lut_1Gray_GC` | mono full refresh | **defined but never called** |
| `lut_1Gray_DU` | direct update, only changed pixels | `Clear(mode=1)` |
| `lut_1Gray_A2` | fastest mono | `display_1Gray` |

**`display_1Gray` is already the fast refresh.** It loads `lut_1Gray_A2`, which is
the ~0.3 s waveform. There is no method called "partial" in the Python driver, but
the behaviour is there under another name — `init(1)` then `display_1Gray()`.

What it does *not* do is limit the update to a rectangle: it writes the whole
480 × 280 frame every time. That costs almost nothing, though — 16,800 bytes over
SPI is milliseconds, and the refresh time is the panel's physics, not the
transfer. A windowed update would gain little.

`lut_1Gray_GC` sitting unused is worth a try: the periodic cleaning refresh that
A2 requires could be a mono full refresh rather than the 3 s four-grey one.

## Refresh timing, decoded from the waveform tables
The four LUTs in `epd3in7.py` are 105 bytes each, laid out per SSD1677 datasheet
section 6.7: 50 bytes of VS (ten groups x four phases x two bits, five LUTs),
50 bytes of TP/RP (phase length in frames, repeat count per group), 5 bytes of
frame rate. Summing frames and dividing by **25 Hz** reproduces Waveshare's own
published figures exactly, which is what pins the frame rate down — the datasheet
leaves those five bytes undocumented.

| LUT | Frames | Time | Inversions |
|---|---|---|---|
| `lut_4Gray_GC` | 76 | 3.04 s | black 0.56 s, 3x (white 0.32 / black 0.32), 0.56 s settle |
| `lut_1Gray_GC` | 38 | 1.52 s | one, 0.6 s — unused by the driver |
| `lut_1Gray_DU` | 28 | 1.12 s | none |
| `lut_1Gray_A2` | 8 | 0.32 s | none |

Waveshare's own wiki publishes the two-plane encoding, which matches what the
emulator decodes: `0x24`/`0x26` bits of `00` are black, `10` dark grey, `01`
light grey, `11` white.

**A2 does not drive unchanged pixels at all.** Its VS entries are hold for every
transition except black-going and white-going, and it never inverts. Nothing
re-balances what the previous frame left, which is the mechanism behind the
"full refresh every few partials" rule — that rule is about charge balance, not
about wear.

## The "180 s" rule — read the paragraph it sits in
Fetched verbatim from the wiki. The Precautions block runs, in this order:

> For e-Paper displays that support partial refresh, please note that you cannot
> refresh them with the partial refresh mode all the time. After refreshing
> partially several times, you need to fully refresh EPD once.

> Note that the screen cannot be powered on for a long time. When the screen is
> not refreshed, please set the screen to sleep mode or power off it. Otherwise,
> the screen will remain in a high voltage state for a long time, which will
> damage the e-Paper and cannot be repaired!

> When using the e-Paper display, it is recommended that the refresh interval is
> at least 180s, and refresh at least once every 24 hours.

Two things follow. The sentence lives in a passage about **leaving the panel
powered and idle**, not about interaction. And the same block, three sentences
earlier, tells you to partial-refresh several times between full refreshes — so
180 s cannot be meant as a floor on every refresh, or the feature it just
described would be unusable.

The identical sentence is present word for word on the 2.13", 4.2" and 7.5"
wikis. It is boilerplate pasted across the range, not a figure for this panel.

**Unconfirmed:** whether it governs full refreshes specifically. Waveshare never
says, and no measurement behind the number was found.

## Notes
- Wiki warns: after several partial refreshes, run a full refresh or the panel
  degrades permanently.
- Pi 5 works: the library moved to `lgpio` (C) and `gpiozero` + `spidev` (Python).
  Waveshare's own pages never name the Pi 5 explicitly, but resellers list it
  and the libraries are RP1-safe. Known papercut on Bookworm:
  `lgpio.error: 'GPIO busy'` — https://github.com/waveshareteam/e-Paper/issues/335

## Unknown
- Whether the panel is also adhesive-bonded to the driver board in production,
  or held only by the FPC socket.

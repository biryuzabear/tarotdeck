# Waveshare 3.7" e-Paper HAT

| | |
|---|---|
| SKU | Waveshare **18057** |
| Resolution | 480 × 280, 0.169 mm dot pitch |
| Colors | black/white + 4 grey levels |
| Driver IC | **SSD1677** — [datasheet](https://files.waveshare.com/upload/2/2a/SSD1677_1.0.pdf) |
| Interface | SPI |
| Voltage | 3.3 V / 5 V (onboard level translator); wiki says 5 V for power and signal |
| Refresh | full **3 s**, partial **0.3 s** |
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
| PWR | 18 | 12 |

Plus 3.3 V and GND.

## Open: how to connect it
Seated as a HAT it covers the 40-pin header, so nothing else can reach it. Three
ways out, none chosen:

1. **Leave it on the header.** The boards sit tightly and well as they are.
   Unclear whether changing that is worth it.
2. **Solder to the underside of the Pi.** Works, but means soldering on the Pi
   itself — not appealing.
3. **A USB expansion / breakout.** Would mean buying something — not appealing.

## Not necessarily a HAT
An 8-pin cable is included, so the panel can be wired **off the header** rather
than seated on it. Two things follow: the 40-pin header stays free for everything
else, and the display can be placed independently of the board inside the
enclosure. The wiki gives full 8-pin wiring tables for Pi, Jetson, STM32, Arduino.

⚠️ Waveshare contradicts itself on the connector: the package list says "PH2.0
20cm 8Pin", the wiki FAQ says the 8-pin connectors on e-Paper HATs are 2.54 mm
pitch. Measure before cutting a hole for it.

## The panel detaches from the driver board
The panel plugs into a 24-pin 0.5 mm flip-lock FPC socket (J3) — connected, not
soldered. Panel alone is 0.78 mm thick. Not documented whether it's also
adhesive-bonded in production; the wiki warns the FPC tail is fragile.
[Schematic](https://files.waveshare.com/upload/8/8e/3.7inch_e-Paper_Schematic.pdf)

## Notes
- **Partial refresh is mono only.** The C driver has `EPD_3IN7_1Gray_Display_Part`
  but no 4-grey partial equivalent; the Python driver has no partial method at
  all — only `init(mode)`, `display_4Gray`, `display_1Gray`, `Clear`, `sleep`.
- Wiki warns: after several partial refreshes, run a full refresh or the panel
  degrades permanently.
- Pi 5 works: the library moved to `lgpio` (C) and `gpiozero` + `spidev` (Python).
  Waveshare's own pages never name the Pi 5 explicitly, but resellers list it
  and the libraries are RP1-safe. Known papercut on Bookworm:
  `lgpio.error: 'GPIO busy'` — https://github.com/waveshareteam/e-Paper/issues/335

## Unknown
- Whether the HAT passes GPIO through for other devices — no source says either way.

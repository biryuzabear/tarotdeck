# Pinout

The 40-pin header, by BCM number and by board pin number. Nothing here has been
wired yet.

The e-Paper goes on **wires, not as a HAT** — its included 8-pin cable reaches
individual header pins. That is what leaves room for everything else.

Header reference to keep open while wiring:
https://www.raspberrypi.com/documentation/computers/images/GPIO-Pinout-Diagram-2.png

Every pin below is given by **physical header number** first — pin 1 is the
corner nearest the SD card, odd numbers down the inner row, even down the outer.
Then its GPIO number, which is the name software uses. Then the second name it
carries when a built-in peripheral is switched on. Those second names are
explained in [the glossary](#the-second-names).

## The second names

Most of the 28 signal pins are just switches the processor can flip on and off.
But a handful are also wired to dedicated circuits inside the chip, and when such
a circuit is enabled, that pin stops being general-purpose and belongs to it.
That is why the same pin has two names.

**SPI** — four wires that move data fast to one chip at a time. `MOSI` carries
the data, `SCLK` is the clock that paces it, `CE0`/`CE1` pick which chip is
listening, `MISO` is the reply line. The e-Paper uses it and needs `MOSI`, `SCLK`
and `CE0` on their own pins — those three cannot be moved.

**I²C** — two wires, `SDA` for data and `SCL` for the clock, shared by many slow
chips at once. Each chip answers to its own address number. PiSugar sits here.

**UART** — two wires, `TXD` out and `RXD` in, the plainest serial link there is.
Kept free so a console cable can show boot messages when nothing else works.

**PWM** — a circuit that switches a pin on and off at a precise rate without the
processor's involvement. Feed a buzzer with it and the rate is the pitch. Four
pins have it; anywhere else the switching is done in software and wobbles.

**PCM** (also called I²S) — four wires for digital audio, the interface a
microphone-on-pins would use. We went USB instead, so these pins stay ordinary —
which is what frees GPIO 21 for the LEDs.

**ID_SD / ID_SC** — a tiny I²C bus the Pi reads at boot to identify an attached
HAT. Not ours to use.

## Test pinout — wire this

Provisional. Every control pin except the buzzer is an arbitrary free choice and
can move later; the point is to have something to build against.

### e-Paper — 8 wires

| Cable | Header pin | GPIO | Also known as | |
|---|---|---|---|---|
| VCC | **17** | 3.3 V rail | — | not pin 1 — see below |
| GND | 20 | GND | — | |
| DIN | 19 | GPIO 10 | **SPI0 MOSI** | fixed |
| CLK | 23 | GPIO 11 | **SPI0 SCLK** | fixed |
| CS | 24 | GPIO 8 | **SPI0 CE0** | fixed |
| DC | 22 | GPIO 25 | plain GPIO | movable |
| RST | 11 | GPIO 17 | plain GPIO | movable |
| BUSY | 18 | GPIO 24 | plain GPIO | movable |

### Controls

| What | Wire | Header pin | GPIO | Also known as |
|---|---|---|---|---|
| Encoder — right gear | A | 29 | GPIO 5 | plain GPIO |
| | B | 31 | GPIO 6 | plain GPIO |
| | C (common) | 30 | GND | — |
| Left gear, tick left | switch | 15 | GPIO 22 | plain GPIO |
| Left gear, tick right | switch | 16 | GPIO 23 | plain GPIO |
| | common | 14 | GND | — |
| Touch pad — dictation | SIG | 37 | GPIO 26 | plain GPIO |
| | VCC | 1 | 3.3 V rail | — |
| | GND | 34 | GND | — |
| WS2812 chain | DIN | 40 | GPIO 21 | PCM DOUT — unused, see below |
| | +5 V | 4 | 5 V rail | — |
| | GND | 39 | GND | — |
| Buzzer | + | 33 | GPIO 13 | **hardware PWM** — required |
| | − | 25 | GND | — |

Grounds are assigned one wire per pin only so nothing has to be doubled up on a
single Dupont socket. Electrically they are all the same net. Pins 6 and 9 stay
spare.

The encoder's push-button is **not used** — decided. SW stays unconnected.

## Why these pins

Only **DIN, CLK and CS** are truly fixed — they are SPI0's own pins. **RST, DC
and BUSY** are ordinary GPIOs written as numbers in `epdconfig.py` and can be
moved anywhere by editing three lines.

The buzzer must sit on a hardware PWM channel — **GPIO 12, 13, 18 or 19**, i.e.
header pins 32, 33, 12, 35 — otherwise the tone jitters under load. Software PWM
works but sounds it.

The LED pin is genuinely free choice: the `ws2812-pio` overlay accepts any
bank-0 GPIO (0–27) and uses RP1's PIO block, which collides with neither SPI0
nor the PWM channels. See [rgb-leds.md](parts/rgb-leds.md).

**3.3 V on pin 17, not pin 1.** Both are the same rail, but pin 1 sits next to
pin 2, which is 5 V. Pin 17's neighbours are pin 15 and pin 19 — a slip there
costs a signal, not the board. The touch pad takes pin 1 because its module has
an onboard regulator range of 2–5.5 V and survives the mistake; the e-Paper is
the one to protect.

**GPIO 18 is not needed.** `epdconfig.py` drives a PWR pin there, but the 3.7"
board has no such net — the code belongs to a different Waveshare product. Delete
those lines and the pin is ours. Details in
[the part file](parts/epaper-waveshare-3in7.md).

SPI0 goes entirely to the display. A second SPI device would have to use CE1 —
header pin 26, GPIO 7.

## e-Paper wiring rules

**VCC goes to 3.3 V, and that is not optional.** The board's TXS0108E level
translator takes its B-side reference from whatever is on the cable's VCC pin.
Supply voltage and logic voltage must match, and the Pi drives 3.3 V. The wiki's
"5 V is required for power and signal" line is boilerplate copied across models;
newer Waveshare products reword it as "the IO level voltage should be the same as
the supply voltage", which is the actual rule. The panel itself never sees VCC —
it sits behind an RT9193-33 regulator and always gets 3.3 V.

⚠️ **Never seat the board on the header and run the cable at the same time.**
H1 pin 1 and header pins 2/4 are the same copper (net `RPI_5V`). Doing both ties
the Pi's 3.3 V rail to its 5 V rail. One connection method or the other.

**Go by the board silkscreen, not by wire colour.** The connector is keyed and
the signals are printed next to it, so the ribbon order is fixed — count from
VCC. Waveshare publishes no colour table at all: checked against the raw wikitext
of the 3.7" template and ~20 other e-Paper wikis, and against the driver HAT
manual. Two incompatible conventions circulate in blogs, and Waveshare's own
boilerplate says photo colours are "for reference only".

Our own cable, read off the board's silkscreen — good for this cable only:

| Signal | Wire | Header pin |
|---|---|---|
| VCC | grey | 17 |
| GND | brown | 20 |
| DIN | blue | 19 |
| CLK | yellow | 23 |
| CS | orange | 24 |
| DC | green | 22 |
| RST | white | 11 |
| BUSY | purple | 18 |

**Connector order on the board**, left to right, silkscreened, confirmed against
the schematic's H1 netlist:

`1 VCC · 2 GND · 3 DIN · 4 CLK · 5 CS · 6 DC · 7 RST · 8 BUSY`

There is no printed "1" — VCC is pin 1. The board-end connector is a shrouded,
keyed JST-style housing and **cannot be inserted reversed**. All the risk is at
the Pi end, where the cable ends in eight individual Dupont sockets.

**Check the `BS` jumper** next to the connector: `0` = 4-line SPI, which is what
every Waveshare demo assumes. `1` = 3-line SPI. Leave it at 0.

Photos to have open:
- board back, silkscreen legible — https://www.waveshare.com/media/catalog/product/3/_/3.7inch-e-paper-hat-3.jpg
- same, angled — https://www.waveshare.com/media/catalog/product/3/_/3.7inch-e-paper-hat-4.jpg
- someone else's build on loose wires (2.13", same cable) — https://janrothen.github.io/btc-ticker/images/assembled.png

## How not to destroy the panel

Sources and detail in [the part file](parts/epaper-waveshare-3in7.md).

- **Never hot-plug.** Power the Pi down before touching either the 8-pin cable or
  the panel's FPC tail. Waveshare states this flatly, without qualification.
- **`sleep()` after every refresh.** This is the best-documented killer: an idle
  powered panel stays under high voltage, and the wiki says the resulting damage
  cannot be repaired. Clear the screen before the deck is put away for a while.
- **Refresh no more often than every 180 s, and at least once every 24 h.**
  Vendor guidance, no published measurement behind it.
- **Full refresh every ≤5 partial refreshes.** Also unrepairable if ignored.
- **Watch RST timing.** On this board RST also gates the power switch (Q32 → Q31)
  — hold it low too long and the board browns out mid-refresh instead of
  resetting. A Python `sleep()`-timed 2 ms pulse is not guaranteed under load.
- **Strain-relieve the FPC tail once, then never flex it.** Never bend it toward
  the front of the panel.
- 0–50 °C, 35–65 % RH as the design envelope. No direct sunlight — UV dries the
  particles out irreversibly.

## Free after that
| Header pin | GPIO | Also known as |
|---|---|---|
| 7 | GPIO 4 | plain GPIO |
| 12 | GPIO 18 | hardware PWM · PCM CLK |
| 13 | GPIO 27 | plain GPIO |
| 32 | GPIO 12 | hardware PWM |
| 35 | GPIO 19 | hardware PWM · PCM FS |
| 36 | GPIO 16 | plain GPIO |
| 38 | GPIO 20 | PCM DIN |

Three are hardware PWM, so more buzzer voices remain possible.

## Deliberately avoided
| Header pin | GPIO | Why |
|---|---|---|
| 27, 28 | GPIO 0, 1 | ID_SD/ID_SC, reserved for HAT EEPROM |
| 8, 10 | GPIO 14, 15 | UART — wanted for a serial console when the Pi won't boot |
| 21 | GPIO 9 | MISO; the display doesn't use it, but leave SPI0 intact |

## The USB microphone earns this map
An I²S microphone on pins would take **GPIO 18, 19, 20, 21** as one block: the
display's PWR line, two of the four PWM channels, and the pin the LEDs are on.
Going USB costs a port and keeps the header roomy.

The left gear is **two plain momentary buttons**, one per direction — not an
encoder. Internal pull-ups, so no external resistors.

## I²C
PiSugar only — header pins 3 and 5 (GPIO 2 SDA, GPIO 3 SCL), addresses 0x57
(power MCU) and 0x68 (RTC, a DS3231
emulated by the same MCU). It occupies no GPIO beyond those two; its buttons are
read over I²C, not through an interrupt line. With the IMU dropped, nothing else
is on the bus.

## Power switch — decided
A button soldered on, wired either to PiSugar or to the Pi's own power button
pads. Either way it costs no GPIO, so header pin 5 stays PiSugar's alone.

## Open
- Whether the WS2812 chain accepts 3.3 V data while powered from 5 V, or needs a
  level shifter. Marginal by datasheet, usually works in practice — untested here.

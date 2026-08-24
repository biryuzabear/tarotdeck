# PiSugar 3 Plus

The one PiSugar model that officially supports the Pi 5.

"Portable" in marketplace titles is padding — there is no Portable variant.
PiSugar's own shop sells a single PiSugar 3 Plus with no options.

Energy budget and runtime: [../POWER.md](../POWER.md).

| | |
|---|---|
| Capacity | 5000 mAh |
| Output | 5 V / 3 A max |
| PCB | 65 × 56 mm |
| Connection | pogo pins from underneath — GPIO header stays free |
| I²C | `0x57` / `0x68`, address customizable |
| RTC | MCU-emulated, works with `hwclock`; scheduled wake, soft power-off, watchdog |
| Product page | https://www.pisugar.com/products/pisugar-3-plus-raspberry-pi-ups |
| Docs | https://docs.pisugar.com/ |

## On our board: SDA and SCL do not reach — measured 2026-08-25
The pogo pins carry power but not I²C. Continuity between each header pin and
the PiSugar, with the boards screwed together:

| Header pin | Signal | Contact |
|---|---|---|
| 2, 4 | 5 V | yes |
| 6 | GND | yes |
| 9 | GND | yes |
| **3** | **SDA (GPIO 2)** | **no** |
| **5** | **SCL (GPIO 3)** | **no** |

So the deck runs off the battery — Pi 5 and the e-paper both, `EXT5V = 5.05 V`,
`throttled=0x0` — while `i2cdetect -y 1` stays empty. One cause, both symptoms.

Pressing the boards together by hand does not bring 3 and 5 back, and pin 9 sits
in the same odd row as they do, so it is not a sideways shift. It is local: on
the Pi 5 the header pins barely protrude underneath, and the contact point is
the solder cap itself. Where that cap is flat the spring cannot reach.

PiSugar's own fix is to add solder to the pin tips. Untried. The alternative,
also untried, is to jumper `SDAT`/`SSCL` from the 2.54 mm extension header on
the PiSugar to header pins 3 and 5 from above, leaving the pogo pins to carry
power only.

**What this costs while unfixed:** battery percentage, RTC, soft power-off,
scheduled wake, watchdog — everything `pisugar-server` provides. The UPS itself
is unaffected. `hardware/PINOUT.md` gives pins 3 and 5 to PiSugar alone, so
nothing else is blocked.

## There is no driver
`pisugar-power-manager` is a userspace daemon over I²C, not a kernel module.
The board powers the Pi with no software at all. Installing it before `0x57`
appears on the bus is pointless — it has nothing to talk to.

```
wget -O pisugar-power-manager.sh https://cdn.pisugar.com/release/pisugar-power-manager.sh
bash pisugar-power-manager.sh -c release
```

Select **PiSugar3** at the prompt — Air, 3 and 3 Plus all use that option. WebUI
lands on port 8421. Their README lists support only up to pi4 on 32-bit; Pi 5
and trixie are not mentioned either way.

## Waking it up
Not obvious, and easy to get wrong:
- The **small round button is a reset**, not a power button — their docs say so
  explicitly. On PiSugar 2 it powered the board on; on 3 it does not.
- Power-on is **short press, then click & hold** until the LEDs count 1 to 4.
  This is the anti-mistaken-touch feature, on by default.
- The green LED never indicates "full" — it blinks in a loop the whole time
  external power is connected. Known firmware limitation.
- Ours arrived flat enough that the Pi would not start. Charging over the
  PiSugar's own Type-C fixed it; the Pi's power input does not charge the board.

## Two caveats on Pi 5
- Output is **5 V / 3 A**, under the Pi 5's 5 V / 5 A spec. Users report
  undervoltage warnings once the battery drops off full, and one report of random
  shutdowns below ~50 % on a heavily loaded Pi 5.
- **Mechanical conflict with the Active Cooler** — its mounting clips protrude
  through the underside of the board and can foul the PiSugar mount.
  https://docs.pisugar.com/docs/product-wiki/battery/faq

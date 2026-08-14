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

## Two caveats on Pi 5
- Output is **5 V / 3 A**, under the Pi 5's 5 V / 5 A spec. Users report
  undervoltage warnings once the battery drops off full, and one report of random
  shutdowns below ~50 % on a heavily loaded Pi 5.
- **Mechanical conflict with the Active Cooler** — its mounting clips protrude
  through the underside of the board and can foul the PiSugar mount.
  https://docs.pisugar.com/docs/product-wiki/battery/faq

# USB microphone — "SunFounder M-305"

Voice input.

**The model number doesn't fully resolve.** No SunFounder listing uses "M-305".
Two candidates:

1. **SunFounder USB 2.0 Mini Microphone**, SKU `CN0029`, ASIN B01KLRBHGM —
   SunFounder's only mini USB mic. https://www.sunfounder.com/products/mini-usb-microphone
2. **MI-305 Mini Microphone Dongle** — a widely rebadged generic USB dongle
   (SparkFun, MIDTeks, and others) that looks essentially identical. If the unit
   is physically labelled M-305/MI-305 it is probably this, not SunFounder-branded.

Likely the same OEM part either way.

## Specs (for the SunFounder CN0029)
| | |
|---|---|
| Type | omnidirectional, noise-cancelling |
| Size | 22 × 18 × 7 mm |
| Frequency response | 100 Hz – 16 kHz (analog capsule, not sample rate) |
| Sensitivity | −47 dBV/Pa ±4 dB |
| Drivers | none needed on Linux / Raspberry Pi OS; enumerates as `card 1, device 0` |
| Pi tutorial | http://wiki.sunfounder.cc/index.php?title=To_use_USB_mini_microphone_on_Raspbian |

## Unconfirmed
- Whether it declares USB Audio Class 1.0 or 2.0 — vendor never says
- **Native sample rates.** SunFounder's own tutorial uses `arecord -D plughw:1,0`,
  which resamples in software and proves nothing. To find out for real:
  `arecord -D hw:1,0 -f S16_LE -r 48000` — note `hw`, not `plughw`.

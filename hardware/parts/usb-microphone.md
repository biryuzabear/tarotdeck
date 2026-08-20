# USB microphone — "SunFounder M-305"

Voice input.

**Identified: SunFounder USB 2.0 Mini Microphone**, SKU `CN0029`, ASIN B01KLRBHGM —
SunFounder's only mini USB mic. https://www.sunfounder.com/products/mini-usb-microphone

Confirmed by the owner. The unit's "M-305" marking does not appear in any
SunFounder listing; the visually identical MI-305 Mini Microphone Dongle,
rebadged by SparkFun, MIDTeks and others, is almost certainly the same OEM
part sold unbranded.

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

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

## It arrives with the capture gain at zero
Measured 2026-08-25. The dongle enumerates on its own, no driver, but ALSA's
`Mic` capture control defaults to **0 of 16** — and a recording then comes out
the right length, the right format, and digitally silent. Easy to read as a dead
capsule.

```
amixer -c 0 sset Mic 16 unmute          # 100%, +23.81 dB
amixer -c 0 sset "Auto Gain Control" off
```

Only two controls exist: `Mic` and `Auto Gain Control`. AGC is off here so the
level stays flat for Whisper.

At full gain, speech from ~20 cm reads: floor ~100 RMS, words 500–1000, peaks
~5500 of 32768, no clipping. Words separate from pauses by about 10x, which is
what matters for endpointing. Further than that and it hears the room, not you —
the capsule is −47 dBV/Pa.

On this unit it comes up as **`card 0`**, not `card 1` as the part notes below
say — the Pi's HDMI outputs land on 1 and 2.

## Unconfirmed
- Whether it declares USB Audio Class 1.0 or 2.0 — vendor never says
- **Native sample rates.** SunFounder's own tutorial uses `arecord -D plughw:1,0`,
  which resamples in software and proves nothing. To find out for real:
  `arecord -D hw:1,0 -f S16_LE -r 48000` — note `hw`, not `plughw`.

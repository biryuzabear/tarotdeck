# Round RGB LEDs — WS2812B

Addressable, single data line. Several of them, loose/discrete, round form.
(The 12-LED ring is a separate part — [led-ring-hs-f12a.md](led-ring-hs-f12a.md).)

| | |
|---|---|
| Chip | WS2812B |
| Protocol | single-wire, GRB order, 800 kHz |
| Voltage | 5 V |
| Form | round modules on board, **10 × 10 mm each** |
| Quantity | plenty on hand; **12** — six a side, mirrored |

The level-shifter question is covered in the ring's file — same protocol, and
they chain onto one data line.

## Driving them on Pi 5 — use the `ws2812-pio` overlay
RP1 killed the old `rpi_ws281x` DMA/PWM path for good: PyPI is frozen at 5.0.0
(2023) and doesn't know Pi 5 board revisions, upstream master still has no
support, and [issue #528](https://github.com/jgarff/rpi_ws281x/issues/528) has
been open since 2023. Don't go there.

The replacement is in-kernel and official, added December 2024, present on both
Bookworm and Trixie. One line in `/boot/firmware/config.txt`:

```
dtoverlay=ws2812-pio,gpio=21,num_leds=12
```

- **Any bank-0 GPIO, 0–27** — arbitrary choice, no pin whitelist. Default is 4.
- Uses RP1's **PIO block, not PWM and not SPI**, so it collides with neither the
  display on SPI0 nor the buzzer on a hardware PWM channel. The only scarce
  resource is PIO itself: 4 state machines, 4 strips maximum. We need one.
- Twelve draw 0.72 A at full white; at the brightness used, about 0.14 A.
- Gamma correction and global brightness are applied in the kernel.

It appears as a plain character device, `/dev/leds0`. No library, just file
writes — 4 bytes per LED, `R, G, B, W`:

```python
import struct
px = [(255, 0, 0, 0), (0, 255, 0, 0)]
buf = b"".join(struct.pack("<4B", *p) for p in px)
open("/dev/leds0", "wb").write(buf)
```

Two traps in the write semantics: a **1-byte write at offset 0 sets brightness**,
it does not set pixel 0; and a **short write blanks every LED past its end** and
defers the update 50 ms. Always write the full `num_leds * 4`.

The device comes up root-owned `0600` — needs a udev rule matching `leds*` to run
unprivileged.

**The Adafruit route is a different thing.** `Adafruit-Blinka-Raspberry-Pi5-Neopixel`
talks to `/dev/pio0` via `piolib` and competes for the same state machines — pick
one or the other, not both. Plain `adafruit-circuitpython-neopixel` doesn't work
on Pi 5 at all.

Sources: [overlay README](https://github.com/raspberrypi/linux/blob/rpi-6.12.y/arch/arm/boot/dts/overlays/README) ·
[driver source](https://github.com/raspberrypi/linux/blob/rpi-6.12.y/drivers/misc/ws2812-pio-rp1.c)

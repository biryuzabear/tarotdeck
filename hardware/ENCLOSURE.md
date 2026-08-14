# Enclosure

## Size constraint
**76 × 41 × 126 mm** — the whole device must fit inside this.

This is the size of a tarot deck in its box. The cyberdeck is meant to be exactly
that: a deck-sized object.

A trial assembly has been done and it fits. Exact dimensions still worth having
for designing the case properly.

## Part dimensions
| Part | Size | Source |
|---|---|---|
| Raspberry Pi 5 board | 85 × 56 mm | [mechanical drawing](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf) |
| — mounting holes | ø2.7 mm, 58 × 49 mm spacing, 3.5 mm from edges | same |
| — USB-A / Ethernet overhang past PCB edge | 3 mm | same |
| Active Cooler | 63.5 × 42.5 mm, 13.7 mm tall incl. push-pins | [drawing](https://datasheets.raspberrypi.com/cooling/raspberry-pi-active-cooler-mechanical-drawing.pdf) |
| — mount-hole spacing | 30 × 30 mm | same |
| e-Paper driver board | 58 × 96.5 mm | [wiki](https://www.waveshare.com/wiki/3.7inch_e-Paper_HAT_Manual) |
| e-Paper panel alone | 93.3 × 54.9 × **0.78 mm** | [panel spec](https://files.waveshare.com/upload/7/71/3.7inch_e-Paper_Specification.pdf) |
| — active area | 81.12 × 47.32 mm | same |
| — FPC tail | 15.55 × 13.8 mm, 24-pin, 0.5 mm pitch | same |
| PiSugar 3 Plus | 65 × 56 mm | [docs](https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series) |
| LED ring HS-F12A | 40 mm diameter (49 mm with header tab) | vendor |
| OLED `GM009605v4.3` | 27 × 27 × 4.1 mm | — |
| USB mic dongle | 22 × 18 × 7 mm | — |
| Rotary encoder body | ~12 × 12 mm | — |

## Footprint
Both large boards only fit along the **126 mm** axis:
- Pi 5: 85 into 126, 56 into 76
- e-Paper driver board: 96.5 into 126, 58 into 76

Neither can stand on edge — 58 mm exceeds the 41 mm face.

**The driver board sets the device's width at 58 mm.** It's wider than the Pi
(56 mm) and wider than the panel it sits behind (54.9 mm), so the panel being
narrower buys no space. Against the 76 mm envelope: 18 mm spare across the width,
~29 mm spare along the length.

## What's actually free
The central block is **58 × 96.5 × 36.8 mm** and it is full — no room inside it,
none above it. Everything else lives in what's left around it.

| Space | Size | Notes |
|---|---|---|
| End pocket | **~29 × 76 × 41 mm** | full width, full depth. The only volume with real room |
| Side strips | 9 × 96.5 × 41 mm, ×2 | narrow; fine for LEDs, too narrow for an encoder body |
| Over the block | 4.2 mm | that's the cover, not usable space |

What fits in the end pocket: OLED module (27 × 27 × 4.1), encoder body (~12 × 12),
buttons, mic grille. Tight, but it is a real pocket.

In the upside-down orientation this pocket lands at the top — where the mic wants
to be anyway.

## The vertical stack
Bottom to top: **PiSugar → Pi 5 → e-Paper board**.

**Measured: 36.8 mm** for the whole sandwich. Against the 41 mm depth that leaves
**4.2 mm** for everything else — bottom shell, top cover, and whatever goes over
the protruding screen. Split across two faces, so roughly 2 mm a side.

This stack is already as tight as it goes, and there is nothing to reclaim in it:
- the boards themselves are flat and sit as close as they can
- the vertical budget is set by the **height of the USB 3.0 ports** — that's what
  the Pi runs into, not the PCBs
- the e-Paper board already rests directly on top of those ports
- the PiSugar underneath likewise uses its space efficiently

So the pie barely fits, and the screen will most likely **protrude** — covered
from above by something thin and neat rather than sunk flush.

Everything else (LEDs, OLED, encoder, buttons, buzzer, mic) goes out to the sides.

**Open:** whether the Active Cooler clears a HAT seated on the 40-pin header.
The cooler is already bought, so if it doesn't fit, it doesn't fit.

Note: the e-paper panel does detach from its driver board — 24-pin 0.5 mm
flip-lock FPC socket, panel alone 0.78 mm thick. That buys nothing vertically
given the stack above, but it's there if the layout ever wants it. The wiki warns
the FPC tail is fragile.

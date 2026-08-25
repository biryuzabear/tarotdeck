# Capacitive touch sensor `HW-139 v1.0`

Chip: **TTP223-BA6**, SOT-23-6. `HW-139` is the board marking; the sibling
`HW-138` is the 4-channel TTP224.

| | |
|---|---|
| Voltage | 2.0–5.5 V — **run it from 3.3 V** |
| Output | **push-pull** CMOS, not open drain |
| Idle current | ~1.5 µA (bare IC) |
| Response | 220 ms in low-power mode; switches to 60 ms fast mode on touch and stays fast ~12 s |
| Board pins | VCC / GND / SIG |
| Datasheet | https://components101.com/sites/default/files/component_datasheet/TTP223-Datasheet.pdf |

**Do not power it from 5 V** — the output is push-pull, so it would drive 5 V
into a Pi GPIO.

Chip marking to check with a loupe: `223B` = TTP223-BA6. `223NB` = TTP223N-BA6,
which the datasheet itself calls more sensitive but **less stable**.

## Mode — nothing to solder
Default as shipped is **momentary, idle low, high on touch**. That's what this
project wants. The A/B jumpers only exist to select the other combinations:

| B (TOG) | A (AHLB) | Behaviour |
|---|---|---|
| open | open | momentary, active high — **default** |
| open | closed | momentary, active low |
| closed | open | toggle, starts off |
| closed | closed | toggle, starts on |

## Sensing through the panel
No maximum thickness is published. Measured by users:
- **~3 mm** through material as shipped
- **~7 mm** with the sensitivity capacitor removed
- 4 mm glass has been made to work; metal blocks it completely

The `Cs` capacitor runs from the sense pad to ground, 0–50 pF. **No capacitor =
maximum sensitivity**; adding capacitance only reduces it. Some boards ship with
it populated — removing it is what took one user from 3 mm to 7 mm.

A 2 mm wall is comfortably inside range — on paper.

### The test to run
Print a set of plain plates and see what the sensor actually reads through. Not a
question to settle from datasheets: everything published is other people's
material at other people's print settings.

- A ladder of thicknesses — 1, 1.5, 2, 2.5, 3, 4 mm
- Printed in **the filament and the settings the case will use**, solid, since
  infill voids change what the field sees
- Each plate held flat against the pad, then touched with a normal fingertip

What comes out of it: the thickest wall that still triggers reliably, and whether
2 mm has margin or is sitting on the edge. If it's marginal, removing `Cs` is the
next move before redesigning anything.

Worth doing on the same print as the chamfer test — both are small coupons and
both gate wall thickness.

## Two behaviours that matter here
**A held touch does not stay asserted, and ours gives up sooner than the
reports.** Measured on our unit, 2026-08-25: a sustained touch is dropped after
about **7.5 seconds**, repeatably, hold after hold. Not the 10–15 s users report.
Below that ceiling it is not steady either — holds collapsed at two or three
seconds while the finger never moved.

**Once it has let go, a resting finger is invisible.** Held for ten seconds, the
output drops at 7.5 and then nothing happens at all: no edges, no pulses, no
difference between a finger still on the pad and a finger lifted away. The
recalibration takes the finger into the baseline. So the state cannot be
recovered in software — there is no signal left to read. A brief flurry of
zero-length pulses does appear if the finger *shifts* slightly, which is what
misled us at first; a truly still finger produces silence.

**Hold-to-talk is therefore off the table** for this control, and not for lack
of a clever threshold. What the pad does do reliably, in every test, is register
short taps. So the interaction has to be tap-on / tap-off, with the toggle held
in our own code — which also means the `TOG` jumper stays unused.

**Through a plastic wall it still works** — confirmed by hand, thickness not yet
measured. The ladder test below still needs running.

**Don't touch it while the Pi boots.** There's a ~0.5 s stabilisation at power-on
during which the function is disabled, and the baseline it captures includes
whatever is touching the pad.

## Noise
The datasheet warns that an unstable supply causes false detections. Documented
fixes: a 100 nF decoupler right at the module's VCC/GND, short wires, keeping the
sense trace away from and never parallel to other traces, and a grounded plane
around the pad.

Coupling from a WS2812 data line specifically: no report found either way.

## On a Pi 5
Plain digital input. Output is push-pull, so no pull resistor:
```python
Button(pin, pull_up=None, active_state=True)
```
Some pages claim the TTP223 is open drain and needs a pull-up — that's true only
of the 16-pin TTP223-ASB, not the BA6 on this board.

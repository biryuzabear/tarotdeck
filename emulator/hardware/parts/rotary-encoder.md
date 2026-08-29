# Rotary encoder

Turns left and right with detents — one click each way — and presses in from
the top. An **EC11** on a breakout board (KY-040 style).

**Already tested and working** — wired up and read without trouble. Nothing to
solve here.

## What it is
Unlike a potentiometer, an encoder has **no end stops and no absolute position**.
It spins forever and only reports *change*: "one step clockwise". Software keeps
the running total. That's why it suits menus and scrolling — the knob and the
value can never disagree, and there's no travel limit to hit. (A pot would also
need an ADC, which the Pi doesn't have.)

**Detents** are the click-stops you feel. Each click = one step the user meant.

**Quadrature** is how direction is detected: two switch contacts, A and B, offset
by a quarter cycle. Turning one way they step `00 → 01 → 11 → 10`; the other way,
the same sequence backwards. Which one changes first is the direction.

## Pins
A bare EC11 has **5 pins**, physically split:
- **3 on one side** — encoder A, common C (middle), encoder B
- **2 on the other** — the push-button, an ordinary momentary switch, electrically
  unrelated to the encoder

A KY-040 breakout relabels these as GND, +, CLK (= A), DT (= B), SW (button).
The KY-040 *is* an EC11 on a carrier board — same part, same code.

The contacts are passive switches, not powered outputs, which is why pull-ups matter.

## Wiring and reading on a Pi 5
`gpiozero.RotaryEncoder` enables the Pi's **internal pull-ups** itself, so a bare
encoder needs no external resistors: A and B to two GPIOs, C to ground.

Debouncing is needed — mechanical contacts chatter. gpiozero's quadrature decoder
rejects illegal state transitions, which is more robust than a fixed `bounce_time`
(too aggressive a time filter drops fast turns).

```python
from gpiozero import RotaryEncoder, Button

enc = RotaryEncoder(a=17, b=18, max_steps=0)   # 0 = unbounded counter
btn = Button(27)                                # the button is a separate device
```

Docs: https://gpiozero.readthedocs.io/en/stable/api_input.html

## The breakout board is optional
The board carries `R1 R2 R3` on the underside — **pull-up resistors**, almost
certainly 10 kΩ (marking `103`). The classic KY-040 has two, on CLK and DT; a
third means SW is pulled up too, which is the better variant.

They pull the signal lines to VCC so the pins read a clean high when the contacts
are open. Without them a floating input reads garbage. That's their whole job —
they carry no logic.

**But `gpiozero` enables the Pi's own internal pull-ups**, on `RotaryEncoder` and
on `Button` both. So on this project the external ones are redundant, and the
carrier board is dead weight. The encoder can be desoldered from it — 5 pins —
and wired straight to the Pi: A and B to two GPIOs, C to ground, and the switch
between its own GPIO and ground.

Worth doing here, since the board is the space problem, not the encoder.

## Identifying the actual part
Bare EC11s are usually **unmarked**. Go by physical traits:
- 3 pins one side + 2 the other = encoder with button; 3 + 0 = no button
- body ~12 × 12 mm; shaft commonly 15 or 20 mm, knurled / D-shaft / flatted
  (determines which knobs fit)
- threaded bushing = panel mount

Detent count varies by variant (20/rev and 30/rev both exist), and some encoders
emit one quadrature cycle per detent while others emit two or four — which is why
code sometimes counts double. Determine empirically.

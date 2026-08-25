"""The deck's four controls. Real gpiozero devices either way.

On a Pi they sit on the header; on a desk they sit on mock pins that the keyboard
drives. The devices themselves, and everything below them, are the same objects in
both — which is the point of the emulator.
"""

import time

from gpiozero import Button, RotaryEncoder

import pins
from board import IS_PI
from mockpins import factory

encoder = RotaryEncoder(a=pins.ENCODER_A, b=pins.ENCODER_B, max_steps=0)
tick_left = Button(pins.BUTTON_LEFT, bounce_time=0.05)
tick_right = Button(pins.BUTTON_RIGHT, bounce_time=0.05)
touch = Button(pins.TOUCH, pull_up=None, active_state=True)

if not IS_PI:
    _a = factory.pin(pins.ENCODER_A)
    _b = factory.pin(pins.ENCODER_B)
    _touch = factory.pin(pins.TOUCH)

    def turn_cw():
        _a.drive_low()
        _b.drive_low()
        _a.drive_high()
        _b.drive_high()

    def turn_ccw():
        _b.drive_low()
        _a.drive_low()
        _b.drive_high()
        _a.drive_high()

    def press(button):
        factory.pin(button.pin.number).drive_low()

    def release(button):
        factory.pin(button.pin.number).drive_high()

    def touch_down():
        _touch.drive_high()

    def touch_up():
        _touch.drive_low()

    touch_up()


STEPS_PER_DETENT = 1
"""How many quadrature cycles the encoder emits per click of its detent.

gpiozero decodes quadrature, so a contact bounce that does not complete a valid
transition is already rejected before it ever becomes a step — that is the real
defence against false movement and it costs nothing. What it does not know is
whether this particular EC11 emits one cycle per detent or four, which is a
property of the part and is unmeasured until one is in hand.
"""

REVERSAL_GUARD = 0.06
"""A step in the opposite direction within this many seconds is discarded.

The bounce that survives quadrature decoding is the one that happens exactly at a
detent boundary, where the contacts settle across the transition and the decoder
sees a step and then its opposite. A real turn does not reverse in 60 ms; a bouncing
detent does. On the reading screen this matters more than anywhere else, because a
page turn there costs a 1.52 s full refresh, so a phantom step is not a nuisance but
a second and a half of the panel's life.
"""


class Dial:
    """Raw encoder steps in, deliberate moves out."""

    def __init__(self, steps_per_detent=STEPS_PER_DETENT, guard=REVERSAL_GUARD):
        self.steps_per_detent = max(1, steps_per_detent)
        self.guard = guard
        self.pending = 0
        self.last_direction = 0
        self.last_at = 0.0

    def step(self, delta, now=None):
        """Returns the move to act on, which is usually zero."""
        now = time.monotonic() if now is None else now
        direction = 1 if delta > 0 else -1
        if (
            self.last_direction
            and direction != self.last_direction
            and now - self.last_at < self.guard
        ):
            self.pending = 0
            self.last_at = now
            return 0
        if direction != self.last_direction:
            self.pending = 0
        self.last_direction = direction
        self.last_at = now
        self.pending += direction
        if abs(self.pending) >= self.steps_per_detent:
            self.pending = 0
            return direction
        return 0


QUIET_BEFORE_TAP = 1.0
"""Silence the pad must show before a touch counts as a deliberate tap.

Measured on our TTP223, 2026-08-25. A held touch is dropped after about 7.5 s, and
around a release the line chatters: re-assertions at 0.45-0.9 s, and pulses so short
both edges land in the same hundredth of a second. Deliberate taps never arrive
inside that window, so the rule is not a duration filter but a quiet one — any edge
at all, press or release, re-arms the timer, and a tap counts only when the line has
been still for this long beforehand. Chatter therefore silences itself.

The release edge is not used for anything. Once a tap is a tap, how long the finger
stays makes no difference, which is what puts the chip's 7.5 s ceiling out of reach.
"""


class Tap:
    """Pad edges in, deliberate taps out. The counterpart of `Dial`."""

    def __init__(self, quiet=QUIET_BEFORE_TAP):
        self.quiet = quiet
        self.last_edge = 0.0

    def edge(self, now=None):
        """Any edge. Re-arms the timer and never counts as a tap."""
        self.last_edge = time.monotonic() if now is None else now

    def pressed(self, now=None):
        """A press. True if it should be acted on."""
        now = time.monotonic() if now is None else now
        quiet = now - self.last_edge
        self.last_edge = now
        return quiet >= self.quiet

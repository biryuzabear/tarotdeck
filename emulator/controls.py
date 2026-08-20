"""Real gpiozero devices on fake pins, driven from the keyboard."""

from gpiozero import Button, RotaryEncoder

import pins
from mockpins import factory

encoder = RotaryEncoder(a=pins.ENCODER_A, b=pins.ENCODER_B, max_steps=0)
tick_left = Button(pins.BUTTON_LEFT)
tick_right = Button(pins.BUTTON_RIGHT)
touch = Button(pins.TOUCH, pull_up=None, active_state=True)

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

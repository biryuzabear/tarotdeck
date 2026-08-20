"""One mock pin factory, shared by everything that opens a gpiozero device."""

from gpiozero import Device
from gpiozero.pins.mock import MockFactory, MockPWMPin

factory = MockFactory(revision="c04170", pin_class=MockPWMPin)
Device.pin_factory = factory

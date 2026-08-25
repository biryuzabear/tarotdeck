"""One mock pin factory, shared by everything that opens a gpiozero device.

On a Pi there is no factory to install: gpiozero finds the real one itself, and
forcing a mock here would give the deck a set of pins that go nowhere.
"""

from board import IS_PI

factory = None

if not IS_PI:
    from gpiozero import Device
    from gpiozero.pins.mock import MockFactory, MockPWMPin

    factory = MockFactory(revision="c04170", pin_class=MockPWMPin)
    Device.pin_factory = factory

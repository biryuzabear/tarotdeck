"""The passive buzzer.

On the deck this is the whole story: `TonalBuzzer` drives GPIO 13 and the thing
makes a noise. On a desk the pin is a mock and nothing would be heard, so the same
tones are synthesised through the mixer as well — the pin logic stays genuine and
the sound is only for the person at the keyboard.
"""

import struct
import time

from gpiozero import TonalBuzzer

import mockpins  # noqa: F401  sets the pin factory
import pins
from board import IS_PI

try:
    import pygame
except ImportError:
    pygame = None

RATE = 22050
CLICK = 2200
CONFIRM = (1760, 2640)
BACK = (2640, 1760)
REVEAL = (1320, 1760, 2200)


_DEVICE = None


class Buzzer:
    def __init__(self):
        global _DEVICE
        if _DEVICE is None:
            _DEVICE = TonalBuzzer(pins.BUZZER, octaves=3)
        self.device = _DEVICE
        self.cache = {}
        self.level = "on"
        self.audible = False
        if pygame is not None and not IS_PI:
            try:
                pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=256)
                self.audible = True
            except pygame.error:
                self.audible = False

    LEVELS = ["on", "quiet", "off"]
    AMPLITUDE = {"on": 9000, "quiet": 2600, "off": 0}

    @property
    def muted(self):
        return self.level == "off"

    @muted.setter
    def muted(self, value):
        self.level = "off" if value else "on"

    def cycle(self):
        self.level = self.LEVELS[(self.LEVELS.index(self.level) + 1) % len(self.LEVELS)]
        return self.level

    def _tone(self, hz, ms):
        key = (hz, ms, self.level)
        if key not in self.cache:
            peak = self.AMPLITUDE[self.level]
            n = int(RATE * ms / 1000)
            period = RATE / hz
            samples = bytearray()
            for i in range(n):
                fade = min(1.0, min(i, n - i) / (RATE * 0.004))
                value = peak if (i % period) < period / 2 else -peak
                samples += struct.pack("<h", int(value * fade))
            self.cache[key] = pygame.mixer.Sound(buffer=bytes(samples))
        return self.cache[key]

    def play(self, hz, ms=26):
        if self.level == "off":
            return
        self.device.play(hz)
        if self.audible:
            self._tone(hz, ms).play()
        if IS_PI:
            # Nothing else is making this sound, so the pin has to be held for as
            # long as the note is meant to last.
            time.sleep(ms / 1000)
        self.device.stop()

    def sequence(self, notes, ms=26):
        for hz in notes:
            self.play(hz, ms)
            time.sleep(ms / 1000)

    def click(self):
        self.play(CLICK, 16)

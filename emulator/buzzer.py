"""The passive buzzer. Real gpiozero call on a mock pin, plus an audible tone."""

import math
import struct

import pygame
from gpiozero import TonalBuzzer

import mockpins  # noqa: F401  sets the pin factory
import pins

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
        self.device.stop()

    def sequence(self, notes, ms=26):
        for hz in notes:
            self.play(hz, ms)
            pygame.time.wait(ms)

    def click(self):
        self.play(CLICK, 16)

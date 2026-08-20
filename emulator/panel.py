"""The window: the device drawn to size, with an honest 280x480 in its cutout."""

import os
import queue
import time
from pathlib import Path

import pygame
from PIL import Image, ImageChops

import timings
import waveform
from face import Face

PANEL_W, PANEL_H = 280, 480
MARGIN = 20
INFO_W = 300

INK = {0x00: (38, 38, 36), 0x80: (104, 103, 96), 0xC0: (158, 156, 146), 0xFF: (223, 221, 212)}

_CHANNELS = [
    bytes(INK[min(INK, key=lambda k: abs(k - v))][c] for v in range(256)) for c in range(3)
]

frames = queue.Queue()


def on_frame(pixels, mode, steps, duration):
    frames.put((pixels, mode, steps, duration, time.monotonic()))


def _image(pixels):
    return Image.frombytes("L", (PANEL_W, PANEL_H), pixels)


def _surface(img):
    rgb = Image.merge("RGB", [img.point(channel) for channel in _CHANNELS])
    return pygame.image.fromstring(rgb.tobytes(), rgb.size, "RGB")


def _font(size, weight="Regular"):
    path = Path(__file__).parent / "fonts" / f"IBMPlexMono-{weight}.ttf"
    try:
        return pygame.font.Font(str(path), size)
    except (OSError, FileNotFoundError):
        return pygame.font.SysFont("menlo,monaco,couriernew", size)


def _scale():
    override = os.environ.get("TAROTDECK_SCALE")
    if override:
        return float(override)
    pygame.display.init()
    available = pygame.display.Info().current_h * 0.92 - MARGIN * 2
    return max(1.0, min(2.0, available / Face(1.0).size[1]))


class Window:
    def __init__(self, strip, title="tarotdeck"):
        pygame.init()
        pygame.display.set_caption(title)
        self.strip = strip
        self.face = Face(_scale())
        w = self.face.size[0] + INFO_W + MARGIN * 3
        h = self.face.size[1] + MARGIN * 2
        self.screen = pygame.display.set_mode((w, h))
        self.font = _font(13, "Text")
        self.small = _font(11)
        self.blank = _surface(Image.new("L", (PANEL_W, PANEL_H), 0xFF))
        self.current = self.blank
        self.shown = None
        self.ghost = Image.new("L", (PANEL_W, PANEL_H), 0)
        self.flash = None
        self.refreshes = 0
        self.partials = 0
        self.last_mode = "-"
        self.last_duration = 0.0
        self.touch_live = False

    def _accept(self):
        while True:
            try:
                pixels, mode, steps, duration, at = frames.get_nowait()
            except queue.Empty:
                return
            self.refreshes += 1
            self.last_mode = mode
            self.last_duration = duration
            image = _image(pixels)
            if steps:
                self.partials = 0
                self.ghost = Image.new("L", (PANEL_W, PANEL_H), 0)
                self.flash = (steps, at, image)
            else:
                self.partials += 1
                self._accumulate_ghost(image)
                self._show(image)

    def _accumulate_ghost(self, image):
        if self.shown is None:
            return
        erased = ImageChops.subtract(image, self.shown)
        self.ghost = ImageChops.add(
            self.ghost, erased.point(lambda v: timings.GHOST_PER_FAST_REFRESH if v > 40 else 0)
        )

    def _show(self, image):
        self.shown = image
        self.current = _surface(ImageChops.subtract(image, self.ghost))

    def _panel_surface(self):
        if not self.flash:
            return self.current
        steps, start, target = self.flash
        elapsed = time.monotonic() - start
        t = 0.0
        for level, span in steps:
            if elapsed < t + span:
                flat = Image.new("L", (PANEL_W, PANEL_H), 0xFF if level == waveform.WHITE else 0x00)
                return _surface(flat)
            t += span
        self._show(target)
        self.flash = None
        return self.current

    def _draw_info(self, x, lines):
        y = MARGIN
        warn = self.partials >= timings.MAX_PARTIALS_BEFORE_FULL
        header = [
            ("refreshes", str(self.refreshes)),
            ("waveform", self.last_mode.replace("lut_", "")),
            ("last refresh", f"{self.last_duration:.2f} s"),
            ("partials since full", f"{self.partials}" + ("  full due" if warn else "")),
        ]
        for key, value in header:
            self.screen.blit(self.small.render(key, True, (110, 110, 118)), (x, y))
            colour = (212, 128, 92) if warn and key.startswith("partials") else (206, 204, 196)
            self.screen.blit(self.font.render(value, True, colour), (x, y + 13))
            y += 34
        y += 8
        for line in (
            "76 x 126 mm body",
            "280 x 480 at 150 dpi",
            "47.3 x 81.1 mm of glass",
            "3 rows x 2 LEDs, mirrored",
        ):
            self.screen.blit(self.small.render(line, True, (96, 96, 104)), (x, y))
            y += 15
        y += 12
        for line in lines:
            self.screen.blit(self.small.render(line, True, (140, 140, 150)), (x, y))
            y += 15

    def tick(self, status_lines=()):
        self._accept()
        self.screen.fill((14, 14, 16))
        self.face.draw(
            self.screen,
            (MARGIN, MARGIN),
            self._panel_surface(),
            [self.strip.row(i) for i in range(self.strip.rows)],
            self.touch_live,
            self.small,
        )
        self._draw_info(MARGIN * 2 + self.face.size[0], list(status_lines))
        pygame.display.flip()

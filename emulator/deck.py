"""A stand-in app. Portrait 280x480, menu rows pitched to the LED strip.

Two menus after power-on: which program, then how many cards. Then hold the pad,
speak, and the reading prints a word at a time.
"""

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import buzzer as tones
import gravure
import layout

W, H = layout.W, layout.H
ROWS = layout.ROWS
ROW_H = layout.ROW_H
MENU_TOP = layout.MENU_TOP

WHITE, LIGHT, DARK, BLACK = 0xFF, 0xC0, 0x80, 0x00

FONTS = Path(__file__).parent / "fonts"


def _font(weight, size):
    try:
        return ImageFont.truetype(str(FONTS / f"IBMPlexMono-{weight}.ttf"), size)
    except OSError:
        return ImageFont.load_default()


BIG = _font("Bold", 24)
BODY = _font("Text", 15)
SMALL = _font("Regular", 12)

SPREADS = [("One card", "card of the day"), ("Two cards", "-"), ("Three cards", "-")]
MODES = ["Offline", "Online"]

SELECTED = (200, 150, 40, 0)
RECORDING = (140, 30, 30, 0)
THINKING = (30, 60, 140, 0)
OFF = (0, 0, 0, 0)

READING = (
    "The Tower stands first, and it is not a warning but a description. "
    "What you built to feel safe has been asking to fall for some time. "
    "The Star follows it, which is the part people forget: after the noise "
    "there is water, and someone pouring it back."
)


def canvas(fill=WHITE):
    return Image.new("L", (W, H), fill)


_ORNAMENT = {}


ORNAMENT_TOP = 34
ORNAMENT_H = 200


def ornament(seed):
    if seed not in _ORNAMENT:
        _ORNAMENT[seed] = gravure.ornament(W, ORNAMENT_H, seed)
    return _ORNAMENT[seed]


def menu_frame(title, items, note="", seed=4242):
    """Top half informs, bottom half chooses.

    The three rows sit level with the three LEDs, and the selection is not drawn
    at all — it is the lit lens beside the row.
    """
    img = canvas()
    img.paste(ornament(seed), (0, ORNAMENT_TOP))
    d = ImageDraw.Draw(img)
    d.text((18, 14), title, font=SMALL, fill=DARK)
    if note:
        d.text((18, MENU_TOP - 44), note, font=BODY, fill=BLACK)
    d.line([(0, MENU_TOP - 12), (W, MENU_TOP - 12)], fill=DARK, width=2)
    for i, (label, hint) in enumerate(items):
        y = layout.row_centre(i)
        if i:
            d.line([(18, y - ROW_H / 2), (W - 18, y - ROW_H / 2)], fill=LIGHT, width=1)
        d.text((26, y - 16), label, font=BIG, fill=BLACK)
        if hint != "-":
            d.text((26, y + 12), hint, font=SMALL, fill=DARK)
    return img


def listening_frame(seconds):
    img = canvas()
    d = ImageDraw.Draw(img)
    d.text((16, 60), "listening", font=BIG, fill=BLACK)
    bar = int((W - 32) * min(seconds / 8.0, 1.0))
    d.rectangle([16, 120, 16 + bar, 140], fill=BLACK)
    d.text((16, 160), f"{seconds:0.1f}s", font=BODY, fill=DARK)
    d.text((16, H - 26), "let go to stop", font=SMALL, fill=DARK)
    return img


def reading_frame(words, done=False):
    img = canvas()
    d = ImageDraw.Draw(img)
    y = 18
    for line in textwrap.wrap(" ".join(words), width=26)[-16:]:
        d.text((16, y), line, font=BODY, fill=BLACK)
        y += 22
    if done:
        d.text((16, H - 26), "Z to go back", font=SMALL, fill=DARK)
    return img


class Deck:
    def __init__(self, epd, strip, controls, buzzer):
        self.epd = epd
        self.strip = strip
        self.controls = controls
        self.buzzer = buzzer
        self.state = "spread"
        self.index = 0
        self.mode = MODES[0]
        self.spread = None
        self.status = "how many cards"

    def _mono(self, image):
        return image.point(lambda v: 255 if v > 0x60 else 0)

    def show_full(self, image):
        self.epd.display_4Gray(self.epd.getbuffer_4Gray(image))

    def show_fast(self, image):
        self.epd.display_1Gray(self.epd.getbuffer(self._mono(image)))

    def items(self):
        if self.state == "spread":
            return SPREADS
        if self.state == "settings":
            return [
                ("Sound", "on" if not self.buzzer.muted else "off"),
                ("Mode", self.mode.lower()),
                ("Back", "-"),
            ]
        return []

    def light_selection(self):
        rows = [OFF] * self.strip.rows
        if self.items():
            rows[self.index % self.strip.rows] = SELECTED
        self.strip.show_rows(rows)

    def draw_menu(self):
        if self.state == "spread":
            self.show_full(menu_frame("TAROT", self.items(), "how many cards", 4242))
        else:
            self.show_full(menu_frame("SETTINGS", self.items(), self.mode.lower(), 909))
        self.light_selection()

    def start(self):
        self.epd.init(0)
        self.epd.Clear(0xFF, 0)
        self.draw_menu()

    def move(self, delta):
        if not self.items():
            return
        self.index = (self.index + delta) % len(self.items())
        self.light_selection()
        self.buzzer.click()

    def confirm(self):
        self.buzzer.sequence(tones.CONFIRM, 22)
        if self.state == "spread":
            self.spread = SPREADS[self.index][0]
            self.state = "waiting"
            self.status = f"{self.mode}, {self.spread} — hold space and speak"
            self.strip.off()
            self.show_fast(listening_frame(0.0))
        elif self.state == "settings":
            if self.index == 0:
                self.buzzer.muted = not self.buzzer.muted
            elif self.index == 1:
                self.mode = MODES[(MODES.index(self.mode) + 1) % len(MODES)]
            else:
                self.state = "spread"
                self.index = 0
                self.status = "how many cards"
            self.draw_menu()

    def back(self):
        self.buzzer.sequence(tones.BACK, 22)
        if self.state == "spread":
            self.state = "settings"
            self.status = "settings"
        else:
            self.state = "spread"
            self.status = "how many cards"
        self.index = 0
        self.draw_menu()

    def listen(self, held_for):
        if self.state not in ("waiting", "listening"):
            return
        self.state = "listening"
        self.status = "listening"
        self.strip.show_rows([RECORDING] * self.strip.rows)
        self.show_fast(listening_frame(held_for))

    def read(self):
        if self.state != "listening":
            return
        self.state = "reading"
        self.status = "streaming — one word per 0.32 s refresh"
        self.buzzer.sequence(tones.REVEAL, 60)
        words = []
        for i, word in enumerate(READING.split()):
            words.append(word)
            rows = [OFF] * self.strip.rows
            rows[i % self.strip.rows] = THINKING
            self.strip.show_rows(rows)
            self.show_fast(reading_frame(words))
        self.strip.off()
        self.show_full(reading_frame(words, done=True))
        self.state = "done"
        self.status = "reading done — Z to go back"

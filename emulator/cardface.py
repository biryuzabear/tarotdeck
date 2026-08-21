"""A card's face, drawn from what the card actually is.

The first attempt drew the same figure on all 78 and varied only the noise, so a
deck of them was unreadable. This draws the card's identity instead, and three
families come out visibly different at a glance:

**Majors** carry no suit mark at all. A double outer ring says "this is a trump",
and the figure inside is built from the card's own number: an n-gon of that order
with its diagonals, counter-rotated against a second. Twenty-two numbers give
twenty-two figures.

**Numbered minors** are counted. The rank is drawn as that many suit marks set on a
ring and linked by the polygon that joins them, so Five of Cups is five marks in a
pentagon and can be counted without reading the name. An Ace is the single mark,
large and central.

**Court cards** are one large mark with rank bars beneath: Page one, Knight two,
Queen three, King four.

Suits are the four elemental triangles, which is the alchemical vocabulary the
gravure style already speaks:

| Suit | Element | Mark |
|---|---|---|
| Wands | fire | triangle, point up |
| Cups | water | triangle, point down |
| Swords | air | triangle up, barred |
| Pentacles | earth | triangle down, barred |

The cog that used to sit at the centre of everything is gone. It was the same on
every card, and being the largest thing on the plate it was all anyone saw.

**A reversed card turns its composition, never its marks.** Rotating the finished
plate by 180 degrees was the obvious way to show a reversal and it was wrong: the
four elemental triangles map onto each other under that rotation, so a reversed
Swords read as Pentacles and a reversed Cups as Wands. The turn is applied to the
layout — where the marks sit — while each mark is drawn the right way up, so the
card is visibly turned and its suit still says what it is.
"""

import math
import zlib

from PIL import Image, ImageDraw

import gravure

PAPER, FAINT, ORNAMENT, INK = 0xFF, 0xC0, 0x80, 0x00

MAJORS = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun", "Judgement",
    "The World",
]

RANKS = {
    "Ace": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6, "Seven": 7,
    "Eight": 8, "Nine": 9, "Ten": 10,
}
COURT = {"Page": 1, "Knight": 2, "Queen": 3, "King": 4}

FIRE, WATER, AIR, EARTH = "fire", "water", "air", "earth"
SUITS = {"Wands": FIRE, "Cups": WATER, "Swords": AIR, "Pentacles": EARTH}


def identify(name):
    """(kind, suit, rank) — kind is 'major', 'pip' or 'court'."""
    if name in MAJORS:
        return "major", None, MAJORS.index(name)
    rank, _, suit = name.partition(" of ")
    if suit not in SUITS:
        return "major", None, 0
    if rank in RANKS:
        return "pip", SUITS[suit], RANKS[rank]
    return "court", SUITS[suit], COURT.get(rank, 1)


def seed(name):
    """Stable across runs and machines. `hash()` is not."""
    return zlib.crc32(name.encode("utf-8"))


def _triangle(cx, cy, r, down):
    turn = math.pi / 2 if down else -math.pi / 2
    return [
        (cx + r * math.cos(turn + 2 * math.pi * k / 3), cy + r * math.sin(turn + 2 * math.pi * k / 3))
        for k in range(3)
    ]


def _mark(d, element, cx, cy, r, width=1):
    down = element in (WATER, EARTH)
    barred = element in (AIR, EARTH)
    pts = _triangle(cx, cy, r, down)
    d.line([(round(x), round(y)) for x, y in pts] + [(round(pts[0][0]), round(pts[0][1]))],
           fill=INK, width=width)
    if barred:
        y = cy + (-r * 0.22 if down else r * 0.22)
        half = r * 0.60
        d.line([round(cx - half), round(y), round(cx + half), round(y)], fill=INK, width=width)


def _ring_positions(count, cx, cy, radius, turned=False):
    if count == 1:
        return [(cx, cy)]
    start = math.pi / 2 if turned else -math.pi / 2
    return [
        (cx + radius * math.cos(start + 2 * math.pi * k / count),
         cy + radius * math.sin(start + 2 * math.pi * k / count))
        for k in range(count)
    ]


def _poly(cx, cy, r, sides, rot=0.0):
    return [
        (cx + r * math.cos(rot + 2 * math.pi * k / sides), cy + r * math.sin(rot + 2 * math.pi * k / sides))
        for k in range(sides)
    ]


def _stroke(d, pts, ink=INK, width=1, close=True):
    path = [(round(x), round(y)) for x, y in pts]
    if close:
        path.append(path[0])
    d.line(path, fill=ink, width=width)


def _major(d, number, cx, cy, r, rand, turned=False):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=2)
    inner = r * 0.88
    d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], outline=INK, width=1)

    sides = 3 + number % 7
    rot = (number % 5) * math.pi / 12 + (math.pi if turned else 0.0)
    _stroke(d, _poly(cx, cy, inner * 0.94, sides, rot), INK, 1)
    for i in range(sides):
        a = rot + 2 * math.pi * i / sides
        d.line([round(cx), round(cy), round(cx + inner * 0.94 * math.cos(a)), round(cy + inner * 0.94 * math.sin(a))],
               fill=ORNAMENT, width=1)

    counter = 3 + (number // 3) % 5
    _stroke(d, _poly(cx, cy, inner * 0.62, counter, rot + math.pi / counter), INK, 1)

    hub = r * 0.16
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=PAPER, outline=INK, width=1)
    if number % 2:
        d.ellipse([cx - hub * 0.45, cy - hub * 0.45, cx + hub * 0.45, cy + hub * 0.45], fill=INK)


def _pip(d, element, count, cx, cy, r, turned=False):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ORNAMENT, width=1)
    if count == 1:
        _mark(d, element, cx, cy, r * 0.60, width=2)
        return
    orbit = r * 0.66
    marks = min(count, 10)
    size = max(9.0, orbit * 2 * math.sin(math.pi / marks) * 0.42)
    points = _ring_positions(marks, cx, cy, orbit, turned)
    if marks >= 3:
        _stroke(d, points, FAINT, 1)
    else:
        _stroke(d, points, FAINT, 1, close=False)
    for px, py in points:
        _mark(d, element, px, py, size, width=1)


def _court(d, element, rank, cx, cy, r, turned=False):
    flip = -1 if turned else 1
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ORNAMENT, width=1)
    _stroke(d, _poly(cx, cy, r * 0.80, 4, -math.pi / 2), INK, 1)
    _mark(d, element, cx, cy - r * 0.10 * flip, r * 0.46, width=2)
    y = cy + r * 0.64 * flip
    half = max(5.0, r * 0.10)
    pitch = half * 2 + max(6.0, r * 0.09)
    start = cx - pitch * (rank - 1) / 2
    for i in range(rank):
        x = start + pitch * i
        d.line([round(x - half), round(y), round(x + half), round(y)], fill=INK, width=3)


def face(name, w, h, turned=False):
    img = Image.new("L", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    kind, element, value = identify(name)
    rand = gravure.rng(seed(name))

    cx, cy = w / 2, h * 0.5
    r = min(w * 0.36, h * 0.24)

    if kind == "major":
        _major(d, value, cx, cy, r, rand, turned)
    elif kind == "pip":
        _pip(d, element, value, cx, cy, r, turned)
    else:
        _court(d, element, value, cx, cy, r, turned)

    _wires(d, w, h, cx, cy, r, rand, majors=kind == "major")
    return img


def _wires(d, w, h, cx, cy, r, rand, majors):
    """The PCB runs that place the figure in the gravure world. Kept to the
    margins so they never cross the thing the card is trying to say."""
    prims = []
    via = 4
    gap = gravure.MIN_GAP
    for corner in range(4):
        left = corner % 2 == 0
        top = corner < 2
        y = (0.07 + rand() * 0.06) * h if top else (0.93 - rand() * 0.06) * h
        x_end = (0.10 + rand() * 0.10) * w if left else (0.90 - rand() * 0.10) * w
        drop = (10 + rand() * 16) * (1 if top else -1)
        if abs(y - cy) < r + gap * 2 or abs(y + drop - cy) < r + gap * 2:
            continue
        pts = gravure._run(-gap if left else w + gap, y, x_end, y + drop, r * 0.4)
        gravure._bundle(prims, pts, 2 if majors else 1, gap, via)
    gravure.render(d, prims, (0, 0), FAINT)

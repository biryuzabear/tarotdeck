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

Suits are four different silhouettes, not four variations on one. The elemental
triangles were the first attempt and they were too alike: point-up against
point-down reads, but barred against unbarred does not, and neither says wand or
coin to anyone.

| Suit | Mark | Silhouette |
|---|---|---|
| Wands | a rod with a knot at its head | a vertical line |
| Cups | a chalice: bowl, stem, foot | an open bowl |
| Swords | a blade with a crossguard | a cross |
| Pentacles | a coin: circle with a star inside | a circle |

Line, bowl, cross, circle — nothing in that set can be mistaken for another at any
size the panel can draw. Each degrades rather than squeezes: below the size where
the star inside a coin would close up it is dropped and the circle carries the suit
alone, and a chalice too small for a foot keeps its bowl.

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

ROD, CUP, BLADE, COIN = "rod", "cup", "blade", "coin"
SUITS = {"Wands": ROD, "Cups": CUP, "Swords": BLADE, "Pentacles": COIN}


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


def _mark(d, suit, cx, cy, r, width=1):
    """One suit sign, drawn to fit `r` and to drop detail rather than crowd it."""
    if suit == ROD:
        _rod(d, cx, cy, r, width)
    elif suit == CUP:
        _cup(d, cx, cy, r, width)
    elif suit == BLADE:
        _blade(d, cx, cy, r, width)
    else:
        _coin(d, cx, cy, r, width)


def _rod(d, cx, cy, r, width):
    top, bottom = cy - r, cy + r
    d.line([round(cx), round(top + r * 0.34), round(cx), round(bottom)], fill=INK, width=width + 1)
    knot = max(2.0, r * 0.30)
    d.ellipse(
        [round(cx - knot), round(top), round(cx + knot), round(top + knot * 2)],
        outline=INK, width=width,
    )
    if r >= 12:
        d.line([round(cx - r * 0.34), round(bottom), round(cx + r * 0.34), round(bottom)], fill=INK, width=width)


def _cup(d, cx, cy, r, width):
    bowl = r * 0.92
    top = cy - r * 0.55
    d.arc(
        [round(cx - bowl), round(top - bowl * 0.55), round(cx + bowl), round(top + bowl * 1.05)],
        0, 180, fill=INK, width=width + 1,
    )
    d.line([round(cx - bowl), round(top), round(cx + bowl), round(top)], fill=INK, width=width)
    d.line([round(cx), round(top + bowl * 0.95), round(cx), round(cy + r * 0.72)], fill=INK, width=width)
    if r >= 11:
        foot = r * 0.52
        d.line(
            [round(cx - foot), round(cy + r * 0.78), round(cx + foot), round(cy + r * 0.78)],
            fill=INK, width=width + 1,
        )


def _blade(d, cx, cy, r, width):
    d.line([round(cx), round(cy - r), round(cx), round(cy + r)], fill=INK, width=width + 1)
    guard = cy - r * 0.34
    half = r * 0.72
    d.line([round(cx - half), round(guard), round(cx + half), round(guard)], fill=INK, width=width + 1)
    if r >= 12:
        tip = r * 0.26
        d.line([round(cx - tip), round(cy + r - tip), round(cx), round(cy + r)], fill=INK, width=width)
        d.line([round(cx + tip), round(cy + r - tip), round(cx), round(cy + r)], fill=INK, width=width)


def _coin(d, cx, cy, r, width):
    d.ellipse([round(cx - r), round(cy - r), round(cx + r), round(cy + r)], outline=INK, width=width + 1)
    if r < 11:
        return
    star = r * 0.66
    pts = [
        (cx + star * math.cos(-math.pi / 2 + 2 * math.pi * k / 5),
         cy + star * math.sin(-math.pi / 2 + 2 * math.pi * k / 5))
        for k in range(5)
    ]
    order = [pts[(k * 2) % 5] for k in range(5)]
    _stroke(d, order, INK, width)


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


def gravure_face(name, w, h, turned=False, wires=True):
    img = Image.new("L", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    kind, element, value = identify(name)
    rand = gravure.rng(seed(name))

    cx, cy = w / 2, h * 0.5
    r = min(w * 0.30, h * 0.20)

    if kind == "major":
        _major(d, value, cx, cy, r, rand, turned)
    elif kind == "pip":
        _pip(d, element, value, cx, cy, r, turned)
    else:
        _court(d, element, value, cx, cy, r, turned)

    if wires:
        _wires(d, w, h, cx, cy, r, rand, majors=kind == "major")
    return img


def _wires(d, w, h, cx, cy, r, rand, majors):
    """The board the figure sits on.

    The suit sign says what the card is; this says what world it is in. It gets the
    room the figure gives up — the sign is drawn smaller than it could be so the
    wiring has somewhere to live rather than being crammed into the corners.

    Four things, in the order they are laid: a border trace inset from the frame
    with 45-degree corners, the way a real ground pour is drawn; bundles entering
    from the edges and stopping at a via short of the figure, never touching it;
    test points scattered where nothing else is; and, on majors only, a second
    border ring, which is the quietest way to say trump twice.
    """
    prims = []
    gap = gravure.MIN_GAP
    via = 4.0
    keepout = r + gap * 2.5

    inset = max(14.0, w * 0.075)
    chamfer = inset * 0.9
    _border(prims, inset, inset, w - inset, h - inset, chamfer)
    if majors:
        step = gap * 1.6
        _border(prims, inset + step, inset + step, w - inset - step, h - inset - step, chamfer * 0.8)

    for i in range(4):
        left = i % 2 == 0
        top = i < 2
        y = cy + (-1 if top else 1) * (keepout + gap * (2 + rand() * 3))
        if not (inset + gap < y < h - inset - gap):
            continue
        edge_x = -gap if left else w + gap
        stop_x = cx + (-1 if left else 1) * (keepout + gap * (1 + rand()))
        if not (inset < stop_x < w - inset):
            continue
        turn = (rand() - 0.5) * gap * 4
        pts = gravure._run(edge_x, y, stop_x, y + turn, r * 0.45)
        gravure._bundle(prims, pts, 1 + int(rand() * 3), gap, via)

    for _ in range(5):
        px = inset + gap + rand() * (w - 2 * (inset + gap))
        py = inset + gap + rand() * (h - 2 * (inset + gap))
        if math.hypot(px - cx, py - cy) < keepout + gap * 2:
            continue
        prims.append(("circle", (px, py), via * 0.8))
        prims.append(("circle", (px, py), via * 0.35))

    gravure.render(d, prims, (0, 0), FAINT)


def _border(prims, x0, y0, x1, y1, chamfer):
    """A rectangle with its corners cut at 45 degrees. No trace turns square."""
    pts = [
        (x0 + chamfer, y0), (x1 - chamfer, y0), (x1, y0 + chamfer),
        (x1, y1 - chamfer), (x1 - chamfer, y1), (x0 + chamfer, y1),
        (x0, y1 - chamfer), (x0, y0 + chamfer),
    ]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        prims.append(("line", a, b))


STYLES = [("Gravure", gravure_face)]
"""Card styles, in menu order.

One for now. A style is a name and a function with `face`'s signature, so adding
another is one entry here and nothing else — the settings menu, the session and the
card screen all read this list rather than knowing any style by name.

The obvious second entry is real art: a function that loads `cards/<slug>.png` off
the device and falls back to the drawn face when a plate is missing.
"""


def style_names():
    return [name for name, _ in STYLES]


def face(name, w, h, turned=False, style=0, wires=True):
    """`wires=False` drops the board layer.

    The wires are drawn in a grey a mono refresh erases, and the reading is a mono
    screen — so the strip of cards that stays above the text is drawn without them
    rather than with an invisible half. At strip size they would be clutter anyway.
    """
    _, draw = STYLES[style % len(STYLES)]
    return draw(name, w, h, turned, wires)

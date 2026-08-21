"""Where a card's name goes once the cards share the screen with the reading.

Four placements, drawn for comparison rather than chosen. Each is a function of
the plate rectangle and returns nothing — it draws.

The constraint they are all working against: the band is half the glass, a card is
1:1.714, and one card as tall as the band is only 140 px wide, so a single-card
spread leaves 70 px of empty column on each side. Two cards fill the width and
leave nothing. Three cascade. So the placement that suits one card is not
necessarily the one that suits three, and the honest answer may be two placements
rather than one.
"""

from PIL import ImageDraw

import typeset

INK, PAPER = 0, 255

NAME = typeset.font("SemiBold", 15)
NAME_SMALL = typeset.font("SemiBold", 12)
TURN = typeset.font("Regular", 11)


def _vertical(d, text, font, x, y, fill=INK):
    for i, ch in enumerate(text):
        d.text((x, y + i * (font.size + 1)), ch, font=font, fill=fill, anchor="ma")


def beside(d, plate, name, orientation, single):
    """In the empty column next to the card. Only one card leaves one."""
    x, y, w, h = plate
    if not single:
        return under(d, plate, name, orientation, single)
    left = x + w + 8
    room = 280 - left - 6
    cols = max(4, room // 8)
    for i, line in enumerate(typeset.wrap(name, cols)):
        d.text((left, y + 14 + i * 17), line, font=NAME_SMALL, fill=INK)



def under(d, plate, name, orientation, single):
    """A line under each plate. Costs the band 18 px of height."""
    x, y, w, h = plate
    font = NAME if single else NAME_SMALL
    d.text((x + w // 2, y + h + 11), name, font=font, fill=INK, anchor="mm")


def inside(d, plate, name, orientation, single):
    """Printed on the plate itself, the way a real card carries its name."""
    x, y, w, h = plate
    font = NAME if single else NAME_SMALL
    d.rectangle([x + 2, y + h - 30, x + w - 3, y + h - 3], fill=PAPER)
    d.text((x + w // 2, y + h - 16), name, font=font, fill=INK, anchor="mm")


def banner(d, plate, name, orientation, single):
    """A filled band across the foot of the plate. The loudest of the four."""
    x, y, w, h = plate
    font = NAME if single else NAME_SMALL
    d.rectangle([x + 2, y + h - 28, x + w - 3, y + h - 3], fill=INK)
    d.text((x + w // 2, y + h - 16), name, font=font, fill=PAPER, anchor="mm")


def listed(d, plate, name, orientation, single):
    """Nothing on the plates. See `list_line` — the names go in one line below.

    Three cascaded cards have no room for three names: every placement above puts
    them on top of each other, because the whole point of the cascade is that the
    plates overlap. So for three the names leave the cards alone.
    """
    if single:
        beside(d, plate, name, orientation, single)


def list_line(d, cards, y, localize=lambda n: n):
    """One line under the cascade, in the order the cards were turned."""
    text = " / ".join(localize(n) for n, _ in cards)
    font = NAME_SMALL if len(text) < 34 else TURN
    d.text((140, y), text, font=font, fill=INK, anchor="mm")


PLACEMENTS = [
    ("beside", beside), ("under", under), ("inside", inside),
    ("banner", banner), ("listed", listed),
]

"""Every frame the panel is ever asked to show.

Each function returns a finished 280x480 image and nothing else — no refreshes, no
state. `glass.py` decides how a frame reaches the panel; this file decides only what
is on it. Keeping the two apart is what lets the same frame be sent as a four-grey
plate or as a mono partial without the drawing code knowing or caring.

Four greys exist here: paper, faint, ornament, ink. **Only ink and paper survive a
mono refresh** — `glass` thresholds at 0x60, so 0x80 and 0xC0 both come out white —
so every screen that will be sent in mono says so and draws itself in ink alone.

That is not a style rule, it is the difference between a working control and a dead
one: the settings values were drawn in 0x80, which meant pressing the button
changed the value and erased it in the same stroke, and the screen was identical
before and after.
"""

from PIL import Image, ImageDraw

import cardface
import gravure
import layout
import typeset

W, H = layout.W, layout.H
PAPER, FAINT, ORNAMENT, INK = 0xFF, 0xC0, 0x80, 0x00

TITLE = typeset.font("Bold", 20)
ROW = typeset.font("Bold", 22)
HINT = typeset.font("Regular", 12)
BODY = typeset.font("Text", 15)
SMALL = typeset.font("Regular", 12)
CARD_NAME = typeset.font("SemiBold", 20)

def _tone(mono, level):
    """A grey, or ink if this frame is going out in mono."""
    return INK if mono else level


_ORNAMENTS = {}


def _ornament(seed):
    if seed not in _ORNAMENTS:
        _ORNAMENTS[seed] = gravure.ornament(W, layout.ORNAMENT_H, seed)
    return _ORNAMENTS[seed]


def _fit(text, cols):
    """Nothing is allowed to run off the glass. Better a clipped word than a line
    that looks like the screen is broken."""
    return text if len(text) <= cols else text[: cols - 1].rstrip() + "\u2026"


def _canvas(fill=PAPER):
    return Image.new("L", (W, H), fill)


def _draw(img):
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    return d


def _page_marks(d, page, pages, y):
    """One mark per page, the current one filled. Small, crisp, and countable at a
    glance — which "2 of 4" was not, because the number of items is not a place."""
    if pages <= 1:
        return
    size, gap = 7, 6
    total = pages * size + (pages - 1) * gap
    x = W - 18 - total
    for i in range(pages):
        box = [x, y - size // 2, x + size, y + size // 2]
        if i == page:
            d.rectangle(box, fill=INK)
        else:
            d.rectangle(box, outline=INK, width=1)
        x += size + gap


def menu(title, items, note="", seed=4242, ornamented=True, page=0, pages=1, mono=False):
    """Top informs, bottom chooses. The selection is the lit lens, not ink."""
    img = _canvas()
    if ornamented:
        img.paste(_ornament(seed), (0, layout.ORNAMENT_TOP))
    d = _draw(img)
    d.text((18, layout.TITLE_Y), title, font=SMALL, fill=_tone(mono, ORNAMENT))
    _page_marks(d, page, pages, layout.MENU_TOP - 30)
    if note:
        d.text((18, layout.MENU_TOP - 44), note, font=BODY, fill=INK)
    d.line([(0, layout.MENU_TOP - 12), (W, layout.MENU_TOP - 12)], fill=_tone(mono, ORNAMENT), width=2)
    for i, (label, hint) in enumerate(items[: layout.ROWS]):
        y = layout.row_centre(i)
        if i:
            d.line([(18, y - layout.ROW_H / 2), (W - 18, y - layout.ROW_H / 2)], fill=_tone(mono, FAINT), width=1)
        d.text((26, y - 16), label, font=ROW, fill=INK)
        if hint and hint != "-":
            d.text((26, y + 12), _fit(hint, 29), font=HINT, fill=_tone(mono, ORNAMENT))
    return img


def splash():
    img = _canvas()
    img.paste(_ornament(4242), (0, 120))
    d = _draw(img)
    d.text((W // 2, 70), "TAROT", font=TITLE, fill=INK, anchor="mm")
    return img


def ask(mode):
    img = _canvas()
    d = _draw(img)
    d.text((layout.MARGIN, 90), "ask", font=TITLE, fill=INK)
    d.text((layout.MARGIN, 130), "tap the pad and speak.", font=BODY, fill=INK)
    d.text((layout.MARGIN, 156), "tap again when you are done.", font=BODY, fill=INK)
    d.text((layout.MARGIN, layout.FOOTER_Y - 6), f"{mode}   tick left to go back", font=SMALL, fill=INK)
    return img


def listening(seconds, cap):
    img = _canvas()
    d = _draw(img)
    d.text((layout.MARGIN, 90), "listening", font=TITLE, fill=INK)
    width = int((W - layout.MARGIN * 2) * min(seconds / cap, 1.0))
    d.rectangle([layout.MARGIN, 140, W - layout.MARGIN, 162], outline=INK, width=2)
    d.rectangle([layout.MARGIN, 140, layout.MARGIN + width, 162], fill=INK)
    d.text((layout.MARGIN, 176), f"{seconds:0.1f}s of {cap:0.0f}", font=BODY, fill=INK)
    d.text((layout.MARGIN, layout.FOOTER_Y - 6), "tap the pad to stop", font=SMALL, fill=INK)
    return img


def hearing():
    img = _canvas()
    d = _draw(img)
    d.text((layout.MARGIN, 90), "hearing", font=TITLE, fill=INK)
    d.text((layout.MARGIN, 130), "putting words to it.", font=BODY, fill=INK)
    return img


def confirm(transcript, items):
    """The transcript above, three things to do with it below."""
    img = _canvas()
    d = _draw(img)
    d.text((layout.MARGIN, layout.TITLE_Y), "heard", font=SMALL, fill=INK)
    y = 44
    for line in typeset.wrap(transcript or "(nothing)", layout.READ_COLS)[:8]:
        d.text((layout.MARGIN, y), line, font=typeset.BODY, fill=INK)
        y += layout.READ_LEADING
    d.line([(0, layout.MENU_TOP - 12), (W, layout.MENU_TOP - 12)], fill=INK, width=2)
    for i, (label, hint) in enumerate(items[: layout.ROWS]):
        cy = layout.row_centre(i)
        if i:
            d.line([(18, cy - layout.ROW_H / 2), (W - 18, cy - layout.ROW_H / 2)], fill=INK, width=1)
        d.text((26, cy - 16), label, font=ROW, fill=INK)
        if hint and hint != "-":
            d.text((26, cy + 12), hint, font=HINT, fill=INK)
    return img


card_seed = cardface.seed


def card(name, orientation=None, index=1, total=1, plate=None, style=0, label=None, turn_word=None):
    """One card, full width. There are no reversals; every card is drawn upright."""
    img = _canvas()
    x0, y0, w, h = layout.CARD_RECT
    face = plate if plate is not None else cardface.face(name, w, h, style=style)
    img.paste(face, (x0, y0))
    d = _draw(img)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], outline=INK, width=2)
    _name_on_plate(d, x0, y0, w, h, label or name)
    if total > 1:
        d.text((layout.MARGIN, layout.CARD_ORIENT_Y), f"{index}/{total}", font=SMALL, fill=ORNAMENT, anchor="lm")
    return img


def _name_on_plate(d, x, y, w, h, name):
    """The card's name goes on the card, in the clear strip under its figure.

    There is room there — the figure never fills the plate — so the name needs
    neither a banner over the art nor a line stolen from the reading. It is the
    same place a printed deck puts it.
    """
    top, bottom = cardface.empty_band(w, h)
    cols = max(6, (w - 12) // 8)
    lines = typeset.wrap(name, cols)[:2]
    font = HINT if w < 110 else BODY
    step = font.size + 3
    y0 = y + top + max(0, (bottom - top - step * len(lines)) // 2)
    for i, line in enumerate(lines):
        d.text((x + w // 2, y0 + i * step), line, font=font, fill=INK, anchor="ma")


def reading(lines, page, pages, cards=(), deck=None, style=0, front=0):
    """The cards stay. They shrink to a strip across the top and remain there while
    the words arrive, because a reading you cannot see the cards for is a reading
    about nothing. The text lives in a frame below them.

    Everything here is ink on paper: this screen is sent in mono, where any grey
    would come out white.
    """
    footer = ""
    if pages > 1:
        footer = f"{page} of {pages}"
        footer += "   turn the gear" if page < pages else "   tick to seal"

    top = layout.FRAME_TOP + layout.FRAME_PAD if cards else layout.READ_TOP
    rows = layout.READ_ROWS_WITH_CARDS if cards else layout.READ_ROWS
    img = typeset.page_image(
        lines, (W, H), footer=footer or None,
        top=top, left=layout.MARGIN + layout.FRAME_PAD if cards else typeset.MARGIN_X,
        rows=rows,
    )
    if not cards:
        return img

    d = _draw(img)
    plates = layout.card_strip(len(cards))
    for index in layout.draw_order(len(cards), front):
        x, y, cw, ch = plates[index]
        name = cards[index][0]
        img.paste(cardface.face(name, cw, ch, style=style, wires=False), (x, y))
        d.rectangle([x, y, x + cw - 1, y + ch - 1], outline=INK, width=2)
        _name_on_plate(d, x, y, cw, ch, deck.localize(name) if deck else name)
    d.rectangle(
        [layout.MARGIN, layout.FRAME_TOP, W - layout.MARGIN, layout.FOOTER_Y - 8],
        outline=INK, width=1,
    )
    return img


def trouble(message, items):
    img = _canvas()
    d = _draw(img)
    d.text((layout.MARGIN, layout.TITLE_Y), "trouble", font=SMALL, fill=INK)
    y = 60
    for line in typeset.wrap(message, layout.READ_COLS)[:6]:
        d.text((layout.MARGIN, y), line, font=typeset.BODY, fill=INK)
        y += layout.READ_LEADING
    d.line([(0, layout.MENU_TOP - 12), (W, layout.MENU_TOP - 12)], fill=INK, width=2)
    for i, (label, hint) in enumerate(items[: layout.ROWS]):
        cy = layout.row_centre(i)
        if i:
            d.line([(18, cy - layout.ROW_H / 2), (W - 18, cy - layout.ROW_H / 2)], fill=INK, width=1)
        d.text((26, cy - 16), label, font=ROW, fill=INK)
    return img


def standing():
    """What the glass holds when the deck is off. E-paper keeps it with no power."""
    img = _canvas()
    img.paste(_ornament(77), (0, 140))
    d = _draw(img)
    d.text((W // 2, 90), "TAROT", font=TITLE, fill=INK, anchor="mm")
    d.text((W // 2, H - 40), "asleep", font=SMALL, fill=ORNAMENT, anchor="mm")
    return img

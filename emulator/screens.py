"""Every frame the panel is ever asked to show.

Each function returns a finished 280x480 image and nothing else — no refreshes, no
state. `glass.py` decides how a frame reaches the panel; this file decides only what
is on it. Keeping the two apart is what lets the same frame be sent as a four-grey
plate or as a mono partial without the drawing code knowing or caring.

Four greys exist here: paper, faint, ornament, ink. Only ink and paper survive a
mono refresh, so anything that must be legible during a streamed reading is drawn
in ink alone.
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


def menu(title, items, note="", seed=4242, ornamented=True, page=0, pages=1):
    """Top informs, bottom chooses. The selection is the lit lens, not ink."""
    img = _canvas()
    if ornamented:
        img.paste(_ornament(seed), (0, layout.ORNAMENT_TOP))
    d = _draw(img)
    d.text((18, layout.TITLE_Y), title, font=SMALL, fill=ORNAMENT if ornamented else INK)
    _page_marks(d, page, pages, layout.MENU_TOP - 30)
    if note:
        d.text((18, layout.MENU_TOP - 44), note, font=BODY, fill=INK)
    d.line([(0, layout.MENU_TOP - 12), (W, layout.MENU_TOP - 12)], fill=ORNAMENT, width=2)
    for i, (label, hint) in enumerate(items[: layout.ROWS]):
        y = layout.row_centre(i)
        if i:
            d.line([(18, y - layout.ROW_H / 2), (W - 18, y - layout.ROW_H / 2)], fill=FAINT, width=1)
        d.text((26, y - 16), label, font=ROW, fill=INK)
        if hint and hint != "-":
            d.text((26, y + 12), _fit(hint, 29), font=HINT, fill=ORNAMENT)
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


def card(name, orientation, index, total, plate=None, style=0, label=None, turn_word=None):
    """One card, full width. A reversed plate is turned; its name is not."""
    img = _canvas()
    x0, y0, w, h = layout.CARD_RECT
    turned = orientation == "reversed"
    if plate is not None:
        face = plate.rotate(180) if turned else plate
    else:
        face = cardface.face(name, w, h, turned=turned, style=style)
    img.paste(face, (x0, y0))
    d = _draw(img)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], outline=INK, width=2)
    d.text((W // 2, layout.CARD_NAME_Y), label or name, font=CARD_NAME, fill=INK, anchor="mm")
    d.text((W // 2, layout.CARD_ORIENT_Y), turn_word or orientation, font=SMALL, fill=ORNAMENT, anchor="mm")
    if total > 1:
        d.text((layout.MARGIN, layout.CARD_ORIENT_Y), f"{index}/{total}", font=SMALL, fill=ORNAMENT, anchor="lm")
    return img


def reading(lines, page, pages):
    footer = f"{page} of {pages}" if pages > 1 else ""
    if pages > 1:
        footer += "   turn the gear" if page < pages else "   tick to seal"
    return typeset.page_image(lines, (W, H), footer=footer or None)


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

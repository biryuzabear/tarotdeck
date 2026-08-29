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
import strings
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
NAME_LIST = typeset.font("SemiBold", 12)

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


def menu(title, items, note="", seed=4242, ornamented=True, page=0, pages=1, mono=False, language="en"):
    """Top informs, bottom chooses. The selection is the lit lens, not ink."""
    img = _canvas()
    if ornamented:
        img.paste(_ornament(seed), (0, layout.ORNAMENT_TOP))
    d = _draw(img)
    t = strings.translator(language)
    d.text((18, layout.TITLE_Y), t(title), font=SMALL, fill=_tone(mono, ORNAMENT))
    _page_marks(d, page, pages, layout.MENU_TOP - 30)
    if note:
        d.text((18, layout.MENU_TOP - 44), t(note), font=BODY, fill=INK)
    d.line([(0, layout.MENU_TOP - 12), (W, layout.MENU_TOP - 12)], fill=_tone(mono, ORNAMENT), width=2)
    for i, (label, hint) in enumerate(items[: layout.ROWS]):
        y = layout.row_centre(i)
        if i:
            d.line([(18, y - layout.ROW_H / 2), (W - 18, y - layout.ROW_H / 2)], fill=_tone(mono, FAINT), width=1)
        d.text((26, y - 16), t(label), font=ROW, fill=INK)
        if hint and hint != "-":
            d.text((26, y + 12), _fit(t(hint), 29), font=HINT, fill=_tone(mono, ORNAMENT))
    return img


def splash():
    img = _canvas()
    img.paste(_ornament(4242), (0, 120))
    d = _draw(img)
    d.text((W // 2, 70), "TAROT", font=TITLE, fill=INK, anchor="mm")
    return img


def ask(mode, language="en"):
    img = _canvas()
    d = _draw(img)
    t = strings.translator(language)
    d.text((layout.MARGIN, 90), t("ask"), font=TITLE, fill=INK)
    for i, line in enumerate((t("tap the pad and speak."), t("tap again when you are done."))):
        d.text((layout.MARGIN, 130 + i * 26), _fit(line, 31), font=BODY, fill=INK)
    d.text((layout.MARGIN, layout.FOOTER_Y - 6), f'{t(mode)}   {t("tick left to go back")}',
           font=SMALL, fill=INK)
    return img


def listening(seconds, cap, language="en"):
    img = _canvas()
    d = _draw(img)
    t = strings.translator(language)
    d.text((layout.MARGIN, 90), t("listening"), font=TITLE, fill=INK)
    width = int((W - layout.MARGIN * 2) * min(seconds / cap, 1.0))
    d.rectangle([layout.MARGIN, 140, W - layout.MARGIN, 162], outline=INK, width=2)
    d.rectangle([layout.MARGIN, 140, layout.MARGIN + width, 162], fill=INK)
    d.text((layout.MARGIN, 176), t("{seconds}s of {cap}", seconds=f"{seconds:0.1f}", cap=f"{cap:0.0f}"),
           font=BODY, fill=INK)
    d.text((layout.MARGIN, layout.FOOTER_Y - 6), t("tap the pad to stop"), font=SMALL, fill=INK)
    return img


def hearing(language="en"):
    img = _canvas()
    d = _draw(img)
    t = strings.translator(language)
    d.text((layout.MARGIN, 90), t("hearing"), font=TITLE, fill=INK)
    d.text((layout.MARGIN, 130), t("putting words to it."), font=BODY, fill=INK)
    return img


def confirm(transcript, items, language="en"):
    """The transcript above, three things to do with it below."""
    img = _canvas()
    d = _draw(img)
    t = strings.translator(language)
    d.text((layout.MARGIN, layout.TITLE_Y), t("heard"), font=SMALL, fill=INK)
    y = 44
    for line in typeset.wrap(transcript or t("(nothing)"), layout.READ_COLS)[:8]:
        d.text((layout.MARGIN, y), line, font=typeset.BODY, fill=INK)
        y += layout.READ_LEADING
    d.line([(0, layout.MENU_TOP - 12), (W, layout.MENU_TOP - 12)], fill=INK, width=2)
    for i, (label, hint) in enumerate(items[: layout.ROWS]):
        cy = layout.row_centre(i)
        if i:
            d.line([(18, cy - layout.ROW_H / 2), (W - 18, cy - layout.ROW_H / 2)], fill=INK, width=1)
        d.text((26, cy - 16), t(label), font=ROW, fill=INK)
        if hint and hint != "-":
            d.text((26, cy + 12), t(hint), font=HINT, fill=INK)
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
    if not cardface.bakes_names(style):
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


def reading(lines, page, pages, cards=(), deck=None, style=0, front=0, language="en", growing=False):
    """The cards, their names listed under them, a rule, and the reading.

    Everything sits on one margin and nothing is boxed: the reading is on the page,
    not in a frame. The names are set one under another rather than across, because
    three of them never fit on a line at any size worth reading — and a list of what
    was dealt is what it is.

    The card the current page is about is marked with a bar beside its name. In a
    row nothing overlaps, so there is no front card to bring forward; the mark is
    what carries that from the cascade it replaced.

    Everything here is ink on paper: this screen is sent in mono, where a grey would
    come out white.
    """
    t = strings.translator(language)
    count = len(cards)

    # The counter is on the glass from the first line, but its second half is not
    # written until it is true. While the reading is still arriving the footer says
    # "1 /" and leaves the total blank; when the reading ends the number is added.
    #
    # That is a deliberate use of what the panel is good at. A partial refresh adds
    # ink to blank paper cleanly and erases badly, so a count that grew in place —
    # "1 / 2" becoming "1 / 3" — would mean rubbing out a digit on every page turn.
    # An empty space that is filled in once is a pure append: 0.32 s, nothing moves.
    counter = t("{page} /", page=page) if growing else t("{page} / {pages}", page=page, pages=pages)
    hint = t("tick either way to close")

    if not cards:
        return typeset.page_image(lines, (W, H), footer=f"{counter}   {hint}")

    img = typeset.page_image(
        lines, (W, H),
        top=layout.text_top(count), left=layout.MARGIN, rows=layout.text_rows(count),
    )
    d = _draw(img)

    for rect, (name, _orientation) in zip(layout.card_row(count), cards):
        x, y, cw, ch = rect
        img.paste(cardface.face(name, cw, ch, style=style, wires=cw > 110), (x, y))
        d.rectangle([x, y, x + cw - 1, y + ch - 1], outline=INK, width=2)

    y = layout.names_top(count)
    for index, (name, _orientation) in enumerate(cards):
        label = (deck.localize(name) if deck is not None else name).upper()
        if count > 1 and index == front:
            d.rectangle([layout.MARGIN, y + 2, layout.MARGIN + 3, y + 11], fill=INK)
        d.text((layout.MARGIN + (10 if count > 1 else 0), y), label, font=NAME_LIST, fill=INK)
        y += layout.NAME_STEP

    rule = layout.rule_y(count)
    d.line([(layout.MARGIN, rule), (W - layout.MARGIN, rule)], fill=INK, width=1)

    baseline = H - layout.MARGIN - 11
    d.text((layout.MARGIN, baseline), counter, font=SMALL, fill=INK)
    d.text((layout.MARGIN + layout.COUNTER_W, baseline), hint, font=SMALL, fill=INK)
    return img


def trouble(message, items, language="en"):
    img = _canvas()
    d = _draw(img)
    t = strings.translator(language)
    d.text((layout.MARGIN, layout.TITLE_Y), t("trouble"), font=SMALL, fill=INK)
    y = 60
    for line in typeset.wrap(t(message), layout.READ_COLS)[:6]:
        d.text((layout.MARGIN, y), line, font=typeset.BODY, fill=INK)
        y += layout.READ_LEADING
    d.line([(0, layout.MENU_TOP - 12), (W, layout.MENU_TOP - 12)], fill=INK, width=2)
    for i, (label, hint) in enumerate(items[: layout.ROWS]):
        cy = layout.row_centre(i)
        if i:
            d.line([(18, cy - layout.ROW_H / 2), (W - 18, cy - layout.ROW_H / 2)], fill=INK, width=1)
        d.text((26, cy - 16), t(label), font=ROW, fill=INK)
    return img


def standing(language="en"):
    """What the glass holds when the deck is off. E-paper keeps it with no power."""
    img = _canvas()
    img.paste(_ornament(77), (0, 140))
    d = _draw(img)
    d.text((W // 2, 90), "TAROT", font=TITLE, fill=INK, anchor="mm")
    d.text((W // 2, H - 40), strings.tr(language, "asleep"), font=SMALL, fill=ORNAMENT, anchor="mm")
    return img

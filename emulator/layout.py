"""Where things sit on the 280x480 panel. The face reads this to place the LEDs.

Portrait only — the device is never held sideways.

The screen splits in two everywhere it can: the top half informs, the bottom half
chooses. The three menu rows are pitched to the three LED pairs, so the lit lens
lands beside its line and the selection never has to be drawn.

The reading grid is the one place that ignores the split, because a reading needs
every row it can get: 31 columns by 22 rows is the whole glass minus a footer.
"""

W, H = 280, 480

ROWS = 3
MENU_TOP = 270
ROW_H = (H - MENU_TOP) // ROWS

MARGIN = 16
TITLE_Y = 12

READ_COLS = 31
READ_LEADING = 20
READ_TOP = 14
READ_ROWS = 22
FOOTER_H = 26
FOOTER_Y = H - FOOTER_H

MARGIN = 16
"""One margin for everything.

There used to be four — the card strip bled to the edge, the text frame inset 12,
the text inset 10 again inside that, and the footer sat on 16 — which is what made
the screen read as assembled rather than designed. Cards, names, rule, text and
footer now all begin and end on this line.
"""

CARD_GAP = 8
CARD_BAND = 196
CARD_BAND_SINGLE = 210
ASPECT = 1.714

NAME_STEP = 18
RULE_GAP = 4
TEXT_GAP = 16
FOOTER_H = 20

COUNTER_W = 56
"""Space reserved for `page / pages` in the footer.

Wide enough for the longest counter the design can produce, so the hint beside it
never moves when the total is written in. A hint that shuffled sideways at the
moment the reading finished would be a repaint, and repaints are what this screen
spends its whole design avoiding.
"""


def card_row(count):
    """The drawn cards, side by side between the margins, as large as the band allows.

    A row rather than a cascade: nothing overlaps, so every card is whole and every
    name in the list below has a plate you can actually look at. It costs size —
    three across come to 13 mm each — and that is the price of all three being
    legible at once rather than two of them being edges.
    """
    count = max(1, min(3, count))
    band = CARD_BAND_SINGLE if count == 1 else CARD_BAND
    width = (W - 2 * MARGIN - (count - 1) * CARD_GAP) // count
    height = min(band, round(width * ASPECT))
    width = round(height / ASPECT)
    total = count * width + (count - 1) * CARD_GAP
    x = (W - total) // 2
    return [(x + i * (width + CARD_GAP), MARGIN, width, height) for i in range(count)]


def names_top(count):
    return MARGIN + card_row(count)[0][3] + 18


def rule_y(count):
    return names_top(count) + NAME_STEP * count + RULE_GAP


def text_top(count):
    return rule_y(count) + TEXT_GAP


def text_rows(count):
    return (H - MARGIN - FOOTER_H - text_top(count)) // READ_LEADING


def draw_order(count, front):
    """Which plate is painted last, and therefore whole.

    The cascade's positions never move — moving them would repaint the whole band
    on every page turn. Only the order changes, so the card the page is talking
    about is the one nothing overlaps.

    Behind it the cards keep the order a hand deals them: the first card lies over
    the second, the second over the third. Painting the rest in ascending order put
    the third card on top of the second, which reads as the pile having been
    shuffled rather than dealt.
    """
    front = max(0, min(count - 1, front))
    return [i for i in range(count) if i != front] + [front]

CARD_RECT = (16, 8, 248, 424)
CARD_NAME_Y = 448
CARD_ORIENT_Y = 468

ORNAMENT_TOP = 34
ORNAMENT_H = 200


def row_centre(index):
    return MENU_TOP + ROW_H * (index + 0.5)


def row_fraction(index):
    return row_centre(index) / H


def read_line_y(index):
    return READ_TOP + READ_LEADING * index

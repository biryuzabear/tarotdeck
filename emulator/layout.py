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

CARD_STRIP_TOP = 0
CARD_STRIP_H = H // 2
CARD_STRIP_GAP = 6

FRAME_TOP = CARD_STRIP_TOP + CARD_STRIP_H + 6
FRAME_PAD = 10
READ_ROWS_WITH_CARDS = (FOOTER_Y - 8 - FRAME_TOP - 2 * FRAME_PAD) // READ_LEADING


ASPECT = 1.714


def card_strip(count):
    """Where the drawn cards sit while the reading is being read.

    They take the top half of the glass and run edge to edge, right out to the lit
    chamfers with no margin of their own, because the card is what the reading is
    about and half the screen is what that is worth. They do not go away when the
    words arrive.

    One card is as tall as the half allows. Two share the width. Three side by side
    would be fingernails, so they overlap into a shallow cascade instead, which
    buys each of them half again the width at the cost of hiding a strip of the two
    behind.
    """
    count = max(1, min(3, count))
    band = CARD_STRIP_H
    if count == 1:
        height = band
        width = round(height / ASPECT)
        return [((W - width) // 2, CARD_STRIP_TOP, width, height)]
    if count == 2:
        width = (W - CARD_STRIP_GAP) // 2
        height = min(band, round(width * ASPECT))
        width = round(height / ASPECT)
        total = 2 * width + CARD_STRIP_GAP
        x = (W - total) // 2
        y = CARD_STRIP_TOP + (band - height) // 2
        return [(x, y, width, height), (x + width + CARD_STRIP_GAP, y, width, height)]
    step = 62
    width = W - 2 * step
    height = min(band - 24, round(width * ASPECT))
    width = round(height / ASPECT)
    total_w = width + 2 * step
    x = (W - total_w) // 2
    y = CARD_STRIP_TOP + (band - height - 24) // 2
    return [(x + i * step, y + i * 12, width, height) for i in range(3)]

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

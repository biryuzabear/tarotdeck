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

CARD_STRIP_TOP = 8
CARD_STRIP_H = 140
CARD_STRIP_GAP = 6

FRAME_TOP = CARD_STRIP_TOP + CARD_STRIP_H + 10
FRAME_PAD = 10
READ_ROWS_WITH_CARDS = (FOOTER_Y - 8 - FRAME_TOP - 2 * FRAME_PAD) // READ_LEADING


def card_strip(count):
    """Where each drawn card sits while the reading is being read.

    The cards do not go away when the words arrive. They shrink to a strip across
    the top and stay there, because a reading you cannot see the cards for is a
    reading about nothing.
    """
    count = max(1, min(3, count))
    gap = CARD_STRIP_GAP
    width = (W - 2 * MARGIN - (count - 1) * gap) // count
    height = min(CARD_STRIP_H, round(width * 1.714))
    width = round(height / 1.714)
    total = count * width + (count - 1) * gap
    x = (W - total) // 2
    y = CARD_STRIP_TOP + (CARD_STRIP_H - height) // 2
    return [(x + i * (width + gap), y, width, height) for i in range(count)]

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

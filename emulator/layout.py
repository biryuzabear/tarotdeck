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
READ_ROWS = 22
READ_LEADING = 20
READ_TOP = 14
FOOTER_H = 26
FOOTER_Y = H - FOOTER_H

CARD_RECT = (20, 12, 240, 411)
CARD_NAME_Y = 432
CARD_ORIENT_Y = 458

ORNAMENT_TOP = 34
ORNAMENT_H = 200


def row_centre(index):
    return MENU_TOP + ROW_H * (index + 0.5)


def row_fraction(index):
    return row_centre(index) / H


def read_line_y(index):
    return READ_TOP + READ_LEADING * index

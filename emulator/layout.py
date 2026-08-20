"""Where things sit on the 280x480 panel. The face reads this to place the LEDs.

Portrait only — the device is never held sideways.
"""

W, H = 280, 480

ROWS = 3
MENU_TOP = 270
ROW_H = (H - MENU_TOP) // ROWS


def row_centre(index):
    return MENU_TOP + ROW_H * (index + 0.5)


def row_fraction(index):
    return row_centre(index) / H

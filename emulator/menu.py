"""A list longer than the lenses can show.

Three LED rows means three visible rows, and that was fine while every menu had
three items. A longer list is turned in **pages of three**, not scrolled by one.

Paging rather than scrolling is what makes the indicator honest. A window sliding
one row at a time can only say "item 2 of 4", which tells you nothing you wanted to
know; a page can say "1 of 2", which is a place you can go back to. It also matches
the lenses: three lit rows are one page, and the page is the unit the hand moves.

The move that costs nothing is still the common one. Turning within a page moves the
light and repaints nothing at all; only crossing to the next page costs a fast
refresh. On four items that is one repaint in three moves, and on three items — every
other menu here — it is none, ever.
"""

WINDOW = 3


class Pager:
    def __init__(self, count, window=WINDOW):
        self.window = window
        self.cursor = 0
        self.count = max(0, count)

    def resize(self, count):
        self.count = max(0, count)
        self.cursor = min(self.cursor, max(0, self.count - 1))

    @property
    def pages(self):
        if self.count <= 0:
            return 1
        return (self.count + self.window - 1) // self.window

    @property
    def page(self):
        return self.cursor // self.window

    @property
    def row(self):
        """Which of the three lenses is lit."""
        return self.cursor % self.window

    @property
    def rows(self):
        """How many lenses have an item beside them on this page."""
        return min(self.window, self.count - self.page * self.window)

    def move(self, delta):
        """Returns True when the page turned and the screen must be redrawn."""
        if self.count == 0:
            return False
        was = self.page
        self.cursor = (self.cursor + delta) % self.count
        return self.page != was

    def visible(self, items):
        start = self.page * self.window
        return items[start : start + self.window]

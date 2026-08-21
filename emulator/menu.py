"""A list longer than the lenses can show.

Three LED rows means three visible rows, and that was fine while every menu had
three items. Settings has outgrown it, so a list now scrolls through a window of
three — and the distinction that matters is which moves cost the panel anything.

Moving inside the window moves the light and nothing else: no repaint, no refresh,
which is the trick the whole interface is built on. Only stepping past the edge
scrolls the window, and only that costs one fast refresh. A four-item list
therefore repaints on one step in four rather than on every one.
"""

WINDOW = 3


class Scroller:
    def __init__(self, count, window=WINDOW):
        self.count = max(0, count)
        self.window = window
        self.cursor = 0
        self.top = 0

    def resize(self, count):
        self.count = max(0, count)
        self.cursor = min(self.cursor, max(0, self.count - 1))
        self.top = min(self.top, max(0, self.count - self.window))

    def move(self, delta):
        """Returns True when the window shifted and the screen must be redrawn."""
        if self.count == 0:
            return False
        self.cursor = (self.cursor + delta) % self.count
        top = self.top
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + self.window:
            self.top = self.cursor - self.window + 1
        self.top = max(0, min(self.top, max(0, self.count - self.window)))
        return self.top != top

    @property
    def row(self):
        """Which of the three lenses is lit."""
        return self.cursor - self.top

    @property
    def rows(self):
        """How many lenses have an item beside them."""
        return min(self.window, self.count - self.top)

    def visible(self, items):
        return items[self.top : self.top + self.window]

    def more_above(self):
        return self.top > 0

    def more_below(self):
        return self.top + self.window < self.count

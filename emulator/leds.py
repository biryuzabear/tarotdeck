"""Stand-in for /dev/leds0, and the small vocabulary the lenses speak.

Three rows, mirrored left and right, six LEDs on the chain. The vocabulary is
deliberately small, because six lenses behind a printed chamfer cannot carry ten
meanings: colour is the deck's condition, motion means it is working, and the count
of lit rows is where you are in a list.
"""

import os

ROWS = 6
PER_ROW = 2

DEVICE = os.environ.get("TAROTDECK_LEDS", "/dev/leds0")
"""The kernel's WS2812 chain, when there is one.

`dtoverlay=ws2812-pio,gpio=21,num_leds=12` in `config.txt` creates it. Opening it
needs root, and `num_leds` there must match `ROWS * PER_ROW` here — set it short and
the far end of the chain simply stays dark with nothing to say so.
"""

OFF = (0, 0, 0, 0)
SELECTED = (200, 150, 40, 0)
DIM = (40, 30, 8, 0)
RECORDING = (150, 26, 26, 0)
WORKING = (170, 170, 175, 0)
TROUBLE = (70, 12, 12, 0)


class Strip:
    def __init__(self, rows=ROWS, per_row=PER_ROW, device=None):
        self.rows = rows
        self.per_row = per_row
        self.num_leds = rows * per_row
        self.brightness = 255
        self.pixels = [OFF] * self.num_leds
        if device is None:
            device = DEVICE if os.path.exists(DEVICE) else None
        self.device = device

    def write(self, data, offset=0):
        if offset == 0 and len(data) == 1:
            self.brightness = data[0]
            self._emit(data)
            return
        count = len(data) // 4
        for i in range(count):
            self.pixels[i] = tuple(data[i * 4 : i * 4 + 4])
        for i in range(count, self.num_leds):
            self.pixels[i] = OFF
        self._emit(b"".join(bytes(p) for p in self.pixels))

    def _emit(self, data):
        """Out to the chain, if this machine has one.

        Always the whole frame: a short write blanks every LED past its end, so the
        model is serialised in full rather than the caller's fragment being passed
        through.
        """
        if not self.device:
            return
        try:
            with open(self.device, "wb") as chain:
                chain.write(bytes(data))
        except OSError:
            self.device = None

    def show_rows(self, rows):
        data = bytearray()
        for colour in rows:
            for _ in range(self.per_row):
                data += bytes(colour)
        self.write(data)

    def row(self, index):
        return self.pixels[index * self.per_row]

    def off(self):
        self.show_rows([OFF] * self.rows)

    # the vocabulary

    def position(self, index, of=None):
        """Where you are in a list of `of` items that starts at the top lens."""
        of = of if of is not None else self.rows
        self.select(index, range(min(of, self.rows)))

    def select(self, active, among):
        """One lit row, the rest of the set dim, everything else dark.

        `among` is which lenses the list occupies — not always the top ones, since a
        menu sits at the bottom of the screen and takes the lenses beside it.
        """
        among = set(among)
        self.show_rows([
            SELECTED if i == active else (DIM if i in among else OFF)
            for i in range(self.rows)
        ])

    def filling(self, fraction):
        """Recording, and how much of the cap is spent."""
        lit = min(self.rows, int(fraction * self.rows) + 1) if fraction > 0 else 0
        self.show_rows([RECORDING if i < lit else OFF for i in range(self.rows)])

    def travelling(self, step):
        """Working. One row moves; the others are dark."""
        self.show_rows([WORKING if i == step % self.rows else OFF for i in range(self.rows)])

    def stuck(self):
        self.show_rows([TROUBLE] * self.rows)

    def shimmer(self, step):
        """A rainbow crawling down the chamfer while the reading is being made.

        The only place on the device that uses colour as colour rather than as a
        state. Everything else is amber, red or white and means something; this
        means the deck is thinking, and it is the one moment when there is nothing
        to read and nothing to do.
        """
        self.show_rows([_wheel((step * 4 + i * 85) % 256) for i in range(self.rows)])


def _wheel(position):
    """A place on the colour wheel, 0-255, as an RGBW pixel."""
    position &= 0xFF
    if position < 85:
        r, g, b = 255 - position * 3, position * 3, 0
    elif position < 170:
        position -= 85
        r, g, b = 0, 255 - position * 3, position * 3
    else:
        position -= 170
        r, g, b = position * 3, 0, 255 - position * 3
    scale = 0.55
    return (int(r * scale), int(g * scale), int(b * scale), 0)

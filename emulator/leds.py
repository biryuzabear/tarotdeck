"""Stand-in for /dev/leds0, and the small vocabulary the lenses speak.

Three rows, mirrored left and right, six LEDs on the chain. The vocabulary is
deliberately small, because six lenses behind a printed chamfer cannot carry ten
meanings: colour is the deck's condition, motion means it is working, and the count
of lit rows is where you are in a list.
"""

ROWS = 3
PER_ROW = 2

OFF = (0, 0, 0, 0)
SELECTED = (200, 150, 40, 0)
DIM = (40, 30, 8, 0)
RECORDING = (150, 26, 26, 0)
WORKING = (170, 170, 175, 0)
TROUBLE = (70, 12, 12, 0)


class Strip:
    def __init__(self, rows=ROWS, per_row=PER_ROW):
        self.rows = rows
        self.per_row = per_row
        self.num_leds = rows * per_row
        self.brightness = 255
        self.pixels = [OFF] * self.num_leds

    def write(self, data, offset=0):
        if offset == 0 and len(data) == 1:
            self.brightness = data[0]
            return
        count = len(data) // 4
        for i in range(count):
            self.pixels[i] = tuple(data[i * 4 : i * 4 + 4])
        for i in range(count, self.num_leds):
            self.pixels[i] = OFF

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
        """Where you are in a list: one row lit, the rest of the list dim."""
        of = of if of is not None else self.rows
        self.show_rows([
            SELECTED if i == index else (DIM if i < of else OFF)
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

"""Stand-in for /dev/leds0. Same write semantics as the ws2812-pio driver.

Three rows, mirrored left and right, six LEDs on the chain. A menu never needs
more than three items, so one lit row is one menu line.
"""

ROWS = 3
PER_ROW = 2


class Strip:
    def __init__(self, rows=ROWS, per_row=PER_ROW):
        self.rows = rows
        self.per_row = per_row
        self.num_leds = rows * per_row
        self.brightness = 255
        self.pixels = [(0, 0, 0, 0)] * self.num_leds

    def write(self, data, offset=0):
        if offset == 0 and len(data) == 1:
            self.brightness = data[0]
            return
        count = len(data) // 4
        for i in range(count):
            self.pixels[i] = tuple(data[i * 4 : i * 4 + 4])
        for i in range(count, self.num_leds):
            self.pixels[i] = (0, 0, 0, 0)

    def show_rows(self, rows):
        data = bytearray()
        for colour in rows:
            for _ in range(self.per_row):
                data += bytes(colour)
        self.write(data)

    def row(self, index):
        return self.pixels[index * self.per_row]

    def off(self):
        self.show_rows([(0, 0, 0, 0)] * self.rows)

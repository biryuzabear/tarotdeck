"""Reading text, wrapped, paginated and drawn without anything ever moving.

Three measured facts shape all of this.

**31 columns.** IBM Plex Mono advances exactly 8.000 px at size 13 and 14, and
9.000 px at 15. Over 248 px of usable width that is 31 columns at 14 and only 27 at
15, so 14 is the largest size that keeps 31 columns — and 13 is strictly dominated,
same columns with a shorter cap height.

**No antialiasing.** Partial refresh is mono; a grey edge pixel becomes a coin flip
on every stem after thresholding. `fontmode = "1"` removes the guess, and SemiBold
gives the stem enough ink to survive it.

**Append-only.** Lines land at fixed y and nothing already drawn ever moves. This is
not a layout preference — it is what lets a page be built by partial refreshes.
Rewrapping on every word, which is what a scrolling view does, moves every pixel on
the screen every time, and that is the one charge pattern the A2 waveform cannot
survive.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "fonts"

SIZE = 14
COLS = 31
ROWS = 22
LEADING = 20
MARGIN_X = 16
MARGIN_Y = 14
MAX_PAGES = 3

INK, PAPER = 0, 255


def font(weight="SemiBold", size=SIZE):
    try:
        return ImageFont.truetype(str(FONTS / f"IBMPlexMono-{weight}.ttf"), size)
    except OSError:
        return ImageFont.load_default()


BODY = font()


def wrap(text, cols=COLS):
    """Greedy wrap. A word longer than a line is broken rather than allowed to bleed."""
    lines = []
    current = ""
    for word in text.split():
        while len(word) > cols:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:cols])
            word = word[cols:]
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= cols:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def paginate(lines, rows=ROWS, max_pages=MAX_PAGES):
    pages = [lines[i : i + rows] for i in range(0, len(lines), rows)]
    return pages[:max_pages] if pages else [[]]


def page_image(lines, size=(280, 480), footer=None):
    """Draw `lines` at their fixed positions. Drawing fewer lines is the same image
    with the tail missing, which is what makes a partial refresh append-only."""
    img = Image.new("L", size, PAPER)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    y = MARGIN_Y
    for line in lines[:ROWS]:
        d.text((MARGIN_X, y), line, font=BODY, fill=INK)
        y += LEADING
    if footer:
        small = font("Regular", 12)
        d.line([(MARGIN_X, size[1] - 26), (size[0] - MARGIN_X, size[1] - 26)], fill=0x80, width=1)
        d.text((MARGIN_X, size[1] - 20), footer, font=small, fill=INK)
    return img


class LineStream:
    """Turns token fragments into finished lines.

    Holds back the trailing partial word until whitespace arrives, and the trailing
    partial line until the next word would overflow. Display therefore lags the
    stream by up to one line, which is correct: a line is only appended once it can
    never change again.
    """

    def __init__(self, cols=COLS):
        self.cols = cols
        self.buffer = ""
        self.current = ""
        self.lines = []

    def feed(self, chunk):
        """Returns the lines completed by this chunk, in order."""
        self.buffer += chunk
        finished = []
        while True:
            cut = max(self.buffer.rfind(" "), self.buffer.rfind("\n"))
            if cut < 0:
                break
            ready, self.buffer = self.buffer[:cut], self.buffer[cut + 1 :]
            for word in ready.split():
                if not self.current:
                    self.current = word
                elif len(self.current) + 1 + len(word) <= self.cols:
                    self.current += " " + word
                else:
                    finished.append(self.current)
                    self.lines.append(self.current)
                    self.current = word
        return finished

    def flush(self):
        """The tail, once the stream has ended."""
        finished = []
        tail = self.current
        self.buffer = self.buffer.strip()
        if self.buffer:
            if tail and len(tail) + 1 + len(self.buffer) <= self.cols:
                tail = tail + " " + self.buffer
            else:
                if tail:
                    finished.append(tail)
                    self.lines.append(tail)
                tail = self.buffer
        if tail:
            finished.append(tail)
            self.lines.append(tail)
        self.buffer = ""
        self.current = ""
        return finished

"""The only thing that talks to the panel.

Nothing else calls `display_4Gray` or `display_1Gray`. The reason is not tidiness:
the SSD1677 has two modes, `init` chooses between them, and a mono partial issued
while four-grey data is still in the old-image plane does not draw text — it drives
an arbitrary set of pixels in arbitrary directions. Keeping every refresh behind one
object is what makes that impossible rather than merely discouraged.

The waveforms, decoded from the driver's own LUT tables by `waveform.py`:

| | Mode | Time | Flashes |
|---|---|---|---|
| `lut_4Gray_GC` | four-grey | 3.04 s | 7 |
| `lut_1Gray_GC` | mono | 1.52 s | 1 |
| `lut_1Gray_DU` | mono | 1.12 s | 0 |
| `lut_1Gray_A2` | mono | 0.32 s | 0 |

`lut_1Gray_GC` is dead code in Waveshare's driver — defined and never called. It is
the right full refresh for a mono screen: half the time of four-grey, one flash
instead of seven, and no mode switch on either side. It is reached through a small
subclass here rather than by editing `vendor/`, which stays as shipped.

Nobody in this project has sent `lut_1Gray_GC` to real glass. If it turns out not to
clean the panel, every mono full becomes a four-grey at 3.04 s plus two mode
switches. That is on the Open list in docs/SESSION.md.
"""

import time

import timings

FOUR_GREY = 0
MONO = 1

IDLE_SLEEP = 90.0


class Panel:
    """A Waveshare EPD with the unused mono full refresh exposed."""

    def __init__(self, epd):
        self.epd = epd

    def display_1gray_clean(self, buffer):
        """Full mono refresh on lut_1Gray_GC — the driver never offers this."""
        epd = self.epd
        epd.send_command(0x4E)
        epd.send_data(0x00)
        epd.send_data(0x00)
        epd.send_command(0x4F)
        epd.send_data(0x00)
        epd.send_data(0x00)
        epd.send_command(0x24)
        epd.send_data2(buffer)
        epd.load_lut(epd.lut_1Gray_GC)
        epd.send_command(0x20)
        epd.ReadBusy()


class Glass:
    """Owns the panel's mode, its waveforms, and how long it has been idle."""

    def __init__(self, epd, transport=None):
        self.epd = epd
        self.panel = Panel(epd)
        self.transport = transport
        self.mode = None
        self.partials = 0
        self.fulls = 0
        self.panel_seconds = 0.0
        self.asleep = True
        self.last_refresh = 0.0

    def _wake(self, mode):
        if self.asleep or self.mode != mode:
            self.epd.init(mode)
            self.mode = mode
            self.asleep = False
            self.panel_seconds += 0.71
            return True
        return False

    def _done(self, seconds, partial):
        self.panel_seconds += seconds
        self.last_refresh = time.monotonic()
        if partial:
            self.partials += 1
        else:
            self.partials = 0
            self.fulls += 1

    def clear(self):
        self._wake(FOUR_GREY)
        self.epd.Clear(0xFF, FOUR_GREY)
        self._done(3.04, partial=False)

    def full(self, image):
        """Four greys, 3.04 s, seven flashes. For anything with tone in it."""
        self._wake(FOUR_GREY)
        self.epd.display_4Gray(self.epd.getbuffer_4Gray(image))
        self._done(3.04, partial=False)

    def mono_full(self, image):
        """Mono clean, 1.52 s, one flash. Establishes a known old image."""
        self._wake(MONO)
        self.panel.display_1gray_clean(self.epd.getbuffer(_threshold(image)))
        self._done(1.52, partial=False)

    def mono_partial(self, image):
        """0.32 s, no flash. Only legal once mono_full has been run."""
        if self.mode != MONO:
            raise RuntimeError("partial refresh outside mono mode — call mono_full first")
        self.epd.display_1Gray(self.epd.getbuffer(_threshold(image)))
        self._done(0.32, partial=True)

    def partials_left(self):
        """How many more partials before the vendor's own guidance is exceeded."""
        return max(0, timings.MAX_PARTIALS_BEFORE_FULL - self.partials)

    def idle_seconds(self):
        return time.monotonic() - self.last_refresh if self.last_refresh else 0.0

    def sleep_if_idle(self, after=IDLE_SLEEP):
        """Sleep when waiting on a human, never between refreshes.

        Deep sleep loses the controller's RAM, so the old image the A2 waveform
        differentiates against goes with it. Every wake is therefore an init plus
        one full refresh — never a partial.
        """
        if self.asleep or self.idle_seconds() < after:
            return False
        self.epd.sleep()
        self.asleep = True
        self.mode = None
        return True


def _threshold(image):
    return image.point(lambda v: 255 if v > 0x60 else 0)

"""Entry point on the deck itself. The same session, with nothing faked.

`run.py` puts a window in front of the panel and a keyboard behind the pins. This
file removes both and changes nothing else: the driver is Waveshare's own on real
SPI, the controls are the same gpiozero objects on real GPIO, and `Session` cannot
tell the difference. If a reading looks right in the emulator and wrong here, the
fault is in the parts of the world the emulator says it does not model — bounce,
contrast, the panel's actual ghosting — and not in a second implementation, because
there isn't one.

Root is needed for `/dev/leds0`.
"""

import signal
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "vendor"))

from board import IS_PI  # noqa: E402

if not IS_PI:
    sys.exit("run_deck.py is for the Pi. On a desk, run run.py.")

import waveshare_epd.epd3in7 as driver  # noqa: E402

import controls  # noqa: E402
import sources  # noqa: E402
from buzzer import Buzzer  # noqa: E402
from glass import Glass  # noqa: E402
from leds import Strip  # noqa: E402
from session import Session  # noqa: E402


def main():
    strip = Strip()
    glass = Glass(driver.EPD())
    session = Session(
        glass, strip, Buzzer(), ears=sources.ears(), reader_for=sources.for_mode
    )

    dial = controls.Dial()
    tap = controls.Tap()

    def turned(delta):
        move = dial.step(delta)
        if move:
            session.post("turn", move)

    controls.encoder.when_rotated_clockwise = lambda: turned(1)
    controls.encoder.when_rotated_counter_clockwise = lambda: turned(-1)
    controls.tick_left.when_pressed = lambda: session.post("tick_left")
    controls.tick_right.when_pressed = lambda: session.post("tick_right")
    controls.touch.when_pressed = lambda: tap.pressed() and session.post("pad")
    controls.touch.when_released = tap.edge

    print(f"deck running — ears: {session.ears.name}", flush=True)
    threading.Thread(target=session.start, daemon=True).start()

    stopping = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    try:
        while not stopping.is_set():
            session.pump()
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        _put_away(glass, strip)


def _put_away(glass, strip):
    """Leave the panel clean and the chain dark.

    A panel left holding an image sits in a high-voltage state, which is the one
    thing Waveshare's own precautions are unambiguous about.
    """
    strip.off()
    try:
        glass.clear()
        glass.epd.sleep()
    except Exception as exc:
        print(f"could not put the panel away: {exc}", flush=True)
    print("stopped", flush=True)


if __name__ == "__main__":
    main()

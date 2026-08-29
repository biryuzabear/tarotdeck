"""Plays a pre-packed 1-bit frame stream on the real panel, fast-refresh only.

Frames were extracted and dithered on the desk (ffmpeg + PIL), rotated 90°
so portrait glass shows a landscape video, then packed with the exact
bit layout `epd3in7.getbuffer`'s already-tested vertical branch produces —
no on-device decoding, no PIL on the Pi, no reliance on the driver's
never-exercised landscape rotation branch.

Left tick (GPIO22) starts. Right tick (GPIO23) stops and does a full clear +
sleep. Root needed for GPIO. Run from emulator/:
    sudo python3 badapple_play.py
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "vendor"))

from board import IS_PI  # noqa: E402

if not IS_PI:
    sys.exit("badapple_play.py is for the Pi.")

from gpiozero import Button  # noqa: E402
import waveshare_epd.epd3in7 as driver  # noqa: E402

import pins  # noqa: E402

W, H = driver.EPD_WIDTH, driver.EPD_HEIGHT  # 280 x 480
FRAME_BYTES = (W // 8) * H  # 16800
RAW_PATH = HERE / "badapple.raw"


def full_reset(epd):
    epd.init(0)
    epd.Clear(0xFF, 0)
    epd.sleep()


def play(epd, stop_flag):
    epd.init(1)
    epd.Clear(0xFF, 1)
    with open(RAW_PATH, "rb") as f:
        n = 0
        t0 = time.monotonic()
        while not stop_flag["stop"]:
            chunk = f.read(FRAME_BYTES)
            if len(chunk) < FRAME_BYTES:
                break
            epd.display_1Gray(list(chunk))
            n += 1
            if n % 100 == 0:
                elapsed = time.monotonic() - t0
                print(f"frame {n}, {elapsed:.1f}s elapsed, {n / elapsed:.2f} fps", flush=True)


def main():
    if not RAW_PATH.exists():
        sys.exit(f"missing {RAW_PATH} — scp badapple.raw next to this script first")

    epd = driver.EPD()
    left = Button(pins.BUTTON_LEFT, bounce_time=0.05)
    right = Button(pins.BUTTON_RIGHT, bounce_time=0.05)

    print(f"{RAW_PATH.stat().st_size // FRAME_BYTES} frames ready. left tick = play, right tick = stop + reset", flush=True)

    state = {"running": False}
    stop_flag = {"stop": False}

    def on_left():
        if not state["running"]:
            state["running"] = True
            print("left: playing", flush=True)

    def on_right():
        if state["running"]:
            print("right: stopping, full reset", flush=True)
            stop_flag["stop"] = True

    left.when_pressed = on_left
    right.when_pressed = on_right

    try:
        while True:
            if state["running"]:
                stop_flag["stop"] = False
                play(epd, stop_flag)
                full_reset(epd)
                state["running"] = False
                print("done. left tick to replay, ctrl-c to quit", flush=True)
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        full_reset(epd)
        print("stopped", flush=True)


if __name__ == "__main__":
    main()

"""Standalone panel test — run directly on the deck, no Session involved.

Splash: a real photo dithered to the panel's four actual grey levels, full
refresh, so it's judged in content rather than as an abstract swatch. Then one
fast-refresh animation (0.32 s, A2 waveform — the panel's floor, cannot go
faster): the screen is split into 4 vertical columns, each with its own bar
bouncing at a different speed, all updating together every frame so the
speeds are compared side by side, not one after another.

Left tick (GPIO22) starts. Right tick (GPIO23) stops and does a full clear +
sleep. Root needed for GPIO. Run from emulator/:
    sudo python3 screen_test.py
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "vendor"))

from board import IS_PI  # noqa: E402

if not IS_PI:
    sys.exit("screen_test.py is for the Pi.")

from PIL import Image, ImageDraw  # noqa: E402
from gpiozero import Button  # noqa: E402
import waveshare_epd.epd3in7 as driver  # noqa: E402

import pins  # noqa: E402

W, H = driver.EPD_WIDTH, driver.EPD_HEIGHT  # 280 x 480

FAST = 0.3
COLUMN_SPEEDS = [2, 6, 14, 28]  # px moved per 0.3 s frame, one per column
COLUMN_W = W // len(COLUMN_SPEEDS)

PHOTO_PATH = HERE / "monalisa_4gray.png"


def splash(epd):
    if PHOTO_PATH.exists():
        img = Image.open(PHOTO_PATH).convert("L")
        if img.size != (W, H):
            img = img.resize((W, H))
    else:
        img = _moon_scene()
    epd.init(0)
    epd.display_4Gray(epd.getbuffer_4Gray(img))


def _moon_scene():
    img = Image.new("L", (W, H), driver.GRAY1)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, int(H * 0.62)], fill=driver.GRAY2)
    mx, my, mr = int(W * 0.68), int(H * 0.22), 46
    draw.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=driver.GRAY1)
    draw.ellipse(
        [mx - mr + 22, my - mr - 10, mx + mr + 22, my + mr - 10],
        fill=driver.GRAY2,
    )
    for sx, sy in [(30, 40), (70, 100), (150, 60), (200, 140), (40, 180), (230, 90)]:
        draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=driver.GRAY4)

    def hill(y0, amp, shade, phase):
        pts = [(0, H)]
        for x in range(0, W + 1, 10):
            y = y0 - amp * abs(((x + phase) % (W // 2)) / (W // 2) - 0.5) * 2
            pts.append((x, y))
        pts.append((W, H))
        draw.polygon(pts, fill=shade)

    hill(int(H * 0.62), 40, driver.GRAY3, phase=0)
    hill(int(H * 0.78), 55, driver.GRAY3, phase=90)
    hill(int(H * 0.92), 60, driver.GRAY4, phase=40)
    draw.text((14, H - 26), "four greys: white / light / dark / black", fill=driver.GRAY1)
    return img


def enter_fast_mode(epd):
    """Clean 1-bit baseline before the A2 loop starts, so the splash's
    4Gray content doesn't linger as a ghost under the first fast frame."""
    epd.init(1)
    epd.Clear(0xFF, 1)


def run_columns(epd, stop_flag):
    positions = [0] * len(COLUMN_SPEEDS)
    directions = [1] * len(COLUMN_SPEEDS)
    bar_h = 60
    while not stop_flag["stop"]:
        img = Image.new("1", (W, H), 255)
        draw = ImageDraw.Draw(img)
        for col, speed in enumerate(COLUMN_SPEEDS):
            x0 = col * COLUMN_W
            if col > 0:
                draw.line([(x0, 0), (x0, H)], fill=0, width=1)
            draw.text((x0 + 6, 6), f"{speed}px", fill=0)
            y = positions[col]
            draw.rectangle([x0 + 10, y, x0 + COLUMN_W - 10, y + bar_h], fill=0)
            positions[col] += directions[col] * speed
            if positions[col] + bar_h >= H or positions[col] <= 0:
                directions[col] *= -1
        epd.display_1Gray(epd.getbuffer(img))
        time.sleep(FAST)


def full_reset(epd):
    epd.init(0)
    epd.Clear(0xFF, 0)
    epd.sleep()


def main():
    epd = driver.EPD()
    left = Button(pins.BUTTON_LEFT, bounce_time=0.05)
    right = Button(pins.BUTTON_RIGHT, bounce_time=0.05)

    print("splash shown. left tick = start 4-column animation, right tick = stop + reset", flush=True)
    splash(epd)

    state = {"running": False}
    stop_flag = {"stop": False}

    def on_left():
        if not state["running"]:
            state["running"] = True
            print("left: starting", flush=True)

    def on_right():
        if state["running"]:
            print("right: stopping, full reset", flush=True)
            state["running"] = False
            stop_flag["stop"] = True

    left.when_pressed = on_left
    right.when_pressed = on_right

    try:
        while True:
            if state["running"]:
                enter_fast_mode(epd)
                stop_flag["stop"] = False
                run_columns(epd, stop_flag)
                full_reset(epd)
                state["running"] = False
                print("reset done. left tick to start again, ctrl-c to quit", flush=True)
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        full_reset(epd)
        print("stopped", flush=True)


if __name__ == "__main__":
    main()

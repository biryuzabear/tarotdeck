"""TTP223 stopwatch. Holds and the gaps between them, on the screen, until stopped."""
import sys, threading, time
sys.path.insert(0, "/home/biryuzabear/e-Paper/RaspberryPi_JetsonNano/python/lib")
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd3in7
from gpiozero import Button

FONT = "/home/biryuzabear/e-Paper/RaspberryPi_JetsonNano/python/pic/Font.ttc"
ROTATE = 270

epd = epd3in7.EPD()
epd.init(0)
epd.Clear(0xFF, 0)
epd.init(1)
W, H = epd.width, epd.height
f_huge = ImageFont.truetype(FONT, 88)
f_big = ImageFont.truetype(FONT, 28)
f_med = ImageFont.truetype(FONT, 19)
f_small = ImageFont.truetype(FONT, 16)

pad = Button(26, pull_up=None, active_state=True)
reset_btn = Button(23, pull_up=True, bounce_time=0.05)
wash_btn = Button(22, pull_up=True, bounce_time=0.05)

t_start = time.time()
lock = threading.Lock()
rows = []                     # (hold_seconds, gap_before_or_None)
down = {"t": None}
last_up = {"t": None}
want = threading.Event()


def log(m):
    print(f"[{time.time() - t_start:7.2f}] {m}", flush=True)


def draw(live=None, final=None):
    img = Image.new("1", (W, H), 255)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=0, width=2)
    d.text((14, 10), "ttp223 stopwatch", font=f_big, fill=0)
    d.line((14, 48, W - 14, 48), fill=0, width=1)

    if live is not None:
        d.text((18, 76), f"{live:5.1f}", font=f_huge, fill=0)
        d.text((20, 178), "holding", font=f_big, fill=0)
    elif final is not None:
        d.text((18, 76), f"{final:5.1f}", font=f_huge, fill=0)
        d.text((20, 178), "released", font=f_big, fill=0)
    else:
        d.text((20, 110), "ready", font=f_big, fill=0)
        d.text((20, 150), "hold the pad", font=f_med, fill=0)

    y = 224
    d.line((14, y, W - 14, y), fill=0, width=1)
    y += 10
    d.text((18, y), f"{'#':>2}  {'held':>7}  {'gap':>6}", font=f_small, fill=0)
    y += 24
    for i, (h, g) in list(enumerate(rows, 1))[-7:]:
        gap = f"{g:6.2f}" if g is not None else "     -"
        d.text((18, y), f"{i:2d}  {h:6.2f}s  {gap}", font=f_med, fill=0)
        y += 24

    if rows:
        longest = max(r[0] for r in rows)
        gaps = [g for _, g in rows if g is not None]
        d.line((14, y + 4, W - 14, y + 4), fill=0, width=1)
        d.text((18, y + 12), f"longest {longest:.2f}s", font=f_med, fill=0)
        if gaps:
            d.text((18, y + 36), f"min gap {min(gaps):.2f}s", font=f_med, fill=0)

    with lock:
        epd.display_1Gray(epd.getbuffer(img.rotate(ROTATE, expand=True)))


def on_press():
    gap = time.time() - last_up["t"] if last_up["t"] else None
    down["t"] = time.time()
    down["gap"] = gap
    log(f"DOWN{'' if gap is None else f'   after {gap:.2f}s off'}")


def on_release():
    if down["t"] is None:
        return
    held = time.time() - down["t"]
    down["t"] = None
    last_up["t"] = time.time()
    rows.append((held, down.get("gap")))
    log(f"UP    held {held:6.2f}s")
    draw(final=held)


def on_reset():
    log("RESET")
    rows.clear()
    last_up["t"] = None
    with lock:
        epd.init(0)
        epd.Clear(0xFF, 0)
        epd.init(1)
    draw()


def on_wash():
    log("WASH")
    with lock:
        epd.init(0)
        epd.Clear(0xFF, 0)
        epd.init(1)
    draw()


pad.when_pressed = on_press
pad.when_released = on_release
reset_btn.when_pressed = on_reset
wash_btn.when_pressed = on_wash

log("stopwatch running — right tick resets, left tick washes the screen")
draw()

try:
    while True:
        if down["t"]:
            draw(live=time.time() - down["t"])
        else:
            time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    print("\n--- all holds ---", flush=True)
    for i, (h, g) in enumerate(rows, 1):
        print(f"{i:2d}  held {h:6.2f}s  gap {g if g is None else round(g, 2)}", flush=True)
    with lock:
        epd.init(0)
        epd.Clear(0xFF, 0)
        epd.sleep()

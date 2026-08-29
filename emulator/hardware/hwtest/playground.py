"""Everything on the deck, wired together, so it can be poked by hand."""
import subprocess, sys, textwrap, threading, time, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, "/home/biryuzabear/e-Paper/RaspberryPi_JetsonNano/python/lib")
from waveshare_epd import epd3in7
from gpiozero import Button, RotaryEncoder, PWMOutputDevice

LED_DEV = "/dev/leds0"
N_LEDS = 12
FONT = "/home/biryuzabear/e-Paper/RaspberryPi_JetsonNano/python/pic/Font.ttc"
HUM_WAV = "/home/biryuzabear/hum.wav"
SPEECH_WAV = "/home/biryuzabear/speech.wav"
SPEECH_RAW = "/home/biryuzabear/speech.raw"
HUM_SECONDS = 4
SR = 16000
WHISPER = "/home/biryuzabear/whisper.cpp/build/bin/whisper-cli"
MODEL = "/home/biryuzabear/whisper.cpp/models/ggml-base.en.bin"

COLOURS = [
    ("white", (70, 70, 70)), ("red", (90, 0, 0)), ("amber", (80, 35, 0)),
    ("green", (0, 90, 0)), ("cyan", (0, 60, 60)), ("violet", (50, 0, 80)),
]

state = {
    "pos": 0, "steps": 0, "colour": 0,
    "left": 0, "right": 0, "touch": 0,
    "mode": "idle", "last": "started",
    "notes": [], "text": "", "took": "", "held": "",
}
dirty = threading.Event()
busy = threading.Lock()
t_start = time.time()


def log(msg):
    print(f"[{time.time() - t_start:7.2f}] {msg}", flush=True)


def leds(pixels):
    buf = bytearray()
    for (r, g, b) in pixels:
        buf += bytes((r, g, b, 0))
    with open(LED_DEV, "wb") as f:
        f.write(bytes(buf))


def leds_off():
    leds([(0, 0, 0)] * N_LEDS)


def leds_all(col):
    leds([col] * N_LEDS)


def leds_cursor():
    """Three lit points, evenly spaced, each its own colour."""
    px = [(0, 0, 0)] * N_LEDS
    p = state["pos"] % N_LEDS
    base = state["colour"]
    for k in range(3):
        i = (p + k * (N_LEDS // 3)) % N_LEDS
        _, col = COLOURS[(base + k) % len(COLOURS)]
        px[i] = col
        for n in ((i - 1) % N_LEDS, (i + 1) % N_LEDS):
            if px[n] == (0, 0, 0):
                px[n] = tuple(c // 8 for c in col)
    leds(px)


# ---------------------------------------------------------------- screen

epd = epd3in7.EPD()
epd.init(1)
epd.Clear(0xFF, 1)
f_big = ImageFont.truetype(FONT, 22)
f_med = ImageFont.truetype(FONT, 17)
f_small = ImageFont.truetype(FONT, 15)
W, H = epd.width, epd.height          # 280 x 480, portrait
ROTATE = 270                          # portrait, the other way up


def clean():
    """Full four-grey refresh — the only one that inverts and clears ghosting."""
    epd.init(0)
    epd.Clear(0xFF, 0)
    epd.init(1)


def render():
    img = Image.new("1", (W, H), 255)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=0, width=2)
    d.text((12, 10), "playground", font=f_big, fill=0)
    d.line((12, 38, W - 12, 38), fill=0, width=1)

    name = "/".join(COLOURS[(state["colour"] + k) % len(COLOURS)][0][:3]
                    for k in range(3))
    y = 48
    for r in (f"encoder  {state['pos'] % N_LEDS:2d}  ({state['steps']})",
              f"ticks    L{state['left']}  R{state['right']}",
              f"touch    {state['touch']}   {state['held']}",
              f"leds     {name}"):
        d.text((12, y), r, font=f_med, fill=0)
        y += 24

    d.line((12, y + 4, W - 12, y + 4), fill=0, width=1)
    d.text((12, y + 12), state["mode"].upper(), font=f_med, fill=0)
    d.text((12, y + 36), state["last"][:32], font=f_small, fill=0)
    y += 62

    if state["notes"]:
        d.text((12, y), "notes", font=f_small, fill=0)
        d.text((12, y + 18), "  ".join(state["notes"][:8])[:30], font=f_small, fill=0)
        y += 44

    if state["text"]:
        d.line((12, y, W - 12, y), fill=0, width=1)
        head = "heard" + (f"   {state['took']}" if state["took"] else "")
        d.text((12, y + 8), head, font=f_small, fill=0)
        y += 30
        for line in textwrap.wrap(state["text"], 26)[:7]:
            d.text((12, y), line, font=f_med, fill=0)
            y += 22

    epd.display_1Gray(epd.getbuffer(img.rotate(ROTATE, expand=True)))


def screen_loop():
    while True:
        dirty.wait()
        dirty.clear()
        with busy:
            render()
        time.sleep(0.15)


def touch_screen(msg=None):
    if msg:
        state["last"] = msg
    dirty.set()


# ---------------------------------------------------------------- audio out

buzz = PWMOutputDevice(13, frequency=2000, initial_value=0)
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(f):
    n = int(round(12 * np.log2(f / 440.0))) + 69
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"


def detect_pitches(path):
    w = wave.open(path)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    frame, hop = 2048, 1024
    lo, hi = SR // 1000, SR // 70
    out = []
    for i in range(0, len(a) - frame, hop):
        x = a[i:i + frame] - a[i:i + frame].mean()
        if np.sqrt((x ** 2).mean()) < 250:
            out.append(None)
            continue
        c = np.correlate(x, x, "full")[frame - 1:]
        seg = c[lo:hi]
        if not len(seg):
            out.append(None)
            continue
        lag = int(np.argmax(seg)) + lo
        out.append(SR / lag if (c[0] and c[lag] / c[0] > 0.35) else None)
    return out


def to_notes(pitches):
    notes, cur, count = [], None, 0
    for p in pitches + [None]:
        if p and cur and abs(np.log2(p / cur)) < 0.06:
            cur = (cur * count + p) / (count + 1)
            count += 1
        else:
            if cur and count >= 2:
                notes.append((cur, count * 1024 / SR))
            cur, count = p, 1 if p else 0
    return notes


def play(notes):
    for f, dur in notes:
        tone = f
        while tone < 500:
            tone *= 2
        buzz.frequency = int(tone)
        buzz.value = 0.5
        time.sleep(min(dur, 0.9))
        buzz.value = 0
        time.sleep(0.04)


def hum_and_repeat():
    if not busy.acquire(blocking=False):
        return
    try:
        state["mode"] = "humming"
        state["notes"] = []
        touch_screen(f"hum for {HUM_SECONDS}s")
        render()
        leds_all((90, 0, 0))
        r = subprocess.run(["arecord", "-D", "plughw:0,0", "-f", "S16_LE", "-r", str(SR),
                            "-c", "1", "-d", str(HUM_SECONDS), HUM_WAV],
                           capture_output=True, text=True)
        if r.returncode:
            state["mode"] = "idle"
            state["notes"] = []
            err = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "arecord failed"
            log(f"hum: {err}")
            touch_screen(err[-32:])
            render()
            leds_cursor()
            return
        leds_all((80, 35, 0))
        state["mode"] = "repeating"
        notes = to_notes(detect_pitches(HUM_WAV))
        state["notes"] = [note_name(f) for f, _ in notes]
        state["last"] = f"{len(notes)} notes" if notes else "heard nothing"
        log(f"hum -> {len(notes)} notes {state['notes']}")
        render()
        if notes:
            leds_all((0, 90, 0))
            play(notes)
        state["mode"] = "idle"
        render()
        leds_cursor()
    finally:
        busy.release()


# ------------------------------------------------ tap-on / tap-off on the pad

QUIET_BEFORE_TAP = 1.0        # a tap counts only after this much silence on the line
MAX_RECORDING = 60.0

rec = {"proc": None, "t0": 0.0, "file": None}
edge = {"t": 0.0}             # any edge at all, accepted or not


def tap_accepted():
    now = time.time()
    quiet = now - edge["t"]
    edge["t"] = now
    if quiet < QUIET_BEFORE_TAP:
        log(f"  tap ignored — only {quiet:.2f}s of quiet")
        return False
    return True


def pad_released():
    edge["t"] = time.time()


def pad_pressed():
    if not tap_accepted():
        return
    state["touch"] += 1
    if rec["proc"] is None:
        start_recording()
    else:
        stop_recording()


def start_recording():
    if busy.locked():
        log("tap while busy — ignored")
        return
    log("TAP -> recording")
    rec["t0"] = time.time()
    rec["file"] = open(SPEECH_RAW, "wb")
    rec["proc"] = subprocess.Popen(
        ["arecord", "-D", "plughw:0,0", "-f", "S16_LE", "-r", str(SR),
         "-c", "1", "-t", "raw"],
        stdout=rec["file"], stderr=subprocess.DEVNULL)
    state["mode"] = "listening"
    state["text"] = ""
    state["took"] = ""
    state["held"] = ""
    leds_all((0, 0, 90))
    touch_screen("tap again when done")


def stop_recording():
    if rec["proc"] is None:
        return
    held = time.time() - rec["t0"]
    rec["proc"].terminate()
    rec["proc"].wait()
    rec["proc"] = None
    rec["file"].close()
    rec["file"] = None
    state["held"] = f"{held:.1f}s"
    log(f"TAP -> stopped after {held:.2f}s")

    with open(SPEECH_RAW, "rb") as f:
        pcm = f.read()
    pcm = pcm[:len(pcm) // 2 * 2]
    if not pcm:
        state["mode"] = "idle"
        state["text"] = "(mic gave nothing)"
        log("  no audio captured")
        touch_screen("mic gave nothing")
        return
    with wave.open(SPEECH_WAV, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)
    log(f"  wrote {len(pcm) // 2 / SR:.2f}s of audio")
    threading.Thread(target=run_whisper, daemon=True).start()


def recording_watchdog():
    while True:
        time.sleep(0.5)
        if rec["proc"] and time.time() - rec["t0"] > MAX_RECORDING:
            log("cap reached")
            stop_recording()


def run_whisper():
    if not busy.acquire(blocking=False):
        return
    try:
        state["mode"] = "thinking"
        leds_all((60, 30, 0))
        render()
        t0 = time.time()
        out = subprocess.run([WHISPER, "-m", MODEL, "-f", SPEECH_WAV,
                              "-t", "4", "-nt"], capture_output=True, text=True)
        took = time.time() - t0
        text = " ".join(out.stdout.split())
        state["text"] = text or "(nothing)"
        state["took"] = f"{took:.1f}s"
        state["last"] = "transcribed"
        log(f"whisper {took:.2f}s -> {text!r}")
        state["mode"] = "idle"
        render()
        leds_cursor()
    finally:
        busy.release()


# ---------------------------------------------------------------- inputs

enc = RotaryEncoder(5, 6, max_steps=0)
left = Button(22, pull_up=True, bounce_time=0.05)
right = Button(23, pull_up=True, bounce_time=0.05)
pad = Button(26, pull_up=None, active_state=True)


def on_rotate():
    state["steps"] = enc.steps
    state["pos"] = -enc.steps
    state["colour"] = -enc.steps // 3
    leds_cursor()
    touch_screen(f"encoder -> led {state['pos'] % N_LEDS}")


def on_left():
    state["left"] += 1
    log("TICK left")
    threading.Thread(target=hum_and_repeat, daemon=True).start()


def on_right():
    state["right"] += 1
    log("TICK right — wiping screen")
    threading.Thread(target=wipe, daemon=True).start()


def wipe():
    if not busy.acquire(blocking=False):
        return
    try:
        state["mode"] = "wiping"
        state["notes"] = []
        state["text"] = ""
        state["took"] = ""
        state["last"] = "screen wiped"
        clean()
        state["mode"] = "idle"
        render()
    finally:
        busy.release()


enc.when_rotated = on_rotate
left.when_pressed = on_left
right.when_pressed = on_right
pad.when_pressed = pad_pressed
pad.when_released = pad_released

subprocess.run(["pkill", "-x", "arecord"], stderr=subprocess.DEVNULL)
threading.Thread(target=recording_watchdog, daemon=True).start()

threading.Thread(target=screen_loop, daemon=True).start()
leds_cursor()
touch_screen("tap the pad to talk")

log("playground running")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    if rec["proc"]:
        rec["proc"].terminate()
    if rec["file"]:
        rec["file"].close()
    buzz.value = 0
    leds_off()
    clean()
    epd.sleep()
    log("stopped")

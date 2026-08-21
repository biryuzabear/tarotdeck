"""Entry point. The session owns the deck; the window owns the main thread.

Nothing here knows what a tarot reading is. It turns key presses into gpiozero pin
edges, gpiozero callbacks into session events, and pumps the session between frames.
That is the whole job, and it is deliberately the whole job: everything below this
file has to run on a Pi where there are no key presses and no window.
"""

import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "vendor")

import fake_epdconfig

sys.modules["waveshare_epd.epdconfig"] = fake_epdconfig
import waveshare_epd.epd3in7 as driver

driver.epdconfig = fake_epdconfig

import pygame

import controls
import panel
from buzzer import Buzzer
from glass import Glass
from leds import Strip
import sources
from session import Session

KEYS = [
    "left / right   right gear, turn",
    "z              left gear, tick left",
    "x              left gear, tick right",
    "space          touch pad, tap to start and stop",
    "esc            quit",
]


def main():
    fake_epdconfig.on_frame = panel.on_frame
    strip = Strip()
    window = panel.Window(strip)
    glass = Glass(driver.EPD(), fake_epdconfig)
    session = Session(glass, strip, Buzzer(), reader_for=sources.for_mode)

    import threading

    threading.Thread(target=session.start, daemon=True).start()

    controls.encoder.when_rotated_clockwise = lambda: session.post("turn", 1)
    controls.encoder.when_rotated_counter_clockwise = lambda: session.post("turn", -1)
    controls.tick_left.when_pressed = lambda: session.post("tick_left")
    controls.tick_right.when_pressed = lambda: session.post("tick_right")
    controls.touch.when_pressed = lambda: session.post("pad")

    clock = pygame.time.Clock()
    running = True
    pump = threading.Thread(target=_pump_forever, args=(session,), daemon=True)
    pump.start()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                    controls.turn_cw()
                elif event.key in (pygame.K_LEFT, pygame.K_UP):
                    controls.turn_ccw()
                elif event.key == pygame.K_z:
                    controls.press(controls.tick_left)
                elif event.key == pygame.K_x:
                    controls.press(controls.tick_right)
                elif event.key == pygame.K_SPACE:
                    controls.touch_down()
                    window.touch_live = session.state != "listen"
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_z:
                    controls.release(controls.tick_left)
                elif event.key == pygame.K_x:
                    controls.release(controls.tick_right)
                elif event.key == pygame.K_SPACE:
                    controls.touch_up()

        window.tick(_status(session, glass) + [""] + KEYS)
        clock.tick(60)

    pygame.quit()


def _pump_forever(session):
    while True:
        session.pump()
        time.sleep(0.02)


def _status(session, glass):
    return [
        f"{session.state}  —  {session.status}",
        f"{session.mode}   spread {session.spread}   partials left {glass.partials_left()}",
        f"reader: {session.reader.name if session.reader else '(chosen at draw)'}",
    ]


if __name__ == "__main__":
    main()

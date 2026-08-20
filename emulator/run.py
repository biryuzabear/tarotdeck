"""Entry point. App logic runs in a thread; the window owns the main thread."""

import sys
import threading
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
from deck import Deck
from leds import Strip

KEYS = [
    "left / right   right gear, turn",
    "z              left gear, tick left (back)",
    "x              left gear, tick right (ok)",
    "space (hold)   touch pad, dictation",
    "esc            quit",
]


def main():
    fake_epdconfig.on_frame = panel.on_frame
    strip = Strip()
    window = panel.Window(strip)
    deck = Deck(driver.EPD(), strip, controls, Buzzer())

    jobs = []
    lock = threading.Lock()

    def worker():
        deck.start()
        while True:
            with lock:
                job = jobs.pop(0) if jobs else None
            if job is None:
                time.sleep(0.01)
                continue
            job()

    def submit(job):
        with lock:
            if not jobs:
                jobs.append(job)

    threading.Thread(target=worker, daemon=True).start()

    controls.encoder.when_rotated_clockwise = lambda: deck.move(1)
    controls.encoder.when_rotated_counter_clockwise = lambda: deck.move(-1)
    controls.tick_left.when_pressed = lambda: submit(deck.back)
    controls.tick_right.when_pressed = lambda: submit(deck.confirm)

    clock = pygame.time.Clock()
    held_since = None
    running = True

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
                elif event.key == pygame.K_SPACE and held_since is None:
                    held_since = time.monotonic()
                    window.touch_live = True
                    controls.touch_down()
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_z:
                    controls.release(controls.tick_left)
                elif event.key == pygame.K_x:
                    controls.release(controls.tick_right)
                elif event.key == pygame.K_SPACE and held_since is not None:
                    controls.touch_up()
                    window.touch_live = False
                    held_since = None
                    submit(deck.read)

        if held_since is not None:
            elapsed = time.monotonic() - held_since
            submit(lambda: deck.listen(elapsed))

        window.tick([deck.status, ""] + KEYS)
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()

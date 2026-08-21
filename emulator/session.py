"""The state machine. Ten states, four controls, and one object that owns refreshes.

The rules that shape it:

**No state destroys work on a single unconfirmed tick.** The left gear sits under a
resting index finger. Abandoning happens from CONFIRM, before a wait has been spent,
and from TROUBLE, which is a menu — never from DRAW or READ.

**Long work never runs on the input thread.** Transcription and generation run on a
worker with a cancel token, and post events back. A tick during a ten-second reveal
is queued, not swallowed.

**Every refresh goes through `glass`.** No screen here calls the driver.
"""

import queue
import threading
import time

import cardface
import layout
import menu
import readers
import screens
import tarot
import timings
import typeset
from leds import Strip

TURN = "turn"
TICK_RIGHT = "tick_right"
TICK_LEFT = "tick_left"
PAD = "pad"
CHUNK = "chunk"
ENDED = "ended"
FAILED = "failed"
HEARD = "heard"

SPREADS = [
    ("One card", "the day, or a plain answer"),
    ("Two cards", "two forces pulling"),
    ("Three cards", "how it moves"),
]
MODES = ["offline", "online", "cards"]
MODE_HINT = {
    "offline": "the model, on the device",
    "online": "the model, over the network",
    "cards": "no model — the cards and what they mean",
}

LANGUAGES = [("en", "english"), ("ru", "\u0440\u0443\u0441\u0441\u043a\u0438\u0439")]
ONLINE_ONLY = {"ru"}
"""Russian is online only. The Russian adapter was never exported, so there is
nothing for the offline program to load."""

CONFIRM_ITEMS = [
    ("Yes", "read it"),
    ("Again", "say it again"),
    ("Back", "another spread"),
]
TROUBLE_ITEMS = [("Try again", ""), ("Go offline", ""), ("Back", "")]

LISTEN_CAP = 10.0


class Session:
    def __init__(self, glass, strip, buzzer, reader=None, deck=None, transcribe=None, reader_for=None):
        self.glass = glass
        self.strip = strip
        self.buzzer = buzzer
        self.reader_for = reader_for or (lambda mode, deck, language: reader)
        self.reader = reader
        self.deck = deck or tarot.Deck()
        self.transcribe = transcribe or (lambda seconds: "what should i know about the week ahead")

        self.events = queue.Queue()
        self.state = None
        self.index = 0
        self.mode = MODES[0]
        self.language = LANGUAGES[0][0]
        self.style = 0
        self.spread = 1
        self.settings = menu.Scroller(4)
        self.cards = []
        self.question = ""
        self.status = ""

        self.lines = []
        self.pages = [[]]
        self.page = 0
        self.stream = None
        self.pending = []
        self.cancel = None
        self.worker = None
        self.listen_started = 0.0
        self.travel = 0

    # ------------------------------------------------------------------ helpers

    def post(self, kind, value=None):
        self.events.put((kind, value))

    def _spawn(self, target):
        self.cancel = threading.Event()
        self.worker = threading.Thread(target=target, args=(self.cancel,), daemon=True)
        self.worker.start()

    def _stop_worker(self):
        if self.cancel:
            self.cancel.set()
        self.cancel = None

    def _settings_rows(self):
        language = dict(LANGUAGES)[self.language]
        return [
            ("Sound", self.buzzer.level),
            ("Mode", MODE_HINT[self.mode]),
            ("Language", language),
            ("Style", cardface.style_names()[self.style].lower()),
        ]

    def _items(self):
        if self.state == "settings":
            rows = self._settings_rows()
            self.settings.resize(len(rows))
            return self.settings.visible(rows)
        return {
            "spread": SPREADS,
            "confirm": CONFIRM_ITEMS,
            "trouble": TROUBLE_ITEMS,
        }.get(self.state, [])

    def _modes(self):
        return ["online"] if self.language in ONLINE_ONLY else MODES

    def light_selection(self):
        """Where you are in a list, and how long the list is. Never drawn on glass."""
        if self.state == "settings":
            self.strip.position(self.settings.row, of=self.settings.rows)
            return
        items = self._items()
        if items:
            self.strip.position(self.index % self.strip.rows, of=len(items))
        else:
            self.strip.off()

    # ------------------------------------------------------------------- states

    def enter(self, state, **kw):
        self.state = state
        self.index = 0
        getattr(self, f"_enter_{state}")(**kw)

    def start(self):
        self.enter("wake")

    def _enter_wake(self):
        self.status = "waking"
        self.glass.clear()
        self.glass.full(screens.splash())
        self.strip.travelling(0)
        self.enter("spread")

    def _enter_spread(self):
        self.status = "how many cards"
        self.glass.full(screens.menu("TAROT", SPREADS, self.mode, 4242))
        self.strip.position(self.index, of=len(SPREADS))

    def _enter_settings(self):
        self.status = "settings"
        self.settings.resize(len(self._settings_rows()))
        self._draw_settings(full=True)

    def _draw_settings(self, full=False):
        rows = self._items()
        note = ""
        if self.settings.more_above() or self.settings.more_below():
            note = f"{self.settings.cursor + 1} of {self.settings.count}"
        frame = screens.menu("SETTINGS", rows, note, 909, ornamented=False)
        if full:
            self.glass.mono_full(frame)
        else:
            self.glass.mono_partial(frame)
        self.light_selection()

    def _enter_ask(self):
        self.status = "tap the pad and speak"
        self.glass.mono_full(screens.ask(self.mode))
        self.strip.show_rows([(0, 0, 0, 0), (0, 0, 0, 0), (60, 45, 12, 0)])

    def _enter_listen(self):
        self.status = "listening"
        self.listen_started = time.monotonic()
        self.glass.mono_partial(screens.listening(0.0, LISTEN_CAP))
        self.strip.filling(0.0)

    def _enter_hearing(self):
        self.status = "hearing"
        took = time.monotonic() - self.listen_started
        self.strip.travelling(0)

        def job(cancel):
            time.sleep(min(1.2, max(0.4, took * 0.25)))
            if not cancel.is_set():
                self.post(HEARD, self.transcribe(took))

        self._spawn(job)

    def _enter_confirm(self):
        self.status = "is that the question"
        self.glass.mono_partial(screens.confirm(self.question, CONFIRM_ITEMS))
        self.strip.position(self.index, of=len(CONFIRM_ITEMS))

    def _enter_draw(self):
        self.status = "the cards turn"
        self.cards = self.deck.draw(self.spread)
        self.reader = self.reader_for(self.mode, self.deck, self.language)
        prompt = tarot.build_prompt(self.question, self.cards, self.deck)
        self.lines = []
        self.stream = typeset.LineStream(layout.READ_COLS)
        self.pending = []

        def job(cancel):
            try:
                for chunk in self.reader.stream(prompt, cancel):
                    if cancel.is_set():
                        return
                    self.post(CHUNK, chunk)
                self.post(ENDED)
            except readers.ReaderError as exc:
                self.post(FAILED, str(exc))

        self._spawn(job)
        self.buzzer.sequence((1320, 1760), 40)
        for i, (name, orientation) in enumerate(self.cards, 1):
            self.strip.position(i - 1, of=len(self.cards))
            self.glass.full(
                screens.card(
                    name, orientation, i, len(self.cards),
                    style=self.style,
                    label=self.deck.localize(name),
                    turn_word=tarot.TURN[self.language][orientation],
                )
            )
        self.enter("hold")

    def _enter_hold(self):
        self.status = "it is thinking"
        self.travel = 0

    def _enter_read(self):
        self.status = "the reading"
        self.page = 0
        self.glass.mono_full(screens.reading([], 1, 1))

    def _enter_trouble(self, message="something went wrong"):
        self.status = "trouble"
        self._stop_worker()
        self.glass.mono_full(screens.trouble(message, TROUBLE_ITEMS))
        self.strip.stuck()

    def _enter_standing(self):
        self.status = "asleep"
        self.glass.full(screens.standing())
        self.strip.off()

    # ------------------------------------------------------------------- events

    def handle(self, kind, value=None):
        getattr(self, f"_on_{kind}", lambda v: None)(value)

    def _on_turn(self, delta):
        if self.state == "settings":
            shifted = self.settings.move(delta)
            self.buzzer.click()
            if shifted:
                self._draw_settings()
            else:
                self.light_selection()
            return
        items = self._items()
        if items:
            self.index = (self.index + delta) % len(items)
            self.strip.position(self.index, of=len(items))
            self.buzzer.click()
        elif self.state == "read" and len(self.pages) > 1:
            self.page = (self.page + delta) % len(self.pages)
            self.buzzer.click()
            self._show_page()

    def _on_tick_right(self, _=None):
        self.buzzer.sequence((1760, 2640), 22)
        if self.state == "spread":
            self.spread = self.index + 1
            self.enter("ask")
        elif self.state == "settings":
            self._settings_confirm()
            self._draw_settings()
        elif self.state == "confirm":
            if self.index == 0:
                self.enter("draw")
            elif self.index == 1:
                self.enter("ask")
            else:
                self.enter("spread")
        elif self.state == "read":
            if self.page < len(self.pages) - 1:
                self.page += 1
                self._show_page()
            else:
                self.buzzer.play(880, 90)
                self.enter("spread")
        elif self.state == "trouble":
            if self.index == 0:
                self.enter("draw")
            elif self.index == 1:
                self.mode = "offline"
                self.enter("draw")
            else:
                self.enter("ask")

    def _settings_confirm(self):
        row = self.settings.cursor
        if row == 0:
            self.buzzer.cycle()
        elif row == 1:
            choices = self._modes()
            here = choices.index(self.mode) if self.mode in choices else -1
            self.mode = choices[(here + 1) % len(choices)]
        elif row == 2:
            codes = [code for code, _ in LANGUAGES]
            self.language = codes[(codes.index(self.language) + 1) % len(codes)]
            self.deck = tarot.Deck(language=self.language)
            if self.mode not in self._modes():
                self.mode = self._modes()[0]
        else:
            self.style = (self.style + 1) % len(cardface.STYLES)

    def _on_tick_left(self, _=None):
        self.buzzer.sequence((2640, 1760), 22)
        if self.state == "spread":
            self.enter("settings")
        elif self.state in ("settings", "ask", "confirm", "trouble"):
            self.enter("spread" if self.state in ("settings", "ask") else "ask")
        elif self.state == "read" and self.page > 0:
            self.page -= 1
            self._show_page()

    def _on_pad(self, _=None):
        if self.state == "ask":
            self.enter("listen")
        elif self.state == "listen":
            self.enter("hearing")

    def _on_heard(self, text):
        self.question = (text or "").strip()
        self.enter("confirm")

    def _on_chunk(self, chunk):
        if self.state not in ("hold", "read"):
            return
        finished = self.stream.feed(chunk)
        if not finished:
            return
        self.pending.extend(finished)
        if self.state == "hold":
            self.enter("read")
        self._flush_lines()

    def _on_ended(self, _=None):
        if self.state not in ("hold", "read"):
            return
        self.pending.extend(self.stream.flush())
        if self.state == "hold":
            self.enter("read")
        self._flush_lines(final=True)
        self.status = "read it, then tick to seal"
        self.strip.position(self.page, of=len(self.pages))

    def _on_failed(self, message):
        self.enter("trouble", message=message or "the reading stopped")

    # -------------------------------------------------------------------- pages

    def _flush_lines(self, final=False):
        step = max(1, timings.LINES_PER_PARTIAL)
        while len(self.pending) >= step or (final and self.pending):
            take, self.pending = self.pending[:step], self.pending[step:]
            self.lines.extend(take)
            self.pages = typeset.paginate(self.lines)
            if len(self.pages) - 1 > self.page:
                self.page = len(self.pages) - 1
                self.glass.mono_full(self._page_image())
            else:
                self.glass.mono_partial(self._page_image())
            self.strip.position(self.page, of=len(self.pages))

    def _page_image(self):
        page = self.pages[self.page] if self.page < len(self.pages) else []
        return screens.reading(page, self.page + 1, len(self.pages))

    def _show_page(self):
        self.glass.mono_full(self._page_image())
        self.strip.position(self.page, of=len(self.pages))

    # --------------------------------------------------------------------- pump

    def pump(self, budget=0.0):
        """Drain queued events. Returns how many were handled."""
        handled = 0
        deadline = time.monotonic() + budget
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            self.handle(kind, value)
            handled += 1
            if budget and time.monotonic() > deadline:
                break
        if self.state == "listen":
            elapsed = time.monotonic() - self.listen_started
            self.strip.filling(elapsed / LISTEN_CAP)
            if elapsed >= LISTEN_CAP:
                self.enter("hearing")
        elif self.state in ("hearing", "hold"):
            self.travel += 1
            self.strip.travelling(self.travel // (8 if self.state == "hearing" else 24))
        return handled

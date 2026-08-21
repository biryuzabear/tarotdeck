"""Rules the panel imposes.

Refresh durations are not here — they are derived from the waveform table the
driver sends, in waveform.py, so they cannot drift from what the panel would
actually do.
"""

LINES_PER_PARTIAL = 1
"""Lines appended per partial refresh.

One line per refresh is the design, decided against one word per refresh with the
arithmetic in docs/SESSION.md: a typical reading is 133 words but only 25 lines, so
by word it costs 133 partials and 42 s of panel time against a model that finished
in 17, and by line it costs 25 partials and 8 s.

Set it to 5 and a 22-row page becomes five partials, which obeys the literal vendor
rule below with no other change. The cost is that the reading stops arriving as if
spoken and lands in blocks.
"""

MAX_PARTIALS_BEFORE_FULL = 5
"""Waveshare's guidance, recorded rather than enforced. The wiki gives no figure at
all — "after refreshing partially several times" — and 5 is this project's own
reading of it. See docs/SESSION.md for why an append-only page of 22 partials
deposits less charge than five redraws of the same pixels."""

MIN_REFRESH_INTERVAL = 180.0
"""Vendor figure, recorded and not enforced. Verified as boilerplate pasted across
Waveshare's whole e-paper range; no device could obey it."""

GHOST_PER_FAST_REFRESH = 14


CARD_DWELL = 1.6
"""Seconds a revealed card is held after its refresh has finished.

The waveform alone was the pacing and it was not enough: a four-grey refresh spends
most of its 3.04 s flashing, so the card itself is only settled and legible for the
last second or so before the next one starts. The dwell is the time the card is
simply there, which is the part a person actually looks at.
"""

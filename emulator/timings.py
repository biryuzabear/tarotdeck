"""Rules the panel imposes. Refresh durations are not here — they are derived
from the waveform table the driver sends, in waveform.py."""

WORD_INTERVAL = 0.32

MAX_PARTIALS_BEFORE_FULL = 5
MIN_REFRESH_INTERVAL = 180.0

GHOST_PER_FAST_REFRESH = 14

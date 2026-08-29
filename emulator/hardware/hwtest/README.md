# Bring-up scripts

Two programs that run on the deck itself, over ssh. They exist to answer
questions about the hardware, not to become the product.

## `playground.py`
Everything wired together at once, so it can be poked by hand.

| Control | What it does |
|---|---|
| encoder | three lit points travel the LED chain, colours shift with position |
| left tick | records four seconds, finds the pitches, repeats them on the buzzer |
| right tick | full four-grey refresh — wipes the screen clean |
| touch pad | tap to start recording, tap again to stop, then Whisper puts the text on the screen |

Needs root for `/dev/leds0`:

```
sudo python3 playground.py
```

Paths inside are absolute and assume `~/e-Paper` and `~/whisper.cpp` are cloned
and built in the home directory.

## `holdtest.py`
A stopwatch for the touch pad, drawn on the e-paper: how long a touch stays
asserted, and the gap before each one. Right tick resets the table, left tick
washes the screen. Runs until killed.

This is what produced the numbers in `../parts/touch-ttp223.md`.

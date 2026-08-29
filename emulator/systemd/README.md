# Starting the deck at boot

Two units, and **only one may be enabled at a time** — they drive the same panel,
the same chain and the same pins, and two processes on those would fight. Each
declares `Conflicts=` on the other, so starting one stops the other rather than
letting that happen quietly.

| Unit | Runs | For |
|---|---|---|
| `tarotdeck-test.service` | `hardware/hwtest/playground.py` | poking every part by hand |
| `tarotdeck.service` | `emulator/run_deck.py` | the deck itself |

## Installing
```
sudo cp ~/tarotdeck/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tarotdeck-test.service
```

## Switching which one runs at boot
```
sudo systemctl disable --now tarotdeck-test.service
sudo systemctl enable --now tarotdeck.service
```

## Watching it
```
systemctl status tarotdeck-test.service
journalctl -u tarotdeck-test.service -f
```

## Why they are what they are
**Root**, because `/dev/leds0` is `root:root 0600`. A udev rule would lift that
and has not been written.

**`SUDO_USER=biryuzabear`** is set by hand because there is no sudo here. It is
what `board.home()` reads to find Whisper and the model, which live in the
person's home and not in root's.

**`ExecStartPre` waits for `/dev/leds0` and `/dev/spidev0.0`** for up to twenty
seconds. Both come from overlays in `config.txt` and both exist well before
`multi-user.target` in practice — but if an overlay is ever dropped, this fails
with a sentence about the overlays instead of a Python traceback about a missing
file.

**`Restart=on-failure`, three times in two minutes.** Enough to ride out a
transient, not enough to sit in a crash loop repainting the panel — e-paper wears
by refresh, so a restart is not free the way it is for a web service.

**`KillSignal=SIGINT`** so that `stop` reaches the same `KeyboardInterrupt` path
the programs already clean up in: panel cleared and put to sleep, chain dark. A
panel left holding an image sits in a high-voltage state, which is the one thing
Waveshare's precautions are unambiguous about.

# Tarot Cyberdeck — Claude Context

## What This Is
A handheld tarot cyberdeck built on Raspberry Pi 5. You speak a question, it
transcribes with Whisper, and a tarot LLM gives the reading.

Two programs, chosen at power-on: a **local** one that runs the model on the
device with Wi-Fi off, and a **networked** one that hands the reading to an API
and answers instantly.

**English only for now.** The Russian adapter exists but is parked. Whisper is
the English-only model. Don't plan around multilingual until this changes.

Hardware: all parts identified and assembled, running on real hardware since
2026-08-25. See `docs/PROGRESS.md` for what actually works on the device.

## Repo Layout — start here, then follow the links
```
CLAUDE.md                   this file
docs/PROGRESS.md            current state — read this first for "what's done"
docs/UI.md                  interaction and face layout, incl. hardware-confirmed
                             screen findings (no bezel margin, card art decisions)
docs/SESSION.md             the buildable session: states, prompt, reader, text on glass
docs/DECK.md                running on the Pi itself: install, deploy, what had to be true
docs/MODEL.md               tarot LLM training pipeline reference
docs/OS.md                  operating system choice and its traps
docs/RUNTIME.md             how the models fit and run on the Pi
docs/RENDER_PROMPT.md       prompt for visualising the object (not a spec)
hardware/BOM.md             parts index — links to parts/, all identified
hardware/parts/             one file per part
hardware/ENCLOSURE.md       size envelope and internal stack
hardware/POWER.md           battery and energy budget
hardware/PINOUT.md          the 40-pin header, by BCM and board number
hardware/hwtest/            standalone hardware test scripts (not the app)
decks/                      bought pixel-art tarot card assets — see each
                             deck's own SOURCE.md for author, license, style;
                             `4gray/` subfolders are the panel-palette conversion
emulator/                   running the deck on a desktop, with no Pi
tarot_model/                model training code
```

## How We Work
This is the user's project. Claude assists — it does not decide.
- Ask about one thing at a time; discuss before writing anything down.
- Record what the user actually said. Claude's inferences, plans, and
  speculation do not go in files.
- Mark unknowns as unknown. Never promote a guess to a fact.
- Do not start implementing unless explicitly asked.
- **Research runs in parallel and in the background.** Fan several agents out at
  once, and run them backgrounded so the conversation keeps going while they
  work — never block the chat waiting on a lookup.

## Repo Rules
- Text only, with one exception: licensed deck art PNGs under `decks/` — small
  enough to commit, and this repo is private. No other images, no weights, no
  CAD binaries, no audio.
- No Git LFS — it broke this repo once and history had to be reset.
- Never read or write `.env`.

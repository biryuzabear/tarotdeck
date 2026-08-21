# Tarot Cyberdeck — Claude Context

## What This Is
A handheld tarot cyberdeck built on Raspberry Pi 5. You speak a question, it
transcribes with Whisper, and a tarot LLM gives the reading.

Two programs, chosen at power-on: a **local** one that runs the model on the
device with Wi-Fi off, and a **networked** one that hands the reading to an API
and answers instantly.

**English only for now.** The Russian adapter exists but is parked. Whisper is
the English-only model. Don't plan around multilingual until this changes.

Hardware project: parts are still being identified, nothing is designed yet.

## Repo Layout
```
CLAUDE.md              this file
hardware/BOM.md        parts index — links to parts/
hardware/parts/        one file per part
docs/MODEL.md          tarot LLM training pipeline reference
docs/OS.md             operating system choice and its traps
docs/RUNTIME.md        how the models fit and run on the Pi
docs/UI.md             interaction and face layout
docs/SESSION.md        the buildable session: states, prompt, reader, text on glass
docs/PROGRESS.md       current state
hardware/PINOUT.md     the 40-pin header, by BCM and board number
emulator/              running the deck on a desktop, with no Pi
tarot_model/           model training code
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
- Text only. No weights, CAD binaries, audio, or images in git.
- No Git LFS — it broke this repo once and history had to be reset.
- Never read or write `.env`.

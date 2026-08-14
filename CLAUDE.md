# Tarot Cyberdeck — Claude Context

## What This Is
A handheld tarot cyberdeck built on Raspberry Pi 5. You speak a question, it
transcribes with Whisper, and a locally-run tarot LLM gives the reading.
Offline — no cloud calls at runtime.

Hardware project: parts are still being identified, nothing is designed yet.

## Repo Layout
```
CLAUDE.md              this file
hardware/BOM.md        parts index — links to parts/
hardware/parts/        one file per part
docs/MODEL.md          tarot LLM training pipeline reference
docs/PROGRESS.md       current state
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

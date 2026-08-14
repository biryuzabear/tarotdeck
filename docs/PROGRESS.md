# Progress

## Done
- Tarot LLM fine-tuning pipeline (`tarot_model/`) — EN and RU adapters on Qwen3.5-0.8B
- All parts identified and written up in `hardware/BOM.md` + `hardware/parts/`
- Enclosure envelope and internal stack: `hardware/ENCLOSURE.md`
- Power budget and its limits: `hardware/POWER.md`
- Interaction and face layout: `docs/UI.md`

## Dropped
- LED ring (40 mm, fits nowhere) · OLED (too small to earn its space) ·
  gyroscope (no use that isn't done better by something else)

## Unproven — nothing here has run on real hardware
Ordered by how much it could invalidate:

1. **Inference time.** Everything about the interaction assumes "it thinks for a
   moment, then answers." If a reading takes two minutes on the Pi, the design
   changes shape.
2. **Both models in 2 GB.** LLM ~900 MB + Whisper ~290 MB, plus OS. Fits on
   paper. Untested.
3. **The e-paper as a usable UI.** Partial refresh exists in C but not in the
   Python driver. Until text renders at a known speed, the menu is theory.
4. **Current draw under real load**, measured with an inline USB-C meter.
5. **The chamfer.** Wall thickness, diffusion, and bleed between LEDs — one small
   test print answers all three.

## Still open in the design
- Where the dictation control goes — the front face has no room left for it, so
  bottom edge or back
- How the transcribed question gets confirmed
- One lit chamfer or both
- Gear size, which collides with where the LED column starts

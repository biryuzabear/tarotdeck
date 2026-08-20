# Progress

## Done
- Tarot LLM fine-tuning pipeline (`tarot_model/`) — EN and RU adapters on Qwen3.5-0.8B
- All parts identified and written up in `hardware/BOM.md` + `hardware/parts/`
- Enclosure envelope and internal stack: `hardware/ENCLOSURE.md`
- Power budget and its limits: `hardware/POWER.md`
- Interaction and face layout: `docs/UI.md`
- Pin allocation drafted, e-Paper on wires rather than as a HAT:
  `hardware/PINOUT.md`
- OS chosen and its traps written down: `docs/OS.md`
- Memory budget for both models on 2 GB: `docs/RUNTIME.md`

## Dropped
- LED ring (40 mm, fits nowhere) · OLED (too small to earn its space) ·
  gyroscope (no use that isn't done better by something else)

## Unproven — nothing here has run on real hardware
Ordered by how much it could invalidate:

1. **Inference time.** Everything about the interaction assumes "it thinks for a
   moment, then answers." Estimated ~17 s for a 200-token reading at Q8_0, plus
   2–4 s to transcribe. Nothing measured on our hardware yet.
2. **Both models in 2 GB.** Fits at ~1.22 GB peak at Q8_0 — running one model at
   a time, with `-ub 64`. Architecture and sizes now check out on paper; see
   `docs/RUNTIME.md`.
3. **The e-paper as a usable UI.** The fast mono refresh *is* in the Python driver
   — `display_1Gray` loads the A2 waveform. Untested: how ~0.3 s actually looks
   with text, and how many fast refreshes the panel takes before it needs a
   cleaning full one.
4. **Current draw under real load**, measured with an inline USB-C meter.
5. **The chamfer.** Wall thickness, diffusion, and bleed between LEDs — one small
   test print answers all three.
6. **How thick a wall the touch sensor reads through.** A ladder of printed
   plates, 1 to 4 mm, in the real filament. Rides along on the same test print.

## Still open in the design
- Where the dictation control goes — the front face has no room left for it, so
  bottom edge or back
- How the transcribed question gets confirmed
- One lit chamfer or both
- Gear size, which collides with where the LED column starts

# Progress

## Done
- Tarot LLM fine-tuning pipeline (`tarot_model/`) — EN and RU adapters on Qwen3.5-0.8B
- Parts identified and written up in `hardware/BOM.md` + `hardware/parts/`
- Enclosure constraint recorded: 76 × 41 × 126 mm (`hardware/ENCLOSURE.md`)

## Now
Next question is **what the device does and how it's used** — which indicators
and which controls. Placement, wiring and pin maps come after that, not before.
Not every part on hand has to end up in the build; the gyro may well not.

Physical envelope is settled: the sandwich is 36.8 mm of the 41 mm, and the area
outside the Pi's footprint is free for controls.

## To discuss
Not started. Each gets its own doc when we actually talk about it.
- Operating system
- UI
- The programs / what runs on the device
- Running different models, possibly in parallel
- Functionality — what the device actually does

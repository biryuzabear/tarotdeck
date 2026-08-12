# Tarot Model — Progress Tracker

## Goal
Fine-tune small LLMs on tarot knowledge and deploy everywhere (Mac, Android, iOS, Raspberry Pi).

## Model Candidates (English)
| Model | Params | Pi 2GB | Best val loss | Quality score | Status |
|---|---|---|---|---|---|
| SmolLM2-135M | 135M | easily | 1.618 | 3.3 | trained en/v3 |
| SmolLM2-360M | 360M | easily | 1.451 | 4.3 | trained en/v1 |
| **Qwen3.5-0.8B** | **800M** | **easily** | **1.524** | **4.5** | **trained en/v2 ← winner** |

## Model Candidates (Russian)
| Model | Best val loss | Status | Notes |
|---|---|---|---|
| SmolLM2-135M | 0.908 | trained ru/v1 | memorized, gibberish output |
| Qwen3.5-0.8B | 1.766 | trained ru/v2 | usable, translated-style Russian |

**Target model: Qwen3.5-0.8B** — best multilingual support, best quality, fits Pi 2GB comfortably.

## Decisions Made
- **Fine-tuning tool**: MLX-LM (Apple Silicon, M4 Pro)
- **Export format**: GGUF (llama.cpp compatible)
- **Deployment targets**: Ollama (Mac), llama.cpp (Pi/Android/iOS)
- **Dataset structure**: `dataset/{lang}/` per language, `train.jsonl`/`valid.jsonl` gitignored
- **English dataset**: 2000 examples (1091 GPT-5.5 + 909 Gemini), keywords injected
- **Russian dataset**: 600 examples translated from English via Gemini + post-processed (card name fix, orphan "The" removal)
- **LoRA config**: rank=16, scale=10, dropout=0.1 (`lora_config.yaml`)
- **Adapter structure**: `adapters/{model}/{lang}/v{N}/`
- **Training script**: `train.py` — auto-versioning, epoch-based iters, language-aware, `--list` with sections per language
- **Test script**: `tests/test_model.py` — multilingual, hardcoded questions per language, think-tag stripping
- **Scoring**: `tests/score_model.py` — Gemini scoring, language-aware, score files include lang suffix
- **Translation**: `translate.py` — local (Tower-Plus-9B MLX 4bit) or Gemini/OpenAI
- **Card name fix**: `fix_card_names.py` — post-process translated data, replace English card names with target language names
- **Language card files**: `create_language_files.py` — generates card_names.txt, upright.txt, reversed.txt per language via Gemini

## Best Training Config (English, Qwen3.5-0.8B)
- Batch: 4, grad-accumulation: 4 (effective batch 16)
- LR: 5e-5 for v1, 2e-5 for v2
- Max seq length: 512 (dataset P99 is 268 tokens)
- Grad checkpointing: on
- Epochs: 5
- LoRA rank: 16, scale: 10, dropout: 0.1
- Save every: 25 (to catch best checkpoint)

## Best Training Config (Russian, Qwen3.5-0.8B)
- Same as English but lr=1e-4, 10 epochs
- Best checkpoint at iter 275 (val loss 1.766) — save-every 25 needed
- Only 540 train examples — small dataset ceiling

---

## Phases

### Phase 1 — Dataset [done]
- [x] Dataset format, spreads, tone rules, system prompt
- [x] generate.py — multi-provider (OpenAI + Gemini), validation, card meaning injection
- [x] 2000 English examples generated
- [x] inject_keywords.py — add keywords to existing data
- [x] Dataset restructured into `dataset/en/`
- [x] create_language_files.py — card_names.txt + upright/reversed per language (7 languages)
- [x] translate.py — translate dataset to target language (local Tower or API)
- [x] fix_card_names.py — post-process: replace English card names, strip orphans, fix brackets
- [x] Russian: 600 examples translated and cleaned

### Phase 2 — Setup [done]
- [x] Mac M4 Pro, MLX-LM installed
- [x] Models downloaded: SmolLM2-135M/360M, Qwen3-0.6B, Qwen3.5-0.8B, Tower-Plus-9B (MLX 4bit)

### Phase 3 — Fine-tuning [in progress]
- [x] train.py — auto-versioning, language-aware, --list with lang sections, save-every
- [x] tests/test_model.py — multilingual, hardcoded questions, RAM tracking
- [x] tests/score_model.py — Gemini scoring, language-aware
- [x] Trained English: SmolLM2-135M/360M, Qwen3-0.6B, Qwen3.5-0.8B (winner: en/v2, score 4.5)
- [x] Quantized English winners: fused + Q4 via mlx_lm
- [x] Trained Russian: Qwen3.5-0.8B v1+v2 (best: ru/v2, val 1.766)
- [x] Trained Russian: SmolLM2-135M v1 (memorized, useless — confirmed 135M can't do Russian)
- [ ] Score Russian Qwen3.5-0.8B (needs Gemini credits)
- [ ] Generate native Russian training data (not translated) for better quality
- [ ] Train remaining languages (DE, FR, ES, IT, PT, PL)

### Phase 4 — Export [ ]
- [ ] Convert best English adapter to GGUF
- [ ] Convert best Russian adapter to GGUF
- [ ] Test in Ollama locally
- [ ] Quantize for Pi/mobile

### Phase 5 — Deployment [ ]
- [ ] Local / Mac — Ollama
- [ ] Raspberry Pi — llama.cpp
- [ ] Android — MLC-LLM or Termux
- [ ] iOS — llama.cpp swift bindings or MLC-LLM

---

## Log
| Date | Note |
|---|---|
| 2026-06-19 | Project started. Model and stack decided. |
| 2026-06-19 | Dataset format, spreads, tone rules, generation script completed. |
| 2026-06-19 | MLX-LM installed. M4 Pro confirmed. |
| 2026-06-19 | 500 examples generated. Card distribution healthy. |
| 2026-06-20 | Card meanings injected into user messages. Multi-provider support. 2000 examples total. |
| 2026-06-20 | Training infrastructure built. Adapters reorganized to adapters/{model}/{lang}/v{N}. |
| 2026-06-20 | Trained 4 English models. Winner: Qwen3.5-0.8B en/v2, quality score 4.5. |
| 2026-06-20 | English models quantized to Q4 MLX. |
| 2026-06-21 | Multilingual infrastructure: translate.py, fix_card_names.py, create_language_files.py. |
| 2026-06-21 | Card files generated for DE/FR/ES/IT/PT/RU/PL via Gemini. |
| 2026-06-21 | Russian dataset: 600 examples translated + cleaned. Trained Qwen3.5-0.8B ru/v1+v2. |
| 2026-06-21 | Confirmed SmolLM2-135M has no Russian capability (val 0.908 = memorization). |
| 2026-06-21 | Dataset structure reorganized to dataset/{lang}/. Score files language-coded. |

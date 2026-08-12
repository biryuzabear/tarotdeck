# Tarot Model — Claude Context

## Project Goal
Fine-tune small LLMs on tarot knowledge and deploy universally (Mac, Pi, mobile).

## Target Model
**Qwen3.5-0.8B** — best multilingual support, best quality, fits Pi 2GB.
- English best: `adapters/qwen3_5_0.8b/en/v2` (val loss 1.524, quality 4.5)
- Russian best: `adapters/qwen3_5_0.8b/ru/v2` (val loss 1.766)

## Stack
- **Fine-tuning**: MLX-LM (Apple Silicon Mac M4 Pro)
- **Export**: GGUF (llama.cpp compatible)
- **Dataset format**: JSONL — user message has question + inline cards with keywords
- **Python venv**: `venv/` — `source venv/bin/activate`

## Dataset Structure
```
dataset/
  en/   card_names.txt, upright.txt, reversed.txt, dataset_en.jsonl
  ru/   card_names.txt, upright.txt, reversed.txt, dataset_ru.jsonl (600 examples)
  de/fr/es/it/pt/pl/  card_names.txt, upright.txt, reversed.txt (no dataset yet)
```
- Train/valid splits gitignored, generated per language
- `dataset/upright.txt` + `dataset/reversed.txt` — English source (root level)

## Scripts
| Script | Purpose |
|---|---|
| `train.py` | LoRA training, auto-versioning, `--lang`, `--list` |
| `translate.py` | Translate dataset to target language (local Tower or Gemini) |
| `fix_card_names.py` | Post-process: replace English card names in translated responses |
| `create_language_files.py` | Generate card_names/upright/reversed per language via Gemini |
| `generate.py` | Generate English training data via OpenAI/Gemini |
| `inject_keywords.py` | Add keywords to existing JSONL data |
| `tests/test_model.py` | Run 3 test prompts, `--lang` aware, RAM tracking |
| `tests/score_model.py` | Score with Gemini, `--lang` aware |

## Training Commands
```bash
# English
python train.py --model Qwen/Qwen3.5-0.8B --lang en --epochs 5 --batch-size 4 \
  --grad-accumulation-steps 4 --lr 5e-5 --grad-checkpoint --max-seq-length 512 --save-every 25

# Russian  
python train.py --model Qwen/Qwen3.5-0.8B --lang ru --epochs 10 --batch-size 4 \
  --grad-accumulation-steps 4 --lr 1e-4 --grad-checkpoint --max-seq-length 512 --save-every 25

# List all versions
python train.py --list
```

## Translation Pipeline
```bash
# 1. Translate dataset (Tower-Plus-9B local by default)
python translate.py --lang ru --provider local

# 2. Fix English card names in responses
python fix_card_names.py --lang ru

# 3. Split
python3 -c "... 90/10 split ..."
```

## LoRA Config (`lora_config.yaml`)
- rank=16, scale=10, dropout=0.1

## Adapter Structure
`adapters/{model_slug}/{lang}/v{N}/`
- model slugs: smollm2_135m, smollm2_360m, qwen3_5_0.8b
- langs: en, ru, de, fr, es, it, pt, pl

## Local Models Downloaded
- `Qwen/Qwen3.5-0.8B` — target training model
- `Qwen/Qwen3-0.6B` — downloaded, not used
- `HuggingFaceTB/SmolLM2-360M-Instruct` — trained, good English
- `HuggingFaceTB/SmolLM2-135M-Instruct` — trained, weak, no Russian
- `mlx-community/gemma-4-26b-a4b-it-4bit` — available for translation (hot/slow)
- `~/.cache/.../Tower-Plus-9B-MLX-4bit` — default translation model (5GB Q4)

## Key Findings
- SmolLM2-135M cannot do Russian (no pretraining data) — val loss 0.908 = memorization
- Qwen3.5-0.8B is the only viable multilingual model in this size range
- Translated Russian training data produces "translated-style" prose — acceptable but not native
- For native quality: generate data directly in target language via API (not translate)
- Tower-Plus-9B translation quality: OK for structure, not great for tarot mystical tone
- Gemini translation quality: better prose but English card names leak into responses — use fix_card_names.py

## Deployment Targets
- Mac — Ollama
- Raspberry Pi 2GB — llama.cpp (Q4_K_M, ~900MB RAM)
- Android/iOS — MLC-LLM or llama.cpp bindings

## Voice Input Plan
- Whisper `base` model — 290MB RAM, 99 languages, ~10s for 5s audio on Pi
- Flow: speak → Whisper → tarot model → response

## Multilingual Plan
- Priority: EN (done), RU (partial), DE, FR, ES, IT, PT, PL
- Each language: separate LoRA adapter on same Qwen3.5-0.8B base
- Other languages: rely on Qwen3.5-0.8B multilingual pretraining

## Conventions
- Track progress in `PROGRESS.md`
- Do not start implementing unless explicitly asked
- Never read or write `.env`

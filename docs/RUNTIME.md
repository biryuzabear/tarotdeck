# Running the models on the Pi

How Whisper and the tarot model share 2 GB. Numbers are research, not yet
measured on our hardware.

**English only.** The `en` adapter and the English-only Whisper. The `ru` adapter
is parked, so nothing here needs to account for switching languages.

## Two decisions the budget rests on

**Q8_0, not Q4.** Q4_K_M would halve the model to ~500 MB and run ~1.8× faster,
but **quality dropped noticeably at Q4** in testing. That's expected: a 0.8B model
suffers far more from 4-bit than a 7B does. The spare gigabyte isn't worth
having — spending it on precision is what it's for.

**Both models stay loaded for the whole session.** The program is chosen once at
power-on, and a session is several readings, not one — speak, answer, speak
again. Whisper is needed before every question and the model after every one, so
loading and unloading them in turn would mean reloading 800 MB on a loop.

They fit together, so they both just stay up. Two local servers, started once.

## The budget

Everything resident at the same time, Q8_0 with the flags below:

| | |
|---|---|
| Weights, Q8_0 | ~835 MB |
| KV cache, `-c 4096` | ~50 MB |
| Linear-attention state, constant | ~20 MB |
| Compute buffer, `-ub 64` | ~64 MB |
| Whisper `base.en` | ~410 MB |
| Pi OS Lite | ~250 MB |
| **Total** | **~1.63 GB** |
| Spare | ~385 MB for Python, Pillow, the application |

Against ~2015 MB on the board. See [OS.md](OS.md).

**`-ub 64` is what makes this fit.** At llama.cpp's default `-ub 512` the compute
buffer grows from 64 MB to 508, and the total goes to **~2.07 GB** — just over the
edge. One flag decides whether both models are resident or not.

Q4_K_M would drop weights from 835 MB to 532, taking the total to ~1.33 GB. Not
needed.

## Loading from the card: two different things
**Cold load** is reading ~835 MB at ~90 MB/s sequential — about **10 seconds**,
once, when the local program starts. Paid at power-on, not per reading.

**Thrashing** is what happens when the model *doesn't* fit: every token re-reads
weights from the card, 10–18 s per token. This only exists in the doesn't-fit
case. Since we fit, it doesn't apply, and NVMe isn't needed.

The networked program never pays either, since it loads only Whisper.

## Where the memory actually goes

**llama.cpp overhead above the file is small** — about 50 MB. Measured on a Pi 5:
Q4_K_M 700 MB file → 750 MB RSS; Q8_0 1.2 GB → 1.3 GB.

**The KV cache is almost free here** — 12 KiB/token, computed from the model's own
`config.json`.

Qwen3.5 is a **hybrid**: of its 24 layers only **6 use full attention**, the other
18 use linear attention whose recurrent state is a fixed size and does not grow
with context at all. Only those six accumulate a KV cache.

```
2 × 6 full-attn layers × 2 kv_heads × 256 head_dim × 2 bytes = 12 KiB/token
```

| Context | KV |
|---|---|
| 2048 | ~24 MB |
| 4096 | ~48 MB |
| 8192 | ~96 MB |

Plus a constant ~19 MB for the linear layers' recurrent state, independent of
context. **Context length is cheap for us** — no reason to economise on it.

**The compute buffer is the expensive one, because the vocabulary is huge.**
248,320 tokens, roughly double the usual. The logits tensor is
`n_ubatch × 248320 × 4 bytes`:

| `-ub` | Logits |
|---|---|
| 512 (default) | **508 MB** |
| 64 | 64 MB |
| 32 | 32 MB |

One flag, half a gigabyte. Prefill here is a short question, so a small batch
costs us nothing.

`-ub` sets how many prompt tokens are processed in one pass. The buffer is sized
for the worst case — a full chunk of tokens each needing a score row across the
whole vocabulary. It affects **prompt reading only**; generation is one token at a
time regardless, so a small chunk costs nothing in the reading itself.

A side effect of that vocabulary: the embedding table is ~254 M parameters of the
model's 800 M. **A third of this model is its vocabulary.**

## Whisper costs more than its file suggests
The encoder allocates fixed-size buffers regardless of input, so the overhead is
worse than llama.cpp's:

| Model | File | RAM |
|---|---|---|
| tiny | 75 MB | ~299 MB |
| base | 142 MB | ~410 MB |
| **small** | 466 MB | **~889 MB — out** |
| medium | 1.5 GB | ~2.1 GB |

**`base.en`** — the English-only model, ~410 MB, roughly 2–4 s for a 10 s clip on
four A76 cores. `small` alone would eat most of the budget.

English-only is the decision for now, so the multilingual variants don't apply.
Still worth keeping **several sizes on the card** and picking at load time
depending on how much RAM is free — the card is cheap, RAM is not. Which size is
right is a measurement, not a decision.

## Expected timings
Decode speed is memory-bandwidth-bound. The Pi 5's LPDDR4X gives ~17 GB/s on
paper, ~5–6 GB/s measured for a plain copy; llama.cpp lands in between.

| | |
|---|---|
| Q8_0, 835 MB | ~12 tok/s |
| Q4_K_M, 532 MB | ~18 tok/s |

So a 200-token reading is roughly **17 s** at Q8, ~11 s at Q4, plus 2–4 s to
transcribe.

Treat these as an upper bound. They come from a Pi 5 benchmark of a *dense* model
where decode was bandwidth-limited at ~10 GB/s, and the linear-attention path is
less optimised on ARM than plain matrix multiplication. Nobody has published
numbers for this model on a Pi.

## Why "almost fits" is not a thing
Decoding touches **every weight on every token**. If the model doesn't fit, mmap
re-reads it from the card each token: 900 MB at SD speeds is **10–18 seconds per
token**. There is no graceful degradation — it works, or it is unusable.

Two flags that look like escape hatches and aren't. Both are now spelled
`-lm/--load-mode`; `--no-mmap` and `--mlock` still work but are deprecated.

- **`--load-mode none`** (old `--no-mmap`) makes the weights anonymous memory, so
  they go to *swap* instead of being dropped. Measured cost when that happens:
  **25 → 7.5 tok/s.** On SD it's also 4K random writes, which is the worst thing
  you can do to a card.
- **`--load-mode mlock`** pins them: silent OOM kill if they don't fit, and it now
  implies mmap, so it can double-count.

Leave it on `auto`. Note the default isn't lazy — llama.cpp maps with
`MAP_POPULATE`, so every page is touched at load.

## Whisper is different: it doesn't mmap at all
`whisper.cpp` reads the whole model into ordinary anonymous memory — there is no
mmap anywhere in it, and no flag to change that.

Two consequences. Its memory *can* be compressed by zram, unlike llama.cpp's
weights. And it can be swapped out rather than dropped, so it competes for the
same pages differently.

## llama.cpp supports this model properly
Qwen3.5 is a first-class architecture in llama.cpp under the name **`qwen35`** —
its own graph, its own hybrid KV cache handling the 18-recurrent/6-attention
split, and a registered converter. Official GGUFs have existed since April 2026,
so none of this is a bet.

**The tied embeddings are why Q8 fits.** Because `tie_word_embeddings` is true
there is no separate output matrix in the GGUF at all — that alone saves ~258 MB
in Q8_0. Without it the file would be over a gigabyte.

**The vision tower is dropped by default.** Conversion emits text-only; the ViT
only appears if you explicitly run a second `mmproj` pass. Skipping it saves
~205 MB. The adapter was trained on text, so nothing is lost.

### Two traps
**Never build with Vulkan.** The Pi 5's V3D backend is broken in llama.cpp, and
this model specifically returns all-NaN logits on Vulkan while the same build
works on CPU. Build with `-DGGML_CUDA=OFF`, CPU only.

**Pass `--no-mtp` when converting our own merged model.** Qwen3.5 carries an
extra speculative-decoding head (`blk.24`), and converting *fine-tuned, merged*
checkpoints is a known failure mode when its layer count doesn't survive the
merge. Official weights convert cleanly; ours are the case that breaks.

One other known converter bug doesn't touch us — it only triggers when a model's
key and value head counts differ, and at 0.8B both are 16.

### Reasoning is off by default
Small Qwen3.5 models ship with thinking disabled. To let it deliberate before a
reading: `--chat-template-kwargs '{"enable_thinking":true}'`. Whether that helps
a tarot reading or just costs 20 seconds is worth testing.

## Settings to start from
```
-c 4096 -b 256 -ub 64 -cram 0 --no-warmup
```
`-ub 64` is the one that matters — it's worth ~440 MB against the default.
Context can be generous since it's only 12 KiB/token; no need for `-ctk`/`-ctv`
here. `-cram 0` turns off the prompt cache we have no use for, and `--no-warmup`
skips a startup pass that touches everything.

## What to measure first
**`-fitp on` prints llama.cpp's own memory estimate before running** — the
cheapest possible check on everything above. `--fit` is on by default and will
already shrink unset parameters to make things fit, which can silently change
your context length; `-fitp` is how you see it happen.

Then `/usr/bin/time -v llama-cli …` for maximum resident set size, and llama.cpp's
own startup lines: `KV self size`, `compute buffer size`, and whether the model
buffer says `CPU_Mapped` (mmap working) or plain `CPU` (copied into anonymous RAM).

## If it turns out not to fit
Ranked by what they cost us:

1. Smaller quant, or `-ub 32`
2. `llama-server --sleep-idle-seconds N` — unloads the model and its KV cache
   while idle and reloads on the next request. Measured elsewhere at 44 GB → 0.4 GB.
   Keeps a server up without keeping the weights resident.
3. Move the model off the SD card. 4K random reads — exactly what mmap eviction
   generates — run **9.9 MB/s on a good microSD versus 65 MB/s on NVMe**. That
   ~7× is the difference between thrashing being survivable and not. Costs space
   and money we don't have, so this is a last resort, not a plan.

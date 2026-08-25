# qwen3_5_0.8b_v2_q8

The English adapter, v2, fused into Qwen3.5-0.8B and quantized to 8 bits in MLX
format. 782 MB, so the weights are not here and never will be — this repo is text
only, and the `adapters/` tree still carries the Git LFS pointers left behind when
the LFS history was reset, which is why nothing in it can be loaded.

**The weights live at**
`~/Library/CloudStorage/GoogleDrive-biryuzabear@gmail.com/My Drive/Projects/Tarot Device/qwen3_5_0.8b_v2_q8`

What is committed here is the light half that decides how the weights must be
called: `config.json`, `tokenizer_config.json` and `chat_template.jinja`. Pinning
the template was an open question in docs/SESSION.md, because a drift between the
template used in training and the one used at inference degrades every reading
without producing an error. This is that pin.

## The template is not optional

Measured on this export: prompting it with the bare training string — the exact
`<question> Cards: 1. ...` the fine-tune was fed — returns **an empty completion**.
The same prompt through `apply_chat_template` returns a full reading. The adapter
was trained through MLX-LM's chat path, so the `<|im_start|>` scaffolding is part of
what it learned.

Two consequences, both corrections to docs/SESSION.md §4:

- The local reader must go through a chat endpoint, not `llama-server`'s
  `/completion`. The spec chose `/completion` to stop a template injecting a system
  turn; this template injects none — the prompt begins straight at
  `<|im_start|>user` — so the reason does not apply to this export.
- The template opens a `<think>` block, and what happens next decides where the
  reading lands. Sometimes the model closes it immediately and writes the reading
  after, so the output begins `</think>` and the text arrives in `content`. More
  often it does not close it at all, and a server that understands reasoning models
  files the entire answer under `reasoning` instead — **measured: two responses in
  three came back with `content` empty and a couple of hundred events of
  `reasoning`**, which on the glass was a reading that simply never appeared.

  The adapter does not reason. The block is scaffolding it was trained through. So
  a client must read whichever field carries text — `content`, `reasoning` or
  `reasoning_content` — and strip the tag if it is there. Sending
  `chat_template_kwargs: {"enable_thinking": false}` helps where the server honours
  it, but the field fallback is what actually makes it reliable.

## Measured, on this Mac

| | |
|---|---|
| load | 1.1 s |
| generation | ~177 tok/s |
| a three-card reading | 111 words in 0.7 s |

All three drawn cards were named, in the trained voice. The Pi will be far slower;
that number is the one that matters and it is still unmeasured.


## GGUF for the deck — half done, 2026-08-26

The Pi runs `llama.cpp`, which reads GGUF; the export above is MLX, which is
Apple-only. So the weights have to be carried across, and the route is
dequantize, convert, requantize — not because anything is lossy-clever about it,
but because MLX 8-bit and GGUF Q8_0 are different containers with no direct path.

**Done:** the MLX export dequantized to bfloat16 and converted to GGUF.

```
# on the Mac, from the repo root
SRC="$HOME/Library/CloudStorage/GoogleDrive-biryuzabear@gmail.com/My Drive/Projects/Tarot Device/qwen3_5_0.8b_v2_q8"
.mlx/bin/python -m mlx_lm convert --hf-path "$SRC" --mlx-path qwen35-bf16 -d --dtype bfloat16

python3 -m venv conv-venv
./conv-venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
./conv-venv/bin/pip install -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
./conv-venv/bin/python llama.cpp/convert_hf_to_gguf.py qwen35-bf16 \
    --outfile tarot-v2-bf16.gguf --outtype bf16
```

`llama.cpp` knows this architecture — `Qwen3_5ForConditionalGeneration`, 24 layers
of which 18 are `linear_attention` and 6 `full_attention`. The conversion produced
320 tensors and 1.5 GB without complaint.

**The result is parked next to the MLX weights**, since the repo is text only:
`.../Tarot Device/tarot-v2-bf16.gguf`, 1.51 GB.

**Left to do**, and none of it is on the laptop:

1. Quantize to Q8_0. `llama-quantize` comes with the Pi's own `llama.cpp` build,
   so it happens there rather than needing cmake on the Mac:
   `~/llama.cpp/build/bin/llama-quantize tarot-v2-bf16.gguf tarot-v2-q8_0.gguf Q8_0`
   Expect about 800 MB. `docs/RUNTIME.md` budgets the deck around Q8_0, and
   1.5 GB of bfloat16 will not sit comfortably in 2 GB beside Whisper.
2. Serve it: `llama-server -m tarot-v2-q8_0.gguf --port 8080`.
3. Point the deck at it. The chat endpoint, not `/completion` — for the reason
   above: this template is part of what the adapter learned.
   `TAROTDECK_LOCAL_CHAT_URL=http://127.0.0.1:8080/v1 TAROTDECK_LOCAL_MODEL=tarot-v2`
4. Then measure. `docs/PROGRESS.md` still lists inference time as the assumption
   that could invalidate the most, and nothing about it has been measured on the
   Pi — only Whisper has.

**Unverified:** whether a GGUF round-trip preserves what the fine-tune learned.
The dequantize-requantize path is lossy twice over, and nobody has compared a
reading from the MLX export against one from the GGUF.

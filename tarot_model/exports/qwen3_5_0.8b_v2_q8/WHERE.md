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

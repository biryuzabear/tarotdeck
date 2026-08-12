import argparse
import json
import os
import re
from pathlib import Path
from openai import OpenAI
from rapidfuzz import fuzz

# languages where morphological changes require fuzzy matching
FUZZY_LANGS = {"ru", "pl"}

_mlx_model = None
_mlx_tokenizer = None

def _load_local(model_id):
    global _mlx_model, _mlx_tokenizer
    if _mlx_model is None:
        from mlx_lm import load
        print(f"Loading local model: {model_id}")
        _mlx_model, _mlx_tokenizer = load(model_id)
    return _mlx_model, _mlx_tokenizer

def _strip_thinking(text):
    # strip complete thinking block
    text = re.sub(r"<\|channel\>thought.*?<channel\|>", "", text, flags=re.DOTALL)
    # strip incomplete thinking block (cut off before closing tag)
    text = re.sub(r"<\|channel\>thought.*$", "", text, flags=re.DOTALL)
    return text.strip()

def _local_generate(model_id, prompt_text):
    from mlx_lm import generate
    model, tokenizer = _load_local(model_id)
    messages = [
        {"role": "system", "content": "You are a translator. Output only the translated text, nothing else."},
        {"role": "user", "content": prompt_text},
    ]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    response = generate(model, tokenizer, prompt=prompt, max_tokens=8192, verbose=False)
    return _strip_thinking(response)

_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

LANGUAGES = {
    "de": {"name": "German",     "cards": "Karten",  "upright": "aufrecht",     "reversed": "umgekehrt"},
    "fr": {"name": "French",     "cards": "Cartes",  "upright": "à l'endroit",  "reversed": "renversée"},
    "es": {"name": "Spanish",    "cards": "Cartas",  "upright": "al derecho",   "reversed": "invertida"},
    "it": {"name": "Italian",    "cards": "Carte",   "upright": "dritta",       "reversed": "rovesciata"},
    "pt": {"name": "Portuguese", "cards": "Cartas",  "upright": "direita",      "reversed": "invertida"},
    "ru": {"name": "Russian",    "cards": "Карты",   "upright": "прямо",        "reversed": "перевёрнуто"},
    "pl": {"name": "Polish",     "cards": "Karty",   "upright": "prosto",       "reversed": "odwrócona"},
}

CARD_RE = re.compile(r'(\d+\. )(.+?) \((upright|reversed)\) \[([^\]]+)\]')


def load_card_files(lang_code):
    base = Path(f"dataset/{lang_code}")
    names, upright, reversed_ = {}, {}, {}
    for line in (base / "card_names.txt").read_text().splitlines():
        if "=" in line:
            en, tr = line.split("=", 1)
            names[en.strip()] = tr.strip()
    for line in (base / "upright.txt").read_text().splitlines():
        if "=" in line:
            card, kw = line.split("=", 1)
            upright[card.strip()] = kw.strip()
    for line in (base / "reversed.txt").read_text().splitlines():
        if "=" in line:
            card, kw = line.split("=", 1)
            reversed_[card.strip()] = kw.strip()
    return names, upright, reversed_


def rebuild_user_message(content, names, upright, reversed_, lang):
    cfg = LANGUAGES[lang]

    def replace_card(m):
        num, en_name, direction, _ = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
        tr_name = names.get(en_name, en_name)
        keywords = (upright if direction == "upright" else reversed_).get(tr_name, "")
        tr_direction = cfg["upright"] if direction == "upright" else cfg["reversed"]
        return f"{num}{tr_name} ({tr_direction}) [{keywords}]"

    # split question from cards block
    cards_pos = content.find(" Cards: ")
    if cards_pos == -1:
        return content
    question = content[:cards_pos]
    cards_block = content[cards_pos + len(" Cards: "):]
    rebuilt_cards = CARD_RE.sub(replace_card, cards_block)
    return f"{{QUESTION}} {cfg['cards']}: {rebuilt_cards}"


def translate_one(text, lang_name, provider, client, local_model, label=""):
    prompt = f"""Translate the following tarot-related text to {lang_name}.
Return ONLY the translated text, nothing else. Keep the same mystical, intimate tone.
Do not translate card names or keywords in brackets — those are handled separately.

{text}"""
    if label:
        print(f"    → {label}", flush=True)
    if provider == "local":
        return _local_generate(local_model, prompt)
    model_id = "gemini-2.5-flash" if provider == "gemini" else "gpt-4.1-mini"
    result = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content.strip()


def translate_texts(client, texts, lang_name, provider="local", local_model=None, labels=None):
    if provider == "local":
        return [translate_one(t, lang_name, provider, client, local_model, label=labels[i] if labels else "") for i, t in enumerate(texts)]

    # API providers: batch in one call for efficiency
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    prompt = f"""Translate the following tarot-related texts to {lang_name}.
Each text is numbered. Return ONLY the translations, numbered the same way.
Keep the same mystical, intimate tone. Do not translate card names or keywords in brackets.

{numbered}"""
    model_id = "gemini-2.5-flash" if provider == "gemini" else "gpt-4.1-mini"
    result = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = result.choices[0].message.content.strip()
    parts = []
    for line in raw.splitlines():
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            parts.append(m.group(1).strip())
    if len(parts) != len(texts):
        parts = [p.strip() for p in raw.split("\n") if p.strip()]
    return parts


def validate_card_names(assistant_text, card_names_in_reading, lang, example_idx):
    """Check translated card names appear in assistant response. Returns list of missing card names."""
    fuzzy = lang in FUZZY_LANGS
    missing = []
    for card in card_names_in_reading:
        if fuzzy:
            # partial_ratio handles inflected forms (Шут → Шута, Шутом etc.)
            score = fuzz.partial_ratio(card.lower(), assistant_text.lower())
            found = score >= 80
        else:
            found = card.lower() in assistant_text.lower()
        if not found:
            missing.append(card)
    return missing


def process_batch(client, batch, names, upright, reversed_, lang, lang_name, provider="gemini", local_model=None, start_idx=0):
    questions = []
    assistant_texts = []
    card_names_per_example = []

    for ex in batch:
        user_msg = next(m["content"] for m in ex["messages"] if m["role"] == "user")
        cards_pos = user_msg.find(" Cards: ")
        questions.append(user_msg[:cards_pos] if cards_pos != -1 else user_msg)
        assistant_texts.append(next(m["content"] for m in ex["messages"] if m["role"] == "assistant"))

        # collect translated card names used in this example
        tr_cards = []
        for m in CARD_RE.finditer(user_msg[cards_pos:] if cards_pos != -1 else ""):
            en_name = m.group(2).strip()
            tr_cards.append(names.get(en_name, en_name))
        card_names_per_example.append(tr_cards)

    all_texts = questions + assistant_texts
    labels = [f"#{start_idx+i} question" for i in range(len(questions))] + \
             [f"#{start_idx+i} response" for i in range(len(assistant_texts))]
    translated = translate_texts(client, all_texts, lang_name, provider=provider, local_model=local_model, labels=labels)
    tr_questions = translated[:len(questions)]
    tr_assistants = translated[len(questions):]

    results = []
    warnings = []
    for i, ex in enumerate(batch):
        user_msg = next(m["content"] for m in ex["messages"] if m["role"] == "user")
        rebuilt = rebuild_user_message(user_msg, names, upright, reversed_, lang)
        rebuilt = rebuilt.replace("{QUESTION}", tr_questions[i].strip())
        tr_response = tr_assistants[i].strip()

        missing = validate_card_names(tr_response, card_names_per_example[i], lang, start_idx + i)
        if missing:
            warnings.append({"example": start_idx + i, "missing_cards": missing, "response": tr_response[:120]})

        results.append({"messages": [
            {"role": "user",      "content": rebuilt},
            {"role": "assistant", "content": tr_response},
        ]})
    return results, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=list(LANGUAGES.keys()))
    parser.add_argument("--input",  default="dataset/en/dataset_en.jsonl")
    parser.add_argument("--output", default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--provider", choices=["gemini", "openai", "local"], default="local")
    parser.add_argument("--local-model", default=str(Path.home() / ".cache/huggingface/hub/models--Unbabel--Tower-Plus-9B-MLX-4bit"))
    args = parser.parse_args()

    cfg = LANGUAGES[args.lang]
    output = args.output or f"dataset/{args.lang}/dataset_{args.lang}.jsonl"

    client = None
    if args.provider == "gemini":
        client = OpenAI(
            api_key=os.environ.get("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    elif args.provider == "openai":
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    names, upright, reversed_ = load_card_files(args.lang)

    examples = [json.loads(l) for l in Path(args.input).read_text().splitlines() if l.strip()]
    total = len(examples)
    print(f"Translating {total} examples to {cfg['name']} → {output}")

    done = 0
    all_warnings = []
    with open(output, "w") as f:
        for i in range(0, total, args.batch_size):
            batch = examples[i:i + args.batch_size]
            translated, warnings = process_batch(
                client, batch, names, upright, reversed_,
                args.lang, cfg["name"], args.provider, args.local_model,
                start_idx=i,
            )
            for ex in translated:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                f.flush()
            all_warnings.extend(warnings)
            done += len(batch)
            if warnings:
                print(f"  {done}/{total}  ⚠ {len(warnings)} card name issue(s) in this batch")
            else:
                print(f"  {done}/{total}")

    if all_warnings:
        warn_file = output.replace(".jsonl", "_warnings.json")
        with open(warn_file, "w") as f:
            json.dump(all_warnings, f, ensure_ascii=False, indent=2)
        print(f"\n⚠ {len(all_warnings)} examples with missing card names → {warn_file}")
        for w in all_warnings[:5]:
            print(f"  #{w['example']}: missing {w['missing_cards']}")
        if len(all_warnings) > 5:
            print(f"  ... and {len(all_warnings) - 5} more (see warnings file)")
    else:
        print("✓ All card names validated")

    print(f"Done → {output}")


if __name__ == "__main__":
    main()

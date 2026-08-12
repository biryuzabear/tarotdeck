import argparse
import os
import re
from datetime import datetime
from pathlib import Path
import mlx.core as mx
from mlx_lm import load, generate
from openai import OpenAI

_ROOT = Path(__file__).parent.parent

_env_file = _ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

LANG_CONFIG = {
    "en": {"cards": "Cards",  "upright": "upright",      "reversed": "reversed"},
    "de": {"cards": "Karten", "upright": "aufrecht",      "reversed": "umgekehrt"},
    "fr": {"cards": "Cartes", "upright": "à l'endroit",   "reversed": "renversée"},
    "es": {"cards": "Cartas", "upright": "al derecho",    "reversed": "invertida"},
    "it": {"cards": "Carte",  "upright": "dritta",        "reversed": "rovesciata"},
    "pt": {"cards": "Cartas", "upright": "direita",       "reversed": "invertida"},
    "ru": {"cards": "Карты",  "upright": "прямо",         "reversed": "перевёрнуто"},
    "pl": {"cards": "Karty",  "upright": "prosto",        "reversed": "odwrócona"},
}

EN_QUESTIONS = [
    "What does today have in store for me?",
    "Should I take this new job offer?",
    "Will this relationship heal or should I let it go?",
]

TRANSLATED_QUESTIONS = {
    "de": ["Was hält der heutige Tag für mich bereit?", "Soll ich dieses neue Jobangebot annehmen?", "Wird sich diese Beziehung heilen oder soll ich sie loslassen?"],
    "fr": ["Que me réserve la journée d'aujourd'hui?", "Devrais-je accepter cette nouvelle offre d'emploi?", "Cette relation va-t-elle guérir ou devrais-je la laisser partir?"],
    "es": ["¿Qué me depara hoy?", "¿Debería aceptar esta nueva oferta de trabajo?", "¿Sanará esta relación o debería dejarla ir?"],
    "it": ["Cosa mi riserva oggi?", "Dovrei accettare questa nuova offerta di lavoro?", "Questa relazione guarirà o dovrei lasciarla andare?"],
    "pt": ["O que hoje me reserva?", "Devo aceitar esta nova oferta de emprego?", "Este relacionamento vai sarar ou devo deixá-lo ir?"],
    "ru": ["Что ждёт меня сегодня?", "Стоит ли мне принять это предложение о работе?", "Исцелятся ли наши отношения или мне следует отпустить их?"],
    "pl": ["Co przyniesie mi dzisiejszy dzień?", "Czy powinienem przyjąć tę nową ofertę pracy?", "Czy ta relacja się uzdrowi, czy powinienem ją puścić?"],
}

TEST_CARDS = [
    [("The Tower", "upright")],
    [("Eight of Pentacles", "upright"), ("The Moon", "reversed")],
    [("Three of Swords", "upright"), ("The Star", "reversed"), ("Ace of Cups", "upright")],
]


def _load_card_files(lang):
    base = _ROOT / f"dataset/{lang}"
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


def _translate_questions(questions, lang_name):
    client = OpenAI(
        api_key=os.environ.get("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    result = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content":
            f"Translate these questions to {lang_name}. Return ONLY the translations numbered the same way.\n\n{numbered}"}],
    )
    raw = result.choices[0].message.content.strip()
    parts = []
    for line in raw.splitlines():
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            parts.append(m.group(1).strip())
    return parts if len(parts) == len(questions) else questions


def build_tests(lang):
    cfg = LANG_CONFIG[lang]
    if lang == "en":
        names = {c: c for cards in TEST_CARDS for c, _ in cards}
        upright = {}
        reversed_ = {}
        for line in (_ROOT / "dataset/upright.txt").read_text().splitlines():
            if "=" in line:
                card, kw = line.split("=", 1)
                upright[card.strip()] = kw.strip()
        for line in (_ROOT / "dataset/reversed.txt").read_text().splitlines():
            if "=" in line:
                card, kw = line.split("=", 1)
                reversed_[card.strip()] = kw.strip()
        questions = EN_QUESTIONS
    else:
        names, upright, reversed_ = _load_card_files(lang)
        if lang in TRANSLATED_QUESTIONS:
            questions = TRANSLATED_QUESTIONS[lang]
        else:
            lang_name = {"de": "German", "fr": "French", "es": "Spanish", "it": "Italian",
                         "pt": "Portuguese", "ru": "Russian", "pl": "Polish"}[lang]
            print(f"  Translating test questions to {lang_name} via Gemini...")
            questions = _translate_questions(EN_QUESTIONS, lang_name)

    tests = []
    labels = ["1-card — Card of the Day", "2-card — Job Offer", "3-card — Relationship"]
    for i, (question, cards) in enumerate(zip(questions, TEST_CARDS)):
        cards_str = " ".join(
            f"{j+1}. {names.get(card, card)} ({cfg['upright'] if d == 'upright' else cfg['reversed']}) [{(upright if d == 'upright' else reversed_).get(names.get(card, card), '')}]"
            for j, (card, d) in enumerate(cards)
        )
        tests.append({"label": labels[i], "prompt": f"{question} {cfg['cards']}: {cards_str}"})
    return tests


def run_tests(model_path, adapter_path, output_file, max_tokens, lang="en", lora_config=None):
    tests = build_tests(lang)

    print(f"Loading model: {model_path}")
    load_kwargs = {}
    if adapter_path:
        load_kwargs["adapter_path"] = adapter_path
    mx.metal.reset_peak_memory()
    model, tokenizer = load(model_path, **load_kwargs)

    results = []
    for test in tests:
        print(f"  Running: {test['label']} ...")
        messages = [{"role": "user", "content": test["prompt"]}]
        try:
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
        except Exception:
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        response = generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, verbose=False)
        response = re.sub(r"<think>.*?</think>\s*", "", response, flags=re.DOTALL)
        response = re.sub(r"<\|channel\>thought.*?<channel\|>", "", response, flags=re.DOTALL).strip()
        results.append((test["label"], test["prompt"], response))

    peak_mem_gb = mx.metal.get_peak_memory() / 1e9

    out = Path(output_file)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with out.open("w") as f:
        f.write(f"Model:      {model_path}\n")
        f.write(f"Adapter:    {adapter_path or 'none'}\n")
        f.write(f"Language:   {lang}\n")
        f.write(f"Date:       {timestamp}\n")
        f.write(f"Peak RAM:   {peak_mem_gb:.2f} GB\n")
        f.write(f"Max tokens: {max_tokens}\n")
        if lora_config and Path(lora_config).exists():
            f.write(f"LoRA config ({lora_config}):\n")
            for line in Path(lora_config).read_text().splitlines():
                if line.strip() and not line.startswith("#"):
                    f.write(f"  {line}\n")
        f.write("=" * 60 + "\n\n")
        for label, prompt, response in results:
            f.write(f"--- {label} ---\n")
            f.write(f"PROMPT:\n{prompt}\n\n")
            f.write(f"RESPONSE:\n{response}\n\n")
            f.write("-" * 60 + "\n\n")

    print(f"\nResults saved to: {output_file}")


def model_slug(model_path, adapter_path, lang):
    name = model_path.replace("/", "_").replace("-", "_").lower()
    if adapter_path:
        adapter = Path(adapter_path).name.replace("-", "_").lower()
        name = f"{name}__{adapter}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return Path(__file__).parent / f"test_results_{name}__{lang}__{timestamp}.txt"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-135M-Instruct")
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--lang", default="en", choices=list(LANG_CONFIG.keys()))
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-tokens",  type=int, default=250)
    parser.add_argument("--lora-config", default="lora_config.yaml")
    args = parser.parse_args()

    output = args.output or model_slug(args.model, args.adapter_path, args.lang)
    run_tests(args.model, args.adapter_path, output, args.max_tokens, args.lang, args.lora_config)

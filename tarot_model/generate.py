import argparse
import json
import os
import random
import time
from pathlib import Path
from openai import OpenAI, AuthenticationError

# load .env if present
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

CARDS = [
    # Major Arcana
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World",
    # Minor Arcana — Wands
    "Ace of Wands", "Two of Wands", "Three of Wands", "Four of Wands", "Five of Wands",
    "Six of Wands", "Seven of Wands", "Eight of Wands", "Nine of Wands", "Ten of Wands",
    "Page of Wands", "Knight of Wands", "Queen of Wands", "King of Wands",
    # Minor Arcana — Cups
    "Ace of Cups", "Two of Cups", "Three of Cups", "Four of Cups", "Five of Cups",
    "Six of Cups", "Seven of Cups", "Eight of Cups", "Nine of Cups", "Ten of Cups",
    "Page of Cups", "Knight of Cups", "Queen of Cups", "King of Cups",
    # Minor Arcana — Swords
    "Ace of Swords", "Two of Swords", "Three of Swords", "Four of Swords", "Five of Swords",
    "Six of Swords", "Seven of Swords", "Eight of Swords", "Nine of Swords", "Ten of Swords",
    "Page of Swords", "Knight of Swords", "Queen of Swords", "King of Swords",
    # Minor Arcana — Pentacles
    "Ace of Pentacles", "Two of Pentacles", "Three of Pentacles", "Four of Pentacles", "Five of Pentacles",
    "Six of Pentacles", "Seven of Pentacles", "Eight of Pentacles", "Nine of Pentacles", "Ten of Pentacles",
    "Page of Pentacles", "Knight of Pentacles", "Queen of Pentacles", "King of Pentacles",
]

SPREADS = [
    {"name": "Card of the Day",              "positions": ["Single card"]},
    {"name": "Simple Answer",                "positions": ["Single card"]},
    {"name": "Advice",                       "positions": ["Single card"]},
    {"name": "Pros & Cons",                  "positions": ["Pros", "Cons"]},
    {"name": "Two Paths",                    "positions": ["Path A", "Path B"]},
    {"name": "Mind & Heart",                 "positions": ["Mind", "Heart"]},
    {"name": "What to Do / Avoid",           "positions": ["Embrace this", "Avoid this"]},
    {"name": "Seen & Hidden",                "positions": ["What is visible", "What is concealed"]},
    {"name": "Past / Present / Future",      "positions": ["Past", "Present", "Future"]},
    {"name": "Situation / Action / Outcome", "positions": ["Situation", "Action", "Outcome"]},
    {"name": "Pros / Cons / Advice",         "positions": ["Pros", "Cons", "Advice"]},
    {"name": "Morning / Afternoon / Evening","positions": ["Morning energy", "Afternoon shift", "Evening reflection"]},
    {"name": "You / Them / The Bond",        "positions": ["You", "The other", "The connection"]},
    {"name": "Thesis / Antithesis / Synthesis", "positions": ["The force", "The counter-force", "The resolution"]},
]

DIRECTIONS = ["upright", "reversed"]

_PROMPT_FILE = Path(__file__).parent / "system_prompt.txt"
SYSTEM_PROMPT = _PROMPT_FILE.read_text()


def _load_meanings(filename):
    meanings = {}
    for line in (Path(__file__).parent / filename).read_text().splitlines():
        if "=" in line:
            card, keywords = line.split("=", 1)
            meanings[card.strip()] = keywords.strip()
    return meanings


_UPRIGHT = _load_meanings("dataset/upright.txt")
_REVERSED = _load_meanings("dataset/reversed.txt")


def draw_cards(n):
    cards = random.sample(CARDS, n)
    directions = [random.choice(DIRECTIONS) for _ in cards]
    return list(zip(cards, directions))


def build_user_message(spread):
    drawn = draw_cards(len(spread["positions"]))
    card_names = [card for card, _ in drawn]
    cards_block = "\n".join(
        f"{i+1}. {card} ({direction}) [{(_UPRIGHT if direction == 'upright' else _REVERSED).get(card, '')}]"
        for i, (card, direction) in enumerate(drawn)
    )
    meta = (
        f"Generate a training example for:\n"
        f"Spread: {spread['name']}\n"
        f"Positions: {', '.join(spread['positions'])}\n"
        f"Cards:\n{cards_block}"
    )
    return meta, card_names


PROVIDERS = {
    "openai": {
        "model": "gpt-5.5",
        "key_env": "OPENAI_API_KEY",
        "base_url": None,
    },
    "gemini": {
        "model": "gemini-2.5-flash",
        "key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
}


def generate_example(spread, provider="openai"):
    cfg = PROVIDERS[provider]
    client = OpenAI(
        api_key=os.environ.get(cfg["key_env"]),
        base_url=cfg["base_url"],
    )
    user_message, card_names = build_user_message(spread)
    response = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    raw = " ".join(response.choices[0].message.content.strip().splitlines())
    return json.loads(raw), card_names


def normalize(example):
    for msg in example["messages"]:
        text = msg["content"]
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")
        text = text.replace("—", ",").replace("–", "-")
        text = text.replace("…", "...")
        text = text.replace("*", "").replace("#", "").replace("_", "")
        text = " ".join(text.split())
        msg["content"] = text
    return example


def validate(example, card_names):
    assistant_text = next(
        m["content"] for m in example["messages"] if m["role"] == "assistant"
    )
    missing = [card for card in card_names if card.lower() not in assistant_text.lower()]
    return missing


def dry_run():
    spread = random.choice(SPREADS)
    user_message, card_names = build_user_message(spread)
    print("=" * 60)
    print("SYSTEM PROMPT:")
    print("=" * 60)
    print(SYSTEM_PROMPT)
    print()
    print("=" * 60)
    print("USER MESSAGE:")
    print("=" * 60)
    print(user_message)
    print()
    print("Expected cards:", card_names)


MAX_RETRIES_PER_EXAMPLE = 3
MAX_TOTAL_ATTEMPTS_MULTIPLIER = 5


def main(n_examples=1, output_file=None, provider="openai"):
    key_env = PROVIDERS[provider]["key_env"]
    if not os.environ.get(key_env):
        print(f"[fatal] {key_env} not set — add it to .env or export it")
        raise SystemExit(1)

    generated = 0
    rejected = 0
    skipped = 0
    attempts = 0
    max_attempts = n_examples * MAX_TOTAL_ATTEMPTS_MULTIPLIER

    while generated < n_examples:
        if attempts >= max_attempts:
            print(f"[fatal] Reached {max_attempts} total attempts — aborting")
            break
        spread = random.choice(SPREADS)
        for retry in range(MAX_RETRIES_PER_EXAMPLE):
            if retry > 0 and provider == "gemini":
                time.sleep(4)
            attempts += 1
            try:
                example, card_names = generate_example(spread, provider)
                example = normalize(example)
                missing = validate(example, card_names)
                if missing:
                    rejected += 1
                    print(f"  [rejected] {spread['name']} — missing: {missing} (attempt {retry+1}/{MAX_RETRIES_PER_EXAMPLE})")
                    continue
                generated += 1
                line = json.dumps(example)
                if output_file:
                    with open(output_file, "a") as f:
                        f.write(line + "\n")
                    print(f"  [ok] {generated}/{n_examples} — {spread['name']}")
                else:
                    print(line)
                break
            except AuthenticationError as e:
                print(f"  [fatal] Authentication failed — check your OPENAI_API_KEY")
                raise SystemExit(1)
            except Exception as e:
                rejected += 1
                print(f"  [error] {spread['name']} — {e} (attempt {retry+1}/{MAX_RETRIES_PER_EXAMPLE})")
        else:
            skipped += 1
            print(f"  [skipped] {spread['name']} — failed {MAX_RETRIES_PER_EXAMPLE} times, moving on")

    if output_file:
        print()
        print(f"Done. requested={n_examples} generated={generated} skipped={skipped} rejected={rejected} attempts={attempts}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print the prompt without calling the API")
    parser.add_argument("--provider", choices=list(PROVIDERS.keys()), required=True, help="API provider to use")
    parser.add_argument("--n", type=int, default=1, help="Number of examples to generate")
    parser.add_argument("--output", type=str, default=None, help="Output file (default: dataset/dataset_{provider}.jsonl)")
    args = parser.parse_args()

    output = args.output or f"dataset/dataset_{args.provider}.jsonl"

    if args.dry_run:
        dry_run()
    else:
        main(n_examples=args.n, output_file=output, provider=args.provider)

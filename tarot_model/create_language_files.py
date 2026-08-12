"""One-time script to generate card_names.txt, upright.txt, reversed.txt for each language."""
import json
import os
import time
from pathlib import Path
from openai import OpenAI

_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

client = OpenAI(
    api_key=os.environ.get("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

LANGUAGES = {
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "pl": "Polish",
}

def load_meanings(filepath):
    result = {}
    for line in Path(filepath).read_text().splitlines():
        if "=" in line:
            card, keywords = line.split("=", 1)
            result[card.strip()] = keywords.strip()
    return result

def ask_gemini(prompt):
    result = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content.strip()

def translate_card_names(cards, lang_name):
    prompt = f"""Translate these 78 Rider-Waite tarot card names to {lang_name}.
Return ONLY a JSON object mapping English name to {lang_name} name, nothing else.
Use the traditional/established tarot names in {lang_name} where they exist.

Cards:
{json.dumps(cards, ensure_ascii=False)}"""
    raw = ask_gemini(prompt)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def translate_keywords(card_name_map, meanings, lang_name, direction):
    entries = []
    for en_name, keywords in meanings.items():
        translated_name = card_name_map.get(en_name, en_name)
        entries.append(f"{en_name} ({translated_name}): {keywords}")

    prompt = f"""Translate these tarot card keywords to {lang_name}.
These are {direction} meanings — short words or phrases, not sentences.
Return ONLY a JSON object where key is the TRANSLATED card name and value is the translated keywords as a comma-separated string.
Keep the same number and style of keywords. Use natural {lang_name} tarot terminology.

{chr(10).join(entries)}"""
    raw = ask_gemini(prompt)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def generate_for_lang(lang_code, lang_name):
    out_dir = Path(f"dataset/{lang_code}")
    print(f"\n=== {lang_name} ({lang_code}) ===")

    upright = load_meanings("dataset/upright.txt")
    reversed_ = load_meanings("dataset/reversed.txt")
    cards = list(upright.keys())

    print("  Translating card names...")
    card_name_map = translate_card_names(cards, lang_name)

    lines = [f"{en}={translated}" for en, translated in card_name_map.items()]
    (out_dir / "card_names.txt").write_text("\n".join(lines) + "\n")
    print(f"  Saved card_names.txt ({len(lines)} entries)")

    print("  Translating upright keywords...")
    upright_translated = translate_keywords(card_name_map, upright, lang_name, "upright")

    lines = [f"{name}={kw}" for name, kw in upright_translated.items()]
    (out_dir / "upright.txt").write_text("\n".join(lines) + "\n")
    print(f"  Saved upright.txt ({len(lines)} entries)")

    print("  Translating reversed keywords...")
    reversed_translated = translate_keywords(card_name_map, reversed_, lang_name, "reversed")

    lines = [f"{name}={kw}" for name, kw in reversed_translated.items()]
    (out_dir / "reversed.txt").write_text("\n".join(lines) + "\n")
    print(f"  Saved reversed.txt ({len(lines)} entries)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=list(LANGUAGES.keys()), help="Language to generate (omit for all)")
    args = parser.parse_args()

    langs = {args.lang: LANGUAGES[args.lang]} if args.lang else LANGUAGES
    for code, name in langs.items():
        generate_for_lang(code, name)

    print("\nAll done.")

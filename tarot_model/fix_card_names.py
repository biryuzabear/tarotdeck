"""Post-process translated JSONL files to replace English card names with translated ones."""
import json
import re
import argparse
from pathlib import Path


def load_card_names(lang):
    mapping = {}
    path = Path(f"dataset/{lang}/card_names.txt")
    for line in path.read_text().splitlines():
        if "=" in line:
            en, tr = line.split("=", 1)
            mapping[en.strip()] = tr.strip()
    return mapping


def replace_card_names(text, mapping):
    # build extended mapping that also includes bare forms (without "The ")
    extended = {}
    for en_name, tr_name in mapping.items():
        extended[en_name] = tr_name
        if en_name.startswith("The "):
            extended[en_name[4:]] = tr_name  # also match "Star", "Moon", etc.

    # sort by length descending to avoid partial matches
    for en_name in sorted(extended.keys(), key=len, reverse=True):
        tr_name = extended[en_name]
        pattern = re.compile(r'\b' + re.escape(en_name) + r'\b', re.IGNORECASE)
        text = pattern.sub(tr_name, text)
    # strip orphaned "The " / "the " before Cyrillic
    text = re.sub(r'\b[Tt]he\s+(?=[А-ЯЁа-яё])', '', text)
    # strip brackets around card names that leaked into assistant response
    text = re.sub(r'\[([А-ЯЁа-яё][^\]]*)\]', r'\1', text)
    # manual fixes
    text = re.sub(r'\bRider[-–]Waite\b', 'Райдер-Уэйт', text, flags=re.IGNORECASE)
    text = re.sub(r'\bStill,', 'Тем не менее,', text)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True)
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    input_file = Path(args.input or f"dataset/{args.lang}/dataset_{args.lang}.jsonl")
    output_file = Path(args.output or str(input_file))

    mapping = load_card_names(args.lang)
    print(f"Loaded {len(mapping)} card name mappings for {args.lang}")

    lines = [l for l in input_file.read_text().splitlines() if l.strip()]
    fixed = 0
    results = []

    for line in lines:
        ex = json.loads(line)
        for msg in ex["messages"]:
            if msg["role"] == "assistant":
                original = msg["content"]
                msg["content"] = replace_card_names(original, mapping)
                if msg["content"] != original:
                    fixed += 1
        results.append(json.dumps(ex, ensure_ascii=False))

    output_file.write_text("\n".join(results) + "\n")
    print(f"Fixed {fixed}/{len(lines)} examples → {output_file}")


if __name__ == "__main__":
    main()

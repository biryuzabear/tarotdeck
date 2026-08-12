import json
import re
from pathlib import Path

def _load_meanings(filename):
    meanings = {}
    for line in (Path(__file__).parent / filename).read_text().splitlines():
        if "=" in line:
            card, keywords = line.split("=", 1)
            meanings[card.strip()] = keywords.strip()
    return meanings

_UPRIGHT = _load_meanings("dataset/upright.txt")
_REVERSED = _load_meanings("dataset/reversed.txt")

CARD_RE = re.compile(r'(\d+\. )([^(]+?) \((upright|reversed)\)')

def inject(text):
    def replace(m):
        num, card, direction = m.group(1), m.group(2).strip(), m.group(3)
        lookup = _UPRIGHT if direction == "upright" else _REVERSED
        keywords = lookup.get(card, "")
        suffix = f" [{keywords}]" if keywords else ""
        return f"{num}{card} ({direction}){suffix}"
    return CARD_RE.sub(replace, text)

def process_file(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)
    ok = skipped = 0
    with output_path.open("w") as out:
        for i, line in enumerate(input_path.read_text().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                example = json.loads(line)
                for msg in example["messages"]:
                    if msg["role"] == "user":
                        msg["content"] = inject(msg["content"])
                out.write(json.dumps(example) + "\n")
                ok += 1
            except Exception as e:
                skipped += 1
                print(f"  [skip] line {i}: {e}")
    print(f"{input_path.name} → {output_path.name}: {ok} ok, {skipped} skipped")

FILES = [
    ("dataset/dataset_openai.jsonl",  "dataset/dataset_openai_kw.jsonl"),
    ("dataset/dataset_gemini.jsonl",  "dataset/dataset_gemini_kw.jsonl"),
]

for src, dst in FILES:
    process_file(src, dst)

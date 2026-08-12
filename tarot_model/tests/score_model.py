import argparse
import json
import os
import re
import time
from pathlib import Path

from openai import OpenAI

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SCORES_DIR = Path(__file__).parent / "scores"

SCORING_PROMPT = """You are a strict evaluator of AI-generated tarot readings in {lang_name}. You are comparing multiple fine-tuned models, so scores MUST differentiate between them. Be critical. Evaluate the response in {lang_name} — fluency, tone and style should match native {lang_name} tarot reading conventions.

Score scale (use the full range — most outputs score 2-4, not 5):
1 = poor / broken
2 = mediocre, generic, or repetitive
3 = acceptable but forgettable
4 = good — concrete, evocative, on-tone
5 = exceptional — rare, only for truly striking lines

Score on these 4 dimensions:

1. card_accuracy — Does it correctly use the card meanings from the keywords in brackets? Reversed cards should be negative/challenging. Penalize if card meanings are wrong or ignored.
2. tone — Mystical, fateful, intimate, speaks to "you" directly. Penalize for being preachy ("you should"), instructional, or generic ("trust the process", "something is shifting").
3. imagery — Concrete vivid images ("black stone in the sky") vs vague filler ("the path ahead", "a necessary step"). Penalize hard for repetition or generic phrases.
4. coherence — Continuous prose, clear arc, strong fateful closing line. Penalize for abrupt endings, repetitive sentences, or losing the thread.

Return ONLY valid JSON, nothing else:
{{"card_accuracy": X, "tone": X, "imagery": X, "coherence": X, "overall": X, "note": "one specific criticism or praise"}}

Overall = weighted average (imagery × 0.35 + tone × 0.30 + coherence × 0.20 + card_accuracy × 0.15).

PROMPT:
{prompt}

RESPONSE:
{response}"""


def parse_test_file(path):
    text = Path(path).read_text()
    header = {}
    for line in text.splitlines()[:10]:
        if ":" in line and not line.startswith("="):
            k, v = line.split(":", 1)
            header[k.strip().lower()] = v.strip()

    tests = []
    blocks = re.split(r"--- (.+?) ---", text)
    for i in range(1, len(blocks), 2):
        label = blocks[i].strip()
        body = blocks[i + 1]
        prompt_m = re.search(r"PROMPT:\n(.+?)\n\nRESPONSE:", body, re.DOTALL)
        response_m = re.search(r"RESPONSE:\n(.+?)(?:\n-{20,}|$)", body, re.DOTALL)
        if prompt_m and response_m:
            tests.append({
                "label": label,
                "prompt": prompt_m.group(1).strip(),
                "response": response_m.group(1).strip(),
            })
    return header, tests


def score_response(client, prompt, response, lang_name="English"):
    msg = SCORING_PROMPT.format(prompt=prompt, response=response, lang_name=lang_name)
    result = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": msg}],
    )
    raw = result.choices[0].message.content.strip()
    # strip markdown code fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    raw = " ".join(raw.splitlines())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [warn] Bad JSON from Gemini: {raw[:200]}")
        raise


def avg_scores(all_scores):
    keys = ["card_accuracy", "tone", "imagery", "coherence", "overall"]
    return {k: round(sum(s[k] for s in all_scores) / len(all_scores), 2) for k in keys}


def find_latest_test_file(model, adapter_path):
    slug_model = model.replace("/", "_").replace("-", "_").lower()
    adapter_name = Path(adapter_path).name.replace("-", "_").lower()
    pattern = f"test_results_{slug_model}__{adapter_name}__*.txt"
    files = sorted(Path(__file__).parent.glob(pattern))
    return files[-1] if files else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter-path", required=True)
    parser.add_argument("--test-file", default=None)
    parser.add_argument("--lang", default="en")
    args = parser.parse_args()

    LANG_NAMES = {
        "en": "English", "de": "German", "fr": "French", "es": "Spanish",
        "it": "Italian", "pt": "Portuguese", "ru": "Russian", "pl": "Polish",
    }
    lang_name = LANG_NAMES.get(args.lang, "English")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[fatal] GEMINI_API_KEY not set")
        raise SystemExit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    test_file = args.test_file or find_latest_test_file(args.model, args.adapter_path)
    if not test_file:
        print(f"[fatal] No test file found for {args.model} / {args.adapter_path}")
        raise SystemExit(1)

    print(f"Scoring: {test_file}")
    header, tests = parse_test_file(test_file)

    if not tests:
        print("[fatal] Could not parse any test cases from file")
        raise SystemExit(1)

    per_test = []
    for test in tests:
        print(f"  Scoring: {test['label']} ...")
        scores = score_response(client, test["prompt"], test["response"], lang_name=lang_name)
        scores["label"] = test["label"]
        per_test.append(scores)
        time.sleep(2)

    averaged = avg_scores(per_test)

    result = {
        "model": args.model,
        "adapter": args.adapter_path,
        "lang": args.lang,
        "test_file": str(test_file),
        "date": header.get("date", ""),
        "peak_ram_gb": float(re.search(r"[\d.]+", header["peak ram"]).group()) if "peak ram" in header else None,
        "scores": averaged,
        "per_test": per_test,
    }

    SCORES_DIR.mkdir(exist_ok=True)
    slug_model = args.model.replace("/", "_").replace("-", "_").replace(".", "_").lower()
    if args.adapter_path:
        adapter_slug = Path(args.adapter_path).parent.name + "_" + Path(args.adapter_path).name
        out = SCORES_DIR / f"{slug_model}__{adapter_slug}__{args.lang}.json"
    else:
        out = SCORES_DIR / f"{slug_model}__{args.lang}.json"
    out.write_text(json.dumps(result, indent=2))

    print(f"\nScores saved to: {out}")
    print(f"\nAverage scores:")
    for k, v in averaged.items():
        print(f"  {k:<16} {v}")
    print(f"\nPer-test notes:")
    for t in per_test:
        print(f"  {t['label']}: {t.get('note', '')}")


if __name__ == "__main__":
    main()

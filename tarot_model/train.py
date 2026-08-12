import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ADAPTERS_DIR = Path("adapters")
LOGS_DIR = Path("logs")
SCORES_DIR = Path("tests/scores")

LANGS = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "pl": "Polish",
}

MODEL_SLUGS = {
    "HuggingFaceTB/SmolLM2-135M-Instruct": "smollm2_135m",
    "HuggingFaceTB/SmolLM2-360M-Instruct": "smollm2_360m",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct": "smollm2_1700m",
    "Qwen/Qwen3-0.6B":                     "qwen3_0.6b",
    "Qwen/Qwen3-1.7B":                     "qwen3_1.7b",
    "Qwen/Qwen3.5-0.8B":                   "qwen3_5_0.8b",
}


def model_slug(model):
    return MODEL_SLUGS.get(model) or model.split("/")[-1].replace("-", "_").lower()


def next_version(slug, lang):
    lang_dir = ADAPTERS_DIR / slug / lang
    if not lang_dir.exists():
        return 1
    existing = [int(d.name[1:]) for d in lang_dir.iterdir() if d.is_dir() and re.match(r"v\d+$", d.name)]
    return max(existing, default=0) + 1


def parse_log(log_path):
    if not log_path.exists():
        return None, None
    losses, peak_mem = [], None
    for line in log_path.read_text().splitlines():
        m = re.search(r"Val loss ([\d.]+)", line)
        if m:
            losses.append(float(m.group(1)))
        m = re.search(r"Peak memory: ([\d.]+) GB", line)
        if m:
            peak_mem = float(m.group(1))
    return (min(losses) if losses else None), peak_mem


def load_scores(model_slug, lang, version):
    pattern = f"*__{model_slug}_{version}__{lang}.json"
    files = list(SCORES_DIR.glob(pattern)) if SCORES_DIR.exists() else []
    if not files:
        return None, None
    data = json.loads(files[-1].read_text())
    return data.get("scores"), data.get("peak_ram_gb")


def render_section(rows, lang, lang_name):
    if not rows:
        return []
    rows.sort(key=lambda r: -(r["scores"]["overall"] if r["scores"] else 0) if r.get("scores") else float("inf"))
    sep = "─" * 105
    lines = [f"\n  {lang_name} ({lang})", sep,
             f"{'#':<4} {'Model':<22} {'Ver':<5} {'Val loss':<10} {'Train RAM':<11} {'Infer RAM':<11} {'Acc':<6} {'Tone':<6} {'Img':<6} {'Coh':<6} {'Overall'}",
             sep]
    for i, r in enumerate(rows, 1):
        loss_str = f"{r['loss']:.3f}" if r["loss"] else "no log"
        train_mem = f"{r['peak_mem']:.1f}GB" if r["peak_mem"] else "—"
        infer_mem = f"{r['infer_ram']:.1f}GB" if r.get("infer_ram") else "—"
        s = r["scores"]
        if s:
            acc, tone, img, coh, ov = f"{s['card_accuracy']:.1f}", f"{s['tone']:.1f}", f"{s['imagery']:.1f}", f"{s['coherence']:.1f}", f"{s['overall']:.1f}"
        else:
            acc = tone = img = coh = ov = "—"
        marker = " ◀ best" if i == 1 and r.get("scores") else ""
        lines.append(f"{i:<4} {r['model']:<22} {r['version']:<5} {loss_str:<10} {train_mem:<11} {infer_mem:<11} {acc:<6} {tone:<6} {img:<6} {coh:<6} {ov}{marker}")
    lines.append(sep)
    return lines


def list_all():
    if not ADAPTERS_DIR.exists():
        print("No adapters directory found.")
        return

    # collect rows grouped by language
    by_lang = {lang: [] for lang in LANGS}

    for model_dir in sorted(ADAPTERS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        for lang_dir in sorted(model_dir.iterdir()):
            if not lang_dir.is_dir() or lang_dir.name not in LANGS:
                continue
            lang = lang_dir.name
            for v_dir in sorted(lang_dir.iterdir()):
                if not v_dir.is_dir() or not re.match(r"v\d+$", v_dir.name):
                    continue
                log_path = LOGS_DIR / f"{model_dir.name}_{lang}_{v_dir.name}.txt"
                loss, peak_mem = parse_log(log_path)
                scores, infer_ram = load_scores(model_dir.name, lang, v_dir.name)
                by_lang[lang].append({
                    "model": model_dir.name,
                    "version": v_dir.name,
                    "loss": loss,
                    "peak_mem": peak_mem,
                    "scores": scores,
                    "infer_ram": infer_ram,
                    "path": str(v_dir),
                })

    # quantized models — put in en section for now
    if SCORES_DIR.exists():
        for score_file in sorted(SCORES_DIR.glob("quantized_*.json")):
            data = json.loads(score_file.read_text())
            model_name = Path(data["model"]).name
            by_lang["en"].append({
                "model": model_name + " [Q4]",
                "version": "—",
                "loss": None,
                "peak_mem": None,
                "scores": data.get("scores"),
                "infer_ram": data.get("peak_ram_gb"),
                "path": data["model"],
            })

    all_lines = ["# Model Comparison"]
    for lang, lang_name in LANGS.items():
        if by_lang[lang]:
            all_lines.extend(render_section(by_lang[lang], lang, lang_name))

    output = "\n".join(all_lines)
    print(output)

    out_path = Path("comparison.md")
    out_path.write_text(f"{output}\n")
    print(f"\nSaved to {out_path}")


def count_examples(data_dir):
    train_file = Path(data_dir) / "train.jsonl"
    if not train_file.exists():
        return None
    return sum(1 for line in train_file.read_text().splitlines() if line.strip())


def calc_iters(n_examples, batch_size, epochs):
    return max(1, (n_examples // batch_size) * epochs)


def main():
    parser = argparse.ArgumentParser(description="Train a LoRA adapter with mlx_lm")
    parser.add_argument("--model",          default="HuggingFaceTB/SmolLM2-135M-Instruct")
    parser.add_argument("--lang",           default="en", choices=list(LANGS.keys()))
    parser.add_argument("--data",           default=None)
    parser.add_argument("--epochs",         type=int,   default=5)
    parser.add_argument("--iters",          type=int,   default=None)
    parser.add_argument("--batch-size",     type=int,   default=16)
    parser.add_argument("--lr",             type=float, default=5e-5)
    parser.add_argument("--val-batches",    type=int,   default=10)
    parser.add_argument("--steps-per-eval", type=int,   default=100)
    parser.add_argument("--config",         default="lora_config.yaml")
    parser.add_argument("--save-every",              type=int, default=100)
    parser.add_argument("--grad-checkpoint",         action="store_true")
    parser.add_argument("--grad-accumulation-steps", type=int, default=1)
    parser.add_argument("--max-seq-length",          type=int, default=512)
    parser.add_argument("--list",                    action="store_true")
    args = parser.parse_args()

    if args.list:
        list_all()
        return

    LOGS_DIR.mkdir(exist_ok=True)

    slug = model_slug(args.model)
    version = next_version(slug, args.lang)
    adapter_path = ADAPTERS_DIR / slug / args.lang / f"v{version}"
    adapter_path.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{slug}_{args.lang}_v{version}.txt"

    data_dir = args.data or f"dataset/{args.lang}"
    effective_batch = args.batch_size * args.grad_accumulation_steps
    n_examples = count_examples(data_dir)
    if args.iters:
        iters = args.iters
        epochs_note = "manual"
    elif n_examples:
        iters = calc_iters(n_examples, effective_batch, args.epochs)
        epochs_note = f"{args.epochs} epochs × {n_examples} examples ÷ effective batch {effective_batch}"
    else:
        iters = 1000
        epochs_note = "fallback (train.jsonl not found)"

    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model",               args.model,
        "--train",
        "--data",                data_dir,
        "--iters",               str(iters),
        "--batch-size",          str(args.batch_size),
        "--learning-rate",       str(args.lr),
        "--adapter-path",        str(adapter_path),
        "--val-batches",         str(args.val_batches),
        "--steps-per-eval",      str(args.steps_per_eval),
        "--config",              args.config,
        "--max-seq-length",      str(args.max_seq_length),
        "--grad-accumulation-steps", str(args.grad_accumulation_steps),
        "--save-every",              str(args.save_every),
    ]
    if args.grad_checkpoint:
        cmd.append("--grad-checkpoint")

    print(f"Model:       {args.model}")
    print(f"Language:    {args.lang} ({LANGS[args.lang]})")
    print(f"Adapter:     {adapter_path}  (auto v{version})")
    print(f"Data:        {data_dir}")
    print(f"Config:      {args.config}")
    print(f"Iters:       {iters}  ({epochs_note})")
    print(f"Batch:       {args.batch_size} × accum {args.grad_accumulation_steps} = effective {effective_batch}  |  LR: {args.lr}  |  Max seq: {args.max_seq_length}")
    print(f"Log:         {log_file}")
    print("=" * 60)

    val_re = re.compile(r"Iter\s+\d+:\s+Val loss")

    with log_file.open("w") as log:
        log.write(f"model={args.model}\n")
        log.write(f"lang={args.lang}\n")
        log.write(f"adapter={adapter_path}\n")
        log.write(f"iters={iters} ({epochs_note})\n")
        log.write(f"batch={args.batch_size} accum={args.grad_accumulation_steps} effective_batch={effective_batch}\n")
        log.write(f"lr={args.lr} max_seq={args.max_seq_length} grad_checkpoint={args.grad_checkpoint}\n")
        log.write(f"lora_config={args.config} val_batches={args.val_batches} steps_per_eval={args.steps_per_eval}\n")
        log.write(f"cmd={' '.join(cmd)}\n")
        log.write("=" * 60 + "\n")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        peak_mem = None
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            if val_re.search(line) or "Iter 1:" in line:
                log.write(line)
                log.flush()
            m = re.search(r"Peak mem ([\d.]+) GB", line)
            if m:
                peak_mem = float(m.group(1))

        if peak_mem is not None:
            log.write(f"Peak memory: {peak_mem} GB\n")
            log.flush()

        process.wait()

    print(f"\nVal loss log saved to: {log_file}")
    print("\nAll versions:")
    list_all()


if __name__ == "__main__":
    main()

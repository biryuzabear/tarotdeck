"""Where a reading comes from. One interface, several sources.

A reader is anything that turns a prompt into a stream of text chunks. The deck
never learns which one it is holding — that is the whole point, because the
device has two programs, local and networked, and they differ only here.

Streaming is not decoration. The panel prints a word per fast refresh, so the
reading appears while it is still being generated rather than after.
"""

import json
import random
import time
from pathlib import Path

DATASET = Path(__file__).resolve().parent.parent / "tarot_model" / "dataset" / "en" / "dataset_en.jsonl"


class ReaderError(RuntimeError):
    """Raised when a reading cannot be produced. The deck shows this, not a traceback."""


class Reader:
    name = "reader"

    def stream(self, prompt):
        """Yield chunks of the reading as they arrive. Chunks are not words."""
        raise NotImplementedError

    def read(self, prompt):
        return "".join(self.stream(prompt))


class ScriptedReader(Reader):
    """Replays a real training answer at a chosen rate.

    Not a mock of the model's quality — it *is* the model's target output, taken
    from the data it was trained on, so the emulator shows real prose of the real
    length. Only the choosing is fake.
    """

    name = "scripted"

    def __init__(self, tokens_per_second=6.0, seed=None):
        self.rate = tokens_per_second
        self.random = random.Random(seed)
        self.examples = self._load()

    @staticmethod
    def _load():
        by_count = {1: [], 2: [], 3: []}
        for line in DATASET.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            user = record["messages"][0]["content"]
            count = user.count(") [")
            if count in by_count:
                by_count[count].append(record["messages"][1]["content"])
        return by_count

    def stream(self, prompt):
        count = max(1, min(3, prompt.count(") [")))
        pool = self.examples.get(count) or self.examples[1]
        if not pool:
            raise ReaderError("no scripted readings available")
        text = self.random.choice(pool)
        interval = 1.0 / self.rate if self.rate else 0.0
        for word in text.split(" "):
            if interval:
                time.sleep(interval)
            yield word + " "


class FailingReader(Reader):
    """For exercising the screens nobody designs until they happen."""

    name = "failing"

    def __init__(self, after=8, message="the network is gone"):
        self.after = after
        self.message = message

    def stream(self, prompt):
        for i in range(self.after):
            yield f"word{i} "
        raise ReaderError(self.message)

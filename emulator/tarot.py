"""The deck, and the prompt built from it.

The prompt shape is not a choice — it is the shape the model was trained on, and
it is reproduced here character for character:

    <question> Cards: 1. <Name> (upright) [<kw, kw, kw>] 2. <Name> (reversed) [...]

The keyword block is retrieval, not decoration: a 0.8B model cannot be trusted to
recall what the Five of Wands means, so the meaning is looked up by drawn card
and orientation and handed to it in the prompt. It was trained with those
keywords present, so leaving them out changes the distribution.

**The keywords are machinery and never reach the screen.** The querent sees the
cards; the block behind them is for the model alone.

Card names and keywords are read from the training data itself rather than
retyped, so the two can never drift apart.
"""

import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "tarot_model" / "dataset" / "en"

UPRIGHT = "upright"
REVERSED = "reversed"


def _table(name):
    out = {}
    for line in (DATA / name).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


class Deck:
    def __init__(self, seed=None):
        self.names = list(_table("card_names.txt"))
        self.upright = _table("upright.txt")
        self.reversed = _table("reversed.txt")
        self.random = random.Random(seed)
        missing = [n for n in self.names if n not in self.upright or n not in self.reversed]
        if missing:
            raise ValueError(f"cards without keywords: {missing}")

    def __len__(self):
        return len(self.names)

    def keywords(self, name, orientation):
        table = self.upright if orientation == UPRIGHT else self.reversed
        return table[name]

    def draw(self, count):
        picked = self.random.sample(self.names, count)
        return [
            (name, UPRIGHT if self.random.random() < 0.5 else REVERSED)
            for name in picked
        ]


def build_prompt(question, cards, deck):
    """The user message, exactly as the model saw it in training."""
    parts = [question.strip()]
    parts.append("Cards:")
    for i, (name, orientation) in enumerate(cards, 1):
        parts.append(f"{i}. {name} ({orientation}) [{deck.keywords(name, orientation)}]")
    return " ".join(parts)

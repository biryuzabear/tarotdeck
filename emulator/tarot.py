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

DATA = Path(__file__).resolve().parent.parent / "tarot_model" / "dataset"

UPRIGHT = "upright"
REVERSED = "reversed"

ENGLISH, RUSSIAN = "en", "ru"


def _table(language, name):
    out = {}
    for line in (DATA / language / name).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


class Deck:
    """The 78 cards, in whichever language is being read.

    A card's identity is always its English name — that is what the prompt is
    built from and what a style looks a plate up by. `card_names.txt` maps that
    identity onto the language's own name, and the keyword tables are keyed by
    whichever name that language uses, so both are reached through `localize`.
    """

    def __init__(self, seed=None, language=ENGLISH):
        self.language = language
        self.local = _table(language, "card_names.txt")
        self.names = list(_table(ENGLISH, "card_names.txt"))
        self.upright = _table(language, "upright.txt")
        self.reversed = _table(language, "reversed.txt")
        self.random = random.Random(seed)
        missing = [n for n in self.names if self.localize(n) not in self.upright]
        if missing:
            raise ValueError(f"cards without keywords in {language}: {missing[:3]}")

    def localize(self, name):
        return self.local.get(name, name)

    def __len__(self):
        return len(self.names)

    def keywords(self, name, orientation):
        table = self.upright if orientation == UPRIGHT else self.reversed
        return table[self.localize(name)]

    def draw(self, count):
        picked = self.random.sample(self.names, count)
        return [
            (name, UPRIGHT if self.random.random() < 0.5 else REVERSED)
            for name in picked
        ]


LABEL = {ENGLISH: "Cards:", RUSSIAN: "Карты:"}
TURN = {
    ENGLISH: {UPRIGHT: "upright", REVERSED: "reversed"},
    RUSSIAN: {UPRIGHT: "прямо", REVERSED: "перевёрнуто"},
}


def build_prompt(question, cards, deck):
    """The user message, exactly as the model saw it in training.

    Every part of it is the language's own — the label, the card names and the
    words for the two directions. The Russian rows were checked for this: they read
    `Карты: 1. Восьмёрка Кубков (перевёрнуто) [...]`, so an English scaffold around
    Russian keywords would be a shape the adapter never saw.
    """
    language = getattr(deck, "language", ENGLISH)
    turn = TURN.get(language, TURN[ENGLISH])
    parts = [question.strip(), LABEL.get(language, LABEL[ENGLISH])]
    for i, (name, orientation) in enumerate(cards, 1):
        parts.append(
            f"{i}. {deck.localize(name)} ({turn[orientation]}) "
            f"[{deck.keywords(name, orientation)}]"
        )
    return " ".join(parts)

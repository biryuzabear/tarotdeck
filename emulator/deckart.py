"""Real card art, loaded from the bought pixel deck instead of drawn.

The deck (Dallas / grijzelucht, see decks/pixel_tarot_deck_2/SOURCE.md) already
carries each card's name as part of the art, in the clear band under the figure —
same as a printed deck. So this style needs no name drawn over it; `cardface`
tracks that per style so `screens.py` knows not to.
"""

import functools
from pathlib import Path

from PIL import Image

DECK_ROOT = Path(__file__).resolve().parent.parent / "decks" / "pixel_tarot_deck_2" / "4gray"

_MAJOR_FILES = {
    "The Fool": "the_fool", "The Magician": "magician", "The High Priestess": "priestess",
    "The Empress": "empress", "The Emperor": "emperor", "The Hierophant": "hierophant",
    "The Lovers": "the_lovers", "The Chariot": "chariot", "Strength": "strength",
    "The Hermit": "the_hermit", "Wheel of Fortune": "wheel_of_fortune", "Justice": "justice",
    "The Hanged Man": "hanged_man", "Death": "death", "Temperance": "temperance",
    "The Devil": "the_devil", "The Tower": "the_tower", "The Star": "the_star",
    "The Moon": "the_moon", "The Sun": "the_sun", "Judgement": "judgement",
    "The World": "the_world",
}

_RANK_FILES = {
    "Ace": "ace", "Two": "2", "Three": "3", "Four": "4", "Five": "5", "Six": "6",
    "Seven": "7", "Eight": "8", "Nine": "9", "Ten": "10",
    "Page": "page", "Knight": "knight", "Queen": "queen", "King": "king",
}


def _stem(name):
    """The deck's filename stem for a card name, or None if it isn't in this deck."""
    if name in _MAJOR_FILES:
        return "major_arcana/" + _MAJOR_FILES[name]
    rank, _, suit = name.partition(" of ")
    if not suit or rank not in _RANK_FILES:
        return None
    return f"minor_arcana/{_RANK_FILES[rank]}_of_{suit.lower()}"


def available(name):
    return _stem(name) is not None


@functools.lru_cache(maxsize=None)
def _load(stem):
    return Image.open(DECK_ROOT / f"{stem}.png").convert("L")


def face(name, w, h, wires=True):
    """Same signature as the other card styles' draw functions; `wires` is unused."""
    stem = _stem(name)
    if stem is None:
        raise KeyError(f"{name!r} is not in this deck")
    return _load(stem).resize((w, h), Image.NEAREST)

from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL_ATTRIBUTIVE, ORDINAL_STEM
from .cardinal import sign, text

_SPECIAL = {"1/2": "ein halb", "½": "ein halb", "1/4": "ein Viertel", "¼": "ein Viertel", "3/4": "drei Viertel",
            "¾": "drei Viertel", "1/3": "ein Drittel", "⅓": "ein Drittel", "2/3": "zwei Drittel", "⅔": "zwei Drittel",
            "24/7": "vierundzwanzig sieben"}
_LOWER = "abcdefghijklmnopqrstuvwxyzäöüß"


def denominator() -> pynini.Fst:
    """``/22`` → `` Zweiundzwanzigstel``; denominators 3 to 100 and 1000 only, so ``12/345`` stays as written."""
    cap = pynini.union(*[pynini.cross(c, c.upper()) for c in _LOWER if c != "ß"]) + pynini.closure(
        pynini.union(*_LOWER))
    names = (pynini.union(*[str(d) for d in range(3, 101)], "1000") @ ORDINAL_STEM @ cap) + pynutil.insert("el")
    return (pynini.cross("/", " ") + names).optimize()


def fraction_words() -> pynini.Fst:
    """``3/4`` → ``drei Viertel``, ``1 1/2`` → ``eineinhalb``."""
    special = pynini.union(*[pynini.cross(k, v) for k, v in _SPECIAL.items()])
    numbers = [str(n) for n in range(1, 1000)]
    numerator = pynini.union(*numbers) @ CARDINAL_ATTRIBUTIVE
    # 1/4, 3/4, 1/3, 2/3 come out the same either way; 24/7 is said as written
    halves = (pynini.union(*numbers[1:]) @ numerator) + pynini.cross("/2", " Halbe")    # 3/2 → drei Halbe
    generic = pynini.union(numerator + denominator(), halves)
    generic = pynini.difference(pynini.union(*numbers) + "/" + pynini.closure(DIGIT, 1), "24/7") @ generic
    fraction = pynini.union(special, generic)
    # 1 1/2 → eineinhalb, 2 ½ → zweieinhalb: said as one word; other fractions after a space
    whole = pynini.union(*numbers) @ CARDINAL_ATTRIBUTIVE
    half = pynini.cross(pynini.union(" 1/2", " ½", "½"), "einhalb")
    mixed = whole + pynini.union(half, pynini.accep(" ") + generic)
    return pynini.union(fraction, mixed).optimize()


class FractionReader(Rule):
    """Fractions, see ``fraction_words``; a sign before one: ``-1/22`` → ``minus ein Zweiundzwanzigstel``."""

    name = "fraction"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(sign() + fraction_words())).optimize()

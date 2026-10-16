from __future__ import annotations

import pynini

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import ORDINAL
from .cardinal import text


def _roman(n: int) -> str:
    out = ""
    for value, sym in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += sym
            n -= value
    return out


def ordinal_words() -> pynini.Fst:
    """``1º`` / ``1°`` / ``1o`` → ``primo``, ``37ª`` / ``37a`` → ``trentasettesima``, ``1.º`` too."""
    number = NONZERO_DIGIT + pynini.closure(DIGIT, 0, 3)
    masculine = pynini.cross(pynini.union("º", "°", "o", ".º", ".°"), "o")
    feminine = pynini.cross(pynini.union("ª", "a", ".ª"), "a")
    return ((number + pynini.union(masculine, feminine)) @ ORDINAL).optimize()


def roman_century() -> pynini.Fst:
    """``XXI secolo`` → ``ventunesimo secolo``, ``XX sec.`` → ``ventesimo secolo``."""
    branches = []
    for n in range(1, 31):
        word = pynini.shortestpath(pynini.accep(f"{n}o") @ ORDINAL).string()
        branches.append(pynini.cross(_roman(n), word))
    century = pynini.union(" secolo", pynini.cross(" sec.", " secolo"))
    return (pynini.union(*branches) + century).optimize()


class OrdinalReader(Rule):
    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = ordinal_words()
        return self.wrap(text(pynini.union(self.number, roman_century()))).optimize()

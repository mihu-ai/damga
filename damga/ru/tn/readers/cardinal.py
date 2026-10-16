from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import ZERO
from ...numbers import cardinal, strip_groups
from .common import cased_gendered, text

_DIGIT_WORDS = {"0": ZERO[0], "1": "один", "2": "два", "3": "три", "4": "четыре", "5": "пять", "6": "шесть",
                "7": "семь", "8": "восемь", "9": "девять"}
DIGIT_BY_DIGIT = (pynini.union(*[pynini.cross(d, w) for d, w in _DIGIT_WORDS.items()])
                  + pynini.closure(pynutil.insert(" ") + pynini.union(*[pynini.cross(d, w) for d, w in _DIGIT_WORDS.items()]))).optimize()


class CardinalReader(Rule):
    """``25`` → двадцать пять, in the case of a preposition before it (``до 5`` → до пяти) and the gender of the noun
    after it (``21 тонна`` → двадцать одна тонна).  Leading zeros and very long numbers are read digit by digit."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        number = strip_groups()

        def build(case: str, gender: str) -> pynini.Fst:
            return number @ cardinal(case, gender)

        sign = pynini.closure(pynini.union(pynini.cross("-", "минус "), pynini.cross("−", "минус "),
                                           pynini.cross("+", "плюс ")), 0, 1)
        digits = pynini.union("0" + pynini.closure(DIGIT, 1), pynini.closure(DIGIT, 16)) @ DIGIT_BY_DIGIT
        numero = pynini.closure(pynini.cross(pynini.union("№", "№ "), "номер "), 0, 1)   # № 5 → номер пять
        return self.wrap(text(pynini.union(numero + sign + cased_gendered(build, variants=variants), digits))).optimize()

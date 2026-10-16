from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import DIGIT_WORD
from .cardinal import text


def spoken_decimal(number: pynini.Fst) -> pynini.Fst:
    """``due virgola cinque`` → ``2,5``, ``zero virgola zero cinque`` → ``0,05``."""
    digit = pynini.invert(DIGIT_WORD)
    digits = digit + pynini.closure(pynutil.delete(" ") + digit)
    after = pynini.union(digits, number @ (pynini.union(*"123456789") + pynini.closure(DIGIT, 0, 1)))
    integer = number @ pynini.closure(DIGIT, 1)
    return (integer + pynini.cross(" virgola ", ",") + after).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        self.number = spoken_decimal(number)
        scale = pynini.closure(pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS]), 0, 1)
        sign = pynini.closure(pynini.cross("meno ", "-"), 0, 1)
        return self.wrap(text(sign + self.number + scale)).optimize()

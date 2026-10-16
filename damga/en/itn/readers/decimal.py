from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import DIGIT_WORD
from .cardinal import text


def spoken_decimal(number: pynini.Fst) -> pynini.Fst:
    """``one point six`` → ``1.6``, ``point five`` → ``0.5``; digits after the point are said one by one."""
    digit = pynini.union(pynini.invert(DIGIT_WORD), pynini.cross("oh", "0"), pynini.cross("o", "0"))
    digits = digit + pynini.closure(pynutil.delete(" ") + digit)
    integer = number @ pynini.closure(DIGIT, 1)
    # "zero point fifteen": two digits said as one number
    after = pynini.union(digits, number @ (pynini.union(*"123456789") + DIGIT))
    return pynini.union(integer + pynini.cross(" point ", ".") + after,
                        pynini.cross("point ", "0.") + after).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        self.number = spoken_decimal(number)
        # "one and a half billion" → 1.5 billion; only before a scale word, a currency or "percent"
        self.half = ((number @ pynini.closure(DIGIT, 1)) + pynini.cross(" and a half", ".5")).optimize()
        scale_word = pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS])
        sign = pynini.closure(pynini.cross("minus ", "-"), 0, 1)
        # a decimal keeps its scale word (164.58 thousand), unlike a whole number (25,000)
        graph = pynini.union(sign + self.number + pynini.closure(pynini.union(scale_word, " thousand"), 0, 1),
                             self.half + scale_word)
        return self.wrap(text(graph)).optimize()

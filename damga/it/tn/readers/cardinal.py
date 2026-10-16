from __future__ import annotations

import pynini

from ....core.rules import DIGIT, Rule
from ....en.tn.readers.cardinal import text
from ...numbers import CARDINAL, DIGITS_SPOKEN, strip_thousands

__all__ = ["CardinalReader", "number_words", "text"]


def number_words() -> pynini.Fst:
    """``25.000`` / ``25000`` → ``venticinquemila``, ``2016`` → ``duemilasedici``; leading zeros and numbers past
    the billions are read digit by digit."""
    plain = strip_thousands() @ CARDINAL
    digits = pynini.union("0" + pynini.closure(DIGIT, 1), pynini.closure(DIGIT, 13)) @ DIGITS_SPOKEN
    return pynini.union(plain, digits).optimize()


class CardinalReader(Rule):
    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = number_words()
        sign = pynini.closure(pynini.union(pynini.cross("-", "meno "), pynini.cross("−", "meno "),
                                           pynini.cross("+", "più ")), 0, 1)
        return self.wrap(text(sign + self.number)).optimize()

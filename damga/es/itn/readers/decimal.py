from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import DIGIT_WORD
from .cardinal import text


def spoken_decimal(number: pynini.Fst) -> pynini.Fst:
    """``cinco coma cuatro`` → ``5,4``, ``doce punto dos`` → ``12.2``."""
    integer = number @ pynini.closure(DIGIT, 1)
    # after the comma: digits, pairs and triples in any mix, each written as said (``catorce quince`` → 1415)
    group = pynini.union(pynini.invert(DIGIT_WORD), number @ (pynini.union(*"123456789") + pynini.closure(DIGIT, 1, 2)))
    fraction = group + pynini.closure(pynutil.delete(" ") + group)
    return pynini.union(integer + pynini.cross(" coma ", ",") + fraction,
                        integer + pynini.cross(" punto ", ".") + fraction).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        self.number = spoken_decimal(number)
        scale = pynini.closure(pynini.union(" millones", " millón", " mil millones", " billones"), 0, 1)
        sign = pynini.closure(pynini.cross("menos ", "-"), 0, 1)
        return self.wrap(text(sign + self.number + scale)).optimize()

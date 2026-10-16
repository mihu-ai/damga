from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NON_QUOTE, Rule
from .cardinal import integer_field


def number_body(group: bool = True, group_four_digits: bool = True, scale_words: bool = False) -> pynini.Fst:
    """``integer="12" fractional="3" quantity="milyon"`` → ``12,3 milyon`` (+ the suffix)."""
    fractional = pynutil.delete(' fractional="') + pynutil.insert(",") + pynini.closure(DIGIT, 1) + pynutil.delete('"')
    quantity = pynutil.delete(' quantity="') + pynutil.insert(" ") + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
    tail = pynini.closure(fractional, 0, 1) + pynini.closure(quantity, 0, 1)
    return integer_field(group, group_four_digits, scale_words, tail=tail)

def optional_sign() -> pynini.Fst:
    return pynini.closure(pynutil.delete('negative="') + pynini.accep("-") + pynutil.delete('" '), 0, 1)

class DecimalWriter(Rule):
    name = "decimal"
    kind = "write"

    def build(self, variants: bool = False, **style: bool):
        dotted = pynutil.delete('dotted="') + pynini.closure(pynini.union(DIGIT, "."), 1) + pynutil.delete('"')
        return self.unwrap(pynini.union(optional_sign() + number_body(**style), dotted))

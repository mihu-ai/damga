from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NON_QUOTE, SIGMA, Rule
from .number import CARDINAL, DIGIT_BY_DIGIT


def optional_sign() -> pynini.Fst:
    return pynini.closure(pynutil.delete('negative="') + pynini.union("eksi", "artı") + pynutil.delete('"') + pynini.accep(" "), 0, 1)

def optional_suffix() -> pynini.Fst:
    return pynini.closure(pynutil.delete(' suffix="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"'), 0, 1)

def soften_dort() -> pynini.Fst:
    """``dört`` softens before a vowel-initial suffix: 4'ü → dördü, 4'e → dörde.  ``dörtü``/``dörte`` occur nowhere
    else, so the rewrite is safe; it is composed onto the small number writers, not the whole sentence."""
    return pynini.cdrewrite(pynini.cross("dört", "dörd"), "", pynini.union("ü", "e"), SIGMA)

class CardinalWriter(Rule):
    name = "cardinal"
    kind = "write"

    def build(self, variants: bool = False):
        integer = pynutil.delete('integer="') + (pynini.closure(DIGIT, 1) @ CARDINAL) + pynutil.delete('"')
        digits = pynutil.delete('digits="') + (pynini.closure(DIGIT, 1) @ DIGIT_BY_DIGIT) + pynutil.delete('"')
        return (self.unwrap(pynini.union(optional_sign() + integer, digits) + optional_suffix()) @ soften_dort()).optimize()

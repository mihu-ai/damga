from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, TR_LOWER, Rule
from ..writers.number import strip_thousand_dots


class CardinalReader(Rule):
    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        number = strip_thousand_dots() @ pynini.union(NONZERO_DIGIT + pynini.closure(DIGIT), "0")
        self.number = number.optimize()
        self.suffix = pynini.closure(pynutil.delete("'") + pynutil.insert(' suffix="') + pynini.closure(TR_LOWER, 1) + pynutil.insert('"'), 0, 1)
        # ``-5`` / ``+5``; a sign followed by a space (``+ 1``, ``− 2``) only for ``+`` and the minus the pre-hook marks
        # between operands, a ``- 2`` after a dash is left to the punctuation.
        spaced = pynini.union(pynini.cross("−", 'negative="eksi" '), pynini.cross("+", 'negative="artı" ')) + pynutil.delete(" ")
        sign = pynini.closure(pynini.union(pynini.cross("-", 'negative="eksi" '), pynini.cross("−", 'negative="eksi" '),
                                           pynini.cross("+", 'negative="artı" '), spaced), 0, 1)
        integer = pynutil.insert('integer="') + self.number + pynutil.insert('"')
        digits = pynutil.insert('digits="') + pynini.accep("0") + pynini.closure(DIGIT, 1) + pynutil.insert('"')
        fst = self.wrap(pynini.union(sign + integer + self.suffix, digits + self.suffix))
        self.unsigned = self.wrap(pynini.union(integer + self.suffix, digits + self.suffix))
        return fst

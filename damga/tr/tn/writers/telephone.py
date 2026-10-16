from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import optional_suffix, soften_dort
from .number import GROUP


class TelephoneWriter(Rule):
    name = "telephone"
    kind = "write"

    def build(self, variants: bool = False):
        d = DIGIT
        three = (d + d + d) @ GROUP
        two = (d + d) @ GROUP
        area0 = pynini.cross("0", "sıfır ") + three
        sp = pynini.accep(" ")
        domestic = area0 + sp + three + sp + two + sp + two
        intl = pynini.union(pynini.cross("+90", "artı doksan"), pynini.cross("0090", "sıfır sıfır doksan")) + sp + three + sp + three + sp + two + sp + two
        return (self.unwrap(pynutil.delete('number="') + pynini.union(domestic, intl) + pynutil.delete('"') + optional_suffix())
                @ soften_dort()).optimize()

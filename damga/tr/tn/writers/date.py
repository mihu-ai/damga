from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NON_QUOTE, Rule
from .cardinal import optional_suffix, soften_dort
from .number import CARDINAL


class DateWriter(Rule):
    name = "date"
    kind = "write"

    def build(self, variants: bool = False):
        num = pynini.union(pynutil.delete("0") + (DIGIT @ CARDINAL), (pynini.difference(DIGIT, "0") + pynini.closure(DIGIT)) @ CARDINAL)
        day = pynutil.delete('day="') + num + pynutil.delete('"')
        month = pynutil.delete('month="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
        month = month + pynini.closure(pynutil.delete(' month_digits="' + pynini.closure(DIGIT, 1) + '"'), 0, 1)
        year = pynutil.delete('year="') + num + pynutil.delete('"')
        sp = pynini.accep(" ")
        # A suffix on the month name keeps its apostrophe (``Haziran'da``); on a year it is joined to the number word.
        month_suffix = pynini.closure(pynutil.delete(' suffix="') + pynutil.insert("'") + pynini.closure(NON_QUOTE, 1)
                                      + pynutil.delete('"'), 0, 1)
        graph = pynini.union(
            day + sp + month + month_suffix,
            day + sp + month + sp + year + optional_suffix(),
            month + sp + year + optional_suffix(),
            year + optional_suffix(),
        )
        return (self.unwrap(graph) @ soften_dort()).optimize()

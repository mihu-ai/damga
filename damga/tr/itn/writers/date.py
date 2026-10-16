from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule
from .cardinal import optional_suffix


def _field(name: str, lead_space: bool) -> pynini.Fst:
    body = pynutil.delete(f'{name}="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
    return (pynutil.delete(" ") + pynutil.insert(" ") + body) if lead_space else body

class DateWriter(Rule):
    name = "date"
    kind = "write"

    def build(self, variants: bool = False):
        day = pynutil.delete('day="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
        month = pynutil.delete('month="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
        year = pynutil.delete('year="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
        text = pynutil.delete(' text="') + pynutil.insert(" ") + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
        sp = pynini.accep(" ")
        graph = pynini.union(
            day + sp + month + sp + year + pynini.union(pynini.closure(text, 0, 1), optional_suffix()),
            day + sp + month,
            month + sp + year + optional_suffix(),
            year + text,
            year + optional_suffix(),
        )
        return self.unwrap(graph.optimize())

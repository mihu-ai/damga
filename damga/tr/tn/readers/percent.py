from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from .cardinal import CardinalReader
from .decimal import DecimalReader


class PercentReader(Rule):
    name = "percent"
    kind = "read"

    def build(self, cardinal: CardinalReader, decimal: DecimalReader, variants: bool = False):
        integer = pynutil.insert('integer="') + cardinal.number + pynutil.insert('"')
        amount = pynini.union(integer, decimal.graph, decimal.dot_graph)
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        graph = pynini.union(
            pynini.cross("%", 'symbol="yüzde" ') + space + decimal.sign + amount,
            pynini.cross("‰", 'symbol="binde" ') + space + amount,
            pynutil.insert('symbol="yüzde" ') + amount + space + pynutil.delete("%"),
        )
        return self.wrap(graph + cardinal.suffix)

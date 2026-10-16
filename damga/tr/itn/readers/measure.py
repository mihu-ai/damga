from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.data import load_tsv
from ....core.rules import Rule, drop_space
from .cardinal import CardinalReader
from .decimal import DecimalReader

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "units.tsv"

class MeasureReader(Rule):
    name = "measure"
    kind = "read"

    def build(self, cardinal: CardinalReader, decimal: DecimalReader, variants: bool = False):
        units = pynini.union(*[pynini.cross(a, pynini.escape(b)) for a, b in load_tsv(DATA)])
        integer = pynutil.insert('integer="') + cardinal.graph_mixed + pynutil.insert('"')
        value = pynini.union(decimal.graph, integer)
        unit = pynutil.insert(' units="') + units + pynutil.insert('"')
        graph = decimal.optional_minus + value + drop_space + unit
        return self.wrap(graph.optimize())

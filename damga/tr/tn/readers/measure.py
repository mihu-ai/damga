from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.data import load_tsv
from ....core.rules import Rule
from .cardinal import CardinalReader
from .decimal import DecimalReader

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "units.tsv"

class MeasureReader(Rule):
    name = "measure"
    kind = "read"

    def build(self, cardinal: CardinalReader, decimal: DecimalReader, variants: bool = False):
        rows = load_tsv(DATA, lower_first=False)
        units = pynini.union(*[pynini.cross(pynini.escape(a), b) for a, b in rows if a != "m"])
        metre = pynini.cross("m", dict(rows)["m"])
        integer = pynutil.insert('integer="') + cardinal.number + pynutil.insert('"')
        space = pynutil.delete(pynini.closure(" ", 0, 1))

        def with_unit(amount: pynini.Fst, unit: pynini.Fst) -> pynini.Fst:
            return amount + space + pynutil.insert(' units="') + unit + pynutil.insert('"')

        # ``1.50 m`` is read like a height (``bir elli metre``), every other point decimal before a unit with ``nokta``.
        graph = pynini.union(with_unit(pynini.union(integer, decimal.graph, decimal.dot_graph), units),
                             with_unit(pynini.union(integer, decimal.graph, decimal.dot_metre_graph), metre))
        return self.wrap(decimal.sign + graph + cardinal.suffix)

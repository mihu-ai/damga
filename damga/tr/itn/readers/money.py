from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule, drop_space
from .cardinal import CardinalReader
from .decimal import DecimalReader

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "currency.tsv"

def _minor_two_digits(cardinal: CardinalReader) -> pynini.Fst:
    return pynini.union(cardinal.two_digit, DIGIT + DIGIT, pynutil.insert("0") + pynini.difference(DIGIT, "0"))

class MoneyReader(Rule):
    name = "money"
    kind = "read"

    def build(self, cardinal: CardinalReader, decimal: DecimalReader, variants: bool = False):
        rows = []
        for line in DATA.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("\t")]
            rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else None))

        integer = pynutil.insert('integer="') + cardinal.graph_mixed + pynutil.insert('"')
        two = _minor_two_digits(cardinal)
        branches = []
        for spoken, symbol, minor in rows:
            cur = pynutil.insert(f' currency="{symbol}"')
            unit = pynutil.delete(spoken)

            branches.append(integer + drop_space + unit + cur)
            branches.append(decimal.graph + drop_space + unit + cur)

            branches.append(integer + pynutil.delete(" buçuk ") + unit + pynutil.insert(' fractional="50"') + cur)
            if minor:
                frac = pynutil.insert(' fractional="') + two + pynutil.insert('"')

                branches.append(integer + drop_space + unit + pynutil.delete(pynini.closure(",", 0, 1)) + drop_space + frac + pynutil.delete(" " + minor) + cur)

                branches.append(pynutil.insert('integer="0"') + frac + pynutil.delete(" " + minor) + cur)
        graph = pynini.union(*branches)
        self.graph = graph.optimize()
        return self.wrap(decimal.optional_minus + self.graph)

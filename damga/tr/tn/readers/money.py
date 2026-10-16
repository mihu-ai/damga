from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import CardinalReader
from .decimal import DecimalReader

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "currency.tsv"

class MoneyReader(Rule):
    name = "money"
    kind = "read"

    def build(self, cardinal: CardinalReader, decimal: DecimalReader, variants: bool = False):
        rows = []
        for line in DATA.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            p = [x.strip() for x in line.split("\t")]
            rows.append((p[0], p[1], p[2] if len(p) > 2 else None))
        integer = pynutil.insert('integer="') + cardinal.number + pynutil.insert('"')
        minor = pynutil.delete(",") + pynutil.insert(' minor="') + DIGIT + DIGIT + pynutil.insert('"')
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        branches = []
        for sym, spoken, minor_spoken in rows:
            cur = pynutil.insert(f' currency="{spoken}"')
            unit = pynutil.delete(pynini.escape(sym))
            amount = pynini.union(integer, decimal.graph)
            if minor_spoken:
                amount = pynini.union(amount, integer + minor + pynutil.insert(f' minor_unit="{minor_spoken}"'))
            branches.append(amount + space + unit + cur)
            # ``$ 5``, ``USD 100``: only a symbol or an ISO code comes before the amount.  ``lira`` / ``TL`` never do in
            # Turkish, and ``… bin lira 2023'ten …`` is a year after an amount, not 2023 liras.
            if not sym.isalpha() or (sym.isupper() and len(sym) == 3):
                branches.append(unit + space + amount + cur)
        return self.wrap(decimal.sign + pynini.union(*branches) + cardinal.suffix)

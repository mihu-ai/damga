from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import cardinal, fraction, strip_groups
from .common import cased, text


class DecimalReader(Rule):
    """``3,5`` → три целых и пять десятых, ``до 2,5`` → до двух целых и пяти десятых."""

    name = "decimal"
    kind = "read"

    def build(self, variants: bool = False):
        decimal = strip_groups() + "," + pynini.closure(DIGIT, 1, 6)
        sign = pynini.closure(pynini.union(pynini.cross("-", "минус "), pynini.cross("−", "минус ")), 0, 1)
        reading = cased(lambda case: decimal @ fraction(case), variants=variants)
        if variants:
            reading = pynini.union(reading, pynutil.add_weight(cased(spoken, variants=True), 0.5))
        return self.wrap(text(sign + reading)).optimize()


def spoken(case: str, gender: str = "m") -> pynini.Fst:
    """How a decimal is said in speech (variants mode): ``1,5`` → полтора (полторы before a feminine
    noun), ``2,5`` → два с половиной, ``3,25`` → три запятая двадцать пять."""
    whole = strip_groups() @ cardinal(case, gender)
    poltora = ("полторы" if gender == "f" else "полтора") if case in ("nom", "acc") else "полутора"
    half = pynini.union(pynini.cross(pynini.union("1,5", "1.5"), poltora),
                        (pynini.difference(pynini.project(strip_groups(), "input"), "1") @ strip_groups()
                         @ cardinal(case, gender)) + pynini.cross(pynini.union(",5", ".5"), " с половиной"))
    after = pynini.union(pynini.union(*"123456789"), pynini.union(*"123456789") + DIGIT) @ cardinal("nom", "f")
    comma = whole + pynini.cross(",", " запятая ") + after
    return pynini.union(half, pynutil.add_weight(comma, 0.4)).optimize()

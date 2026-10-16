from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import CARDINAL, strip_thousands
from .cardinal import text
from .decimal import decimal_words
from .fraction import mixed_number

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "units.tsv"


def load_units() -> list[tuple[str, str, str]]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            written, sg, pl = line.split("\t")
            rows.append((written, sg, pl))
    return rows


class MeasureReader(Rule):
    """``5 km`` → ``five kilometers``, ``2x8 m`` → ``two by eight meters``."""

    name = "measure"
    kind = "read"

    def build(self, variants: bool = False):
        integer = (strip_thousands() @ CARDINAL).optimize()
        one = pynini.cross("1", "one")
        many = pynini.union(pynini.difference(pynini.project(integer, "input"), "1") @ integer, decimal_words())
        sign = pynini.closure(pynini.union(pynini.cross("-", "minus "), pynini.cross("−", "minus "),
                                           pynini.cross("+", "plus ")), 0, 1)
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        units = load_units()
        singular = pynini.union(*[pynini.cross(pynini.escape(w), " " + sg) for w, sg, _ in units])
        plural = pynini.union(*[pynini.cross(pynini.escape(w), " " + pl) for w, _, pl in units])
        scale = pynini.union(" million", " billion", " thousand")
        # ranges, dimensions, fractions and scale words before a unit
        dash = pynini.cross(pynini.closure(" ", 0, 1) + pynini.union("-", "–") + pynini.closure(" ", 0, 1), " to ")
        span = pynini.union(integer, decimal_words()) + dash + many
        by = pynini.union(integer, decimal_words()) + pynini.cross(pynini.union("x", "×"), " by ") + many
        amount = pynini.union(many, span, by, mixed_number(), many + scale)
        measure = sign + pynini.union(one + space + singular, amount + space + plural)
        percent = sign + pynini.union(integer, decimal_words()) + space + pynini.cross("%", " percent")
        # 5-10% → five to ten percent
        dash = pynini.union("-", "–")
        percent_range = (pynini.union(integer, decimal_words()) + pynini.cross(pynini.closure(" ", 0, 1) + dash + pynini.closure(" ", 0, 1), " to ")
                         + pynini.union(integer, decimal_words()) + space + pynini.cross("%", " percent"))
        return self.wrap(text(pynini.union(measure, percent, percent_range, pynutil.add_weight(by, 0.1)))).optimize()

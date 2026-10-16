from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import CARDINAL, SCALE_OF, strip_thousands
from .cardinal import text
from .decimal import decimal_words

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "units.tsv"
FEMININE = {"tonnellata", "ora", "chilocaloria"}


def load_units() -> list[tuple[str, str, str]]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            written, sg, pl = line.split("\t")
            rows.append((written, sg, pl))
    return rows


class MeasureReader(Rule):
    """``5 km`` → ``cinque chilometri``, ``1 t`` → ``una tonnellata``, ``-3 °C`` → ``meno tre gradi``."""

    name = "measure"
    kind = "read"

    def build(self, variants: bool = False):
        integer = (strip_thousands() @ CARDINAL).optimize()
        many = pynini.union(pynini.difference(pynini.project(integer, "input"), "1") @ integer @ SCALE_OF,
                            decimal_words())
        sign = pynini.closure(pynini.union(pynini.cross("-", "meno "), pynini.cross("−", "meno "),
                                           pynini.cross("+", "più ")), 0, 1)
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        units = load_units()
        # one graph per gender of "1" and one for the plural, not one per unit
        singular_m = pynini.union(*[pynini.cross(pynini.escape(w), sg) for w, sg, _ in units if sg not in FEMININE])
        singular_f = pynini.union(*[pynini.cross(pynini.escape(w), sg) for w, sg, _ in units if sg in FEMININE])
        plural = pynini.union(*[pynini.cross(pynini.escape(w), " " + pl) for w, _, pl in units])
        measure = sign + pynini.union(pynini.cross("1", "un ") + space + singular_m,
                                      pynini.cross("1", "una ") + space + singular_f,
                                      many + space + plural)
        amount = pynini.union(integer, decimal_words())
        percent = sign + amount + space + pynini.cross("%", " percento")
        dash = pynini.union("-", "–")
        percent_range = amount + pynini.cross(pynini.closure(" ", 0, 1) + dash + pynini.closure(" ", 0, 1), " ") + percent
        return self.wrap(text(pynini.union(measure, percent, percent_range))).optimize()

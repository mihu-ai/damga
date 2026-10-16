from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import CARDINAL, strip_thousands
from .cardinal import sign, text
from .decimal import decimal_words, scaled
from .fraction import fraction_words

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "units.tsv"


def load_units() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            written, sg, pl, gender = line.split("\t")
            rows.append((written, sg, pl, gender))
    return rows


PER = ("Jahr", "Monat", "Woche", "Tag", "Stunde", "Person", "Kopf", "Einwohner", "Stück", "Haushalt")


def per_unit(units: list[tuple[str, str, str, str]]) -> pynini.Fst:
    """What comes after ``/``: a unit, said in the singular (``m²`` → ``Quadratmeter``), or a word from ``PER``."""
    said = pynini.union(*[pynini.cross(pynini.escape(w), sg) for w, sg, _, _ in units if w not in ("%", "°", "°C", "°F")])
    return pynini.union(said, *PER).optimize()


class MeasureReader(Rule):
    """``5 km`` → ``fünf Kilometer``, ``1 t`` → ``eine Tonne``."""

    name = "measure"
    kind = "read"

    def build(self, variants: bool = False):
        integer = (strip_thousands() @ CARDINAL).optimize()
        # 2 Mio. t → zwei Millionen Tonnen
        many = pynini.union(pynini.difference(pynini.project(integer, "input"), "1") @ integer, decimal_words(), scaled())
        space = pynutil.delete(pynini.closure(pynini.union(" ", " "), 0, 1))
        units = load_units()
        # one number graph per gender of "1" and one for plurals, not one per unit, to keep the FST small
        branches = [many + space + pynini.union(*[pynini.cross(pynini.escape(w), " " + pl) for w, _, pl, _ in units])]
        for gender, one in (("m", "ein"), ("n", "ein"), ("f", "eine")):
            sg = [pynini.cross(pynini.escape(w), " " + s) for w, s, _, g in units if g == gender]
            branches.append(pynini.cross("1", one) + space + pynini.union(*sg))
        # 5 kg/m², 56,3 /km² (pro Quadratkilometer), 100 kWh/Jahr
        per = pynini.cross("/", " pro ") + per_unit(units)
        branches.append(many + space + per)
        # 1/2 l → ein halb Liter, 1 1/2 Stunden → eineinhalb Stunden
        branches.append(fraction_words() + space + pynini.union(*[pynini.cross(pynini.escape(w), " " + pl) for w, _, pl, _ in units]))
        measure = sign() + pynini.union(*branches) + pynini.closure(per, 0, 1)
        # 5-10 % → fünf bis zehn Prozent
        dash = pynini.cross(pynini.closure(" ", 0, 1) + pynini.union("-", "–") + pynini.closure(" ", 0, 1), " bis ")
        percent_range = pynini.union(integer, decimal_words()) + dash + pynini.union(integer, decimal_words()) + space + pynini.cross("%", " Prozent")
        return self.wrap(text(pynini.union(measure, percent_range))).optimize()

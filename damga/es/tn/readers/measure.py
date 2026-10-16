from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_APOC, CARDINAL_FEM, strip_thousands
from ..units import load_units
from .cardinal import text
from .decimal import decimal_words
from .fraction import proper_fractions

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "units.tsv"


class MeasureReader(Rule):
    """``5 km`` → ``cinco kilómetros``, ``21 t`` → ``veintiuna toneladas``, ``1 1/2 kg`` → ``un kilo y medio``."""

    name = "measure"
    kind = "read"

    def build(self, variants: bool = False):
        strip = strip_thousands()
        sign = pynini.closure(pynini.union(pynini.cross("-", "menos "), pynini.cross("−", "menos "),
                                           pynini.cross("+", "más ")), 0, 1)
        space = pynutil.delete(pynini.closure(pynini.union(" ", " ", " "), 0, 1))
        branches = []
        for written, sg, pl, gender in load_units():
            card = CARDINAL_FEM if gender == "f" else CARDINAL_APOC
            one = pynini.cross("1", "una" if gender == "f" else "un") + space + pynini.cross(pynini.escape(written), " " + sg)
            many = (pynini.difference(pynini.project(strip @ card, "input"), "1") @ (strip @ card))
            many = pynini.union(many, decimal_words(gender == "f")) + space + pynini.cross(pynini.escape(written), " " + pl)
            branches += [one, many]
        # fractions of a unit: "1/2 kg" → "medio kilo", "3/5 m" → "tres quintos de metro"
        units = load_units()
        fraction = proper_fractions()
        fraction = pynini.difference(pynini.project(fraction, "input"), "1/2") @ fraction
        of_unit = pynini.union(*[pynini.cross(pynini.escape(w), " de " + sg) for w, sg, _, _ in units])
        half = pynini.union("1/2", "½")
        whole = pynini.union(*"123456789") + pynini.closure(DIGIT, 0, 2)
        for written, sg, pl, gender in units:
            unit = space + pynutil.delete(pynini.escape(written))
            medio = "media" if gender == "f" else "medio"
            branches.append(pynutil.delete(half) + unit + pynutil.insert(f"{medio} {sg}"))
            card = CARDINAL_FEM if gender == "f" else CARDINAL_APOC
            if " " in sg:                       # "una milla por hora y media" is not said: "una y media millas por hora"
                branches.append((whole @ (CARDINAL_FEM if gender == "f" else CARDINAL))
                                + pynini.cross(pynini.union(" 1/2", "½"), f" y {medio}") + unit + pynutil.insert(" " + pl))
                continue
            amount = pynini.union(pynini.cross("1", ("una " if gender == "f" else "un ") + sg),
                                  (pynini.difference(whole, "1") @ card) + pynutil.insert(" " + pl))
            branches.append(amount + pynutil.delete(pynini.union(" 1/2", "½")) + unit + pynutil.insert(" y " + medio))
        branches.append(pynini.closure((whole @ CARDINAL) + pynini.cross(" ", " y "), 0, 1) + fraction + space + of_unit)
        measure = sign + pynini.union(*branches)
        amount = pynini.union(strip @ CARDINAL, decimal_words())
        percent = sign + amount + space + pynini.cross("%", " por ciento")
        span = amount + pynini.cross(pynini.union("-", "–", " - ", " – "), " a ") + percent
        return self.wrap(text(pynini.union(measure, percent, span))).optimize()

from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_FEM, strip_thousands
from .cardinal import text
from .decimal import decimal_words

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "units.tsv"


def load_units() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            written, sg, pl, gender = line.split("\t")
            rows.append((written, sg, pl, gender))
    return rows


def amounts(fem: bool) -> tuple[pynini.Fst, pynini.Fst]:
    """(singular amounts, plural amounts): French takes the plural from 2 on, ``1,5 kilomètre`` is singular."""
    card = CARDINAL_FEM if fem else CARDINAL
    integer = strip_thousands() @ card
    below_two = pynini.union("0", "1")
    one = below_two @ card
    many = pynini.difference(pynini.project(integer, "input"), below_two) @ integer
    dec = decimal_words(fem)
    dec_one = (below_two + "," + pynini.closure(DIGIT, 1)) @ dec
    dec_many = pynini.difference(pynini.project(dec, "input"), below_two + "," + pynini.closure(DIGIT, 1)) @ dec
    return pynini.union(one, dec_one), pynini.union(many, dec_many)


class MeasureReader(Rule):
    """``5 km`` → ``cinq kilomètres``, ``21 t`` → ``vingt et une tonnes``, ``5 %`` → ``cinq pour cent``."""

    name = "measure"
    kind = "read"

    def build(self, variants: bool = False):
        sign = pynini.closure(pynini.union(pynini.cross("-", "moins "), pynini.cross("−", "moins "),
                                           pynini.cross("+", "plus ")), 0, 1)
        space = pynutil.delete(pynini.closure(pynini.union(" ", " ", " "), 0, 1))
        branches = []
        for fem in (False, True):
            one, many = amounts(fem)
            rows = [r for r in load_units() if (r[3] == "f") == fem]
            singular = pynini.union(*[pynini.cross(pynini.escape(w), " " + sg) for w, sg, _, _ in rows])
            plural = pynini.union(*[pynini.cross(pynini.escape(w), " " + pl) for w, _, pl, _ in rows])
            branches.append(sign + pynini.union(one + space + singular, many + space + plural))
            if variants:
                # 2,5 km → deux kilomètres et demi, 1,5 t → une tonne et demie
                card = CARDINAL_FEM if fem else CARDINAL
                half = " et demie" if fem else " et demi"
                whole = strip_thousands() @ card
                one_half = (pynini.accep("1") @ card) + pynutil.delete(",5") + space + singular + pynutil.insert(half)
                many_half = ((pynini.difference(pynini.project(whole, "input"), pynini.union("0", "1")) @ whole)
                             + pynutil.delete(",5") + space + plural + pynutil.insert(half))
                branches.append(pynutil.add_weight(pynini.union(one_half, many_half), 0.5))
        _, number = amounts(False)
        number = pynini.union(number, amounts(False)[0])
        percent = sign + number + space + pynini.cross("%", " pour cent")
        dash = pynini.union("-", "–", " à ")
        percent_range = number + pynini.cross(pynini.closure(" ", 0, 1) + dash + pynini.closure(" ", 0, 1), " à ") + percent
        return self.wrap(text(pynini.union(*branches, percent, percent_range))).optimize()

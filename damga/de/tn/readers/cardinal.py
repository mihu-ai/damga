from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import NOT_YEAR
from ...numbers import CARDINAL, CARDINAL_ATTRIBUTIVE, DIGITS_SPOKEN, YEAR, YEAR_SPOKEN, strip_thousands


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def number_words() -> pynini.Fst:
    plain = (strip_thousands() @ CARDINAL).optimize()
    years = pynini.union(pynini.union("11", "12", "13", "14", "15", "16", "17", "18", "19") + DIGIT + DIGIT,
                         pynini.accep("20") + pynini.union(*"23456789") + DIGIT)
    not_year = pynini.difference(pynini.project(plain, "input"), years) @ plain
    digits = pynini.union("0" + pynini.closure(DIGIT, 1), pynini.closure(DIGIT, 19)) @ DIGITS_SPOKEN
    return pynini.union(years @ YEAR, not_year, pynutil.delete(NOT_YEAR) + (years @ plain), digits).optimize()


def other_number_words() -> pynini.Fst:
    """Variant readings of a year from 2010 on: 2012 → zwanzig zwölf."""
    years = pynini.accep("20") + pynini.union(*"123456789") + DIGIT
    return (pynutil.delete(pynini.closure(NOT_YEAR, 0, 1)) + (years @ YEAR_SPOKEN)).optimize()


def sign() -> pynini.Fst:
    return pynini.closure(pynini.union(pynini.cross("-", "minus "), pynini.cross("−", "minus "),
                                       pynini.cross("+", "plus ")), 0, 1)


class CardinalReader(Rule):
    """``25.000`` → ``fünfundzwanzigtausend``, ``1990`` → ``neunzehnhundertneunzig``, ``-5`` → ``minus fünf``."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = number_words()
        # 47-jähriger → siebenundvierzigjähriger: one word when said
        attributive = strip_thousands() @ CARDINAL_ATTRIBUTIVE
        lower = pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüß")
        compound = attributive + pynutil.delete(pynini.union("-", "—", "–")) + pynini.closure(lower, 2)
        graph = pynini.union(sign() + self.number, compound)
        if variants:
            graph = pynini.union(graph, pynutil.add_weight(other_number_words(), 0.5))
        return self.wrap(text(graph)).optimize()

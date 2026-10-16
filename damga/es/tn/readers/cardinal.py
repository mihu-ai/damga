from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import BEFORE_NOUN, FEMININE
from ...numbers import CARDINAL, CARDINAL_APOC, CARDINAL_FEM, DIGITS_SPOKEN, strip_thousands


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def number_words() -> pynini.Fst:
    """``25.000`` / ``25000`` → ``veinticinco mil``, with the gender the pre-hook marked; numbers with a leading zero
    or longer than 18 digits are read digit by digit."""
    strip = strip_thousands()
    digits = pynini.union("0" + pynini.closure(DIGIT, 1), pynini.closure(DIGIT, 19)) @ DIGITS_SPOKEN
    return pynini.union(
        strip @ CARDINAL,
        pynutil.delete(FEMININE) + (strip @ CARDINAL_FEM),
        pynutil.delete(BEFORE_NOUN) + (strip @ CARDINAL_APOC),
        pynini.closure(pynutil.delete(pynini.union(FEMININE, BEFORE_NOUN)), 0, 1) + digits,
    ).optimize()


class CardinalReader(Rule):
    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = number_words()
        sign = pynini.closure(pynini.union(pynini.cross("-", "menos "), pynini.cross("−", "menos "),
                                           pynini.cross("+", "más ")), 0, 1)
        return self.wrap(text(sign + self.number)).optimize()

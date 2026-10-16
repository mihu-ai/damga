from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import ORDINAL, ORDINAL_FEM, strip_thousands
from .cardinal import text

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI",
         "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII", "XXIX", "XXX"]


def roman_to_digits() -> pynini.Fst:
    return pynini.union(*[pynini.cross(r, str(i)) for i, r in enumerate(ROMAN, 1)]).optimize()


def ordinal_words() -> pynini.Fst:
    """``1er`` → ``premier``, ``1re`` → ``première``, ``9e`` / ``9ème`` → ``neuvième``, ``XXe`` → ``vingtième``."""
    number = pynini.union(DIGIT + pynini.closure(DIGIT, 0, 5), strip_thousands(), roman_to_digits())
    ending = pynini.union("e", "ème", "ième", "è", "eme", "ieme")
    masc = (pynini.union("1", "I") + pynutil.delete(pynini.union("er", "ᵉʳ"))) @ (roman_to_digits() | "1") @ ORDINAL
    fem = (pynini.union("1", "I") + pynutil.delete(pynini.union("re", "ère", "ere"))) @ (roman_to_digits() | "1") @ ORDINAL_FEM
    rest = (number + pynutil.delete(pynini.union(ending, "ᵉ"))) @ pynini.difference(pynini.closure(DIGIT, 1), "1") @ ORDINAL
    second = pynini.union(pynini.cross("2nd", "second"), pynini.cross("2nde", "seconde"), pynini.cross("2d", "second"))
    return pynini.union(masc, fem, rest, second).optimize()


class OrdinalReader(Rule):
    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(ordinal_words())).optimize()

from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_FEM, DIGITS_SPOKEN, strip_thousands
from .cardinal import BEFORE_NOUN, FEMININE, text


def fraction_words() -> pynini.Fst:
    """The digits after the comma, read as a number (``3,65`` → *sesenta y cinco*), leading zeros one by one; four
    digits and more one by one."""
    zeros = pynini.closure(pynini.cross("0", "cero "))
    short = zeros + ((NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2)) @ CARDINAL)
    all_zeros = pynini.closure(pynini.cross("0", "cero "), 0, 2) + pynini.cross("0", "cero")    # 0, 00, 000
    return pynini.union(short, pynini.closure(DIGIT, 4) @ DIGITS_SPOKEN, all_zeros).optimize()


def decimal_words(feminine: bool = False) -> pynini.Fst:
    """``5,4`` → ``cinco coma cuatro``, ``12.2`` → ``doce punto dos`` (a point with one or two digits; three are a
    thousands group)."""
    card = CARDINAL_FEM if feminine else CARDINAL
    integer = strip_thousands() @ card
    comma = integer + pynini.cross(",", " coma ") + fraction_words()
    point = (pynini.closure(DIGIT, 1, 3) @ card) + pynini.cross(".", " punto ") + (pynini.closure(DIGIT, 1, 2) @ fraction_words())
    return pynini.union(comma, point).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, variants: bool = False):
        sign = pynini.closure(pynini.union(pynini.cross("-", "menos "), pynini.cross("−", "menos ")), 0, 1)
        # The pre-hook marks a number before a noun; a decimal before "millones" is read the same either way.
        number = pynini.union(decimal_words(), pynutil.delete(FEMININE) + decimal_words(True),
                              pynutil.delete(BEFORE_NOUN) + decimal_words())
        # "2,5 millones" is one token, so its readings can move the half: dos millones y medio
        scale = pynini.closure(pynini.union(" millones", " mil millones", " billones", " millón"), 0, 1)
        return self.wrap(text(sign + number + scale)).optimize()

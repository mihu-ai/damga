from __future__ import annotations

import pynini

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import CARDINAL, DIGITS_SPOKEN, strip_thousands
from .cardinal import text


def fraction_words() -> pynini.Fst:
    """After the comma: one or two digits are one number (``3,14`` → ``tre virgola quattordici``); a leading zero or
    three digits and more, digit by digit."""
    as_number = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT) @ CARDINAL
    digit_by_digit = pynini.union("0" + pynini.closure(DIGIT), pynini.closure(DIGIT, 3)) @ DIGITS_SPOKEN
    return pynini.union(as_number, digit_by_digit).optimize()


def decimal_words() -> pynini.Fst:
    """``2,5`` → ``due virgola cinque``, ``0,7`` → ``zero virgola sette``."""
    integer = strip_thousands() @ CARDINAL
    return (integer + pynini.cross(",", " virgola ") + fraction_words()).optimize()


def quantity() -> pynini.Fst:
    return pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS]).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, cardinal_number: pynini.Fst, variants: bool = False):
        self.number = decimal_words()
        sign = pynini.closure(pynini.union(pynini.cross("-", "meno "), pynini.cross("−", "meno ")), 0, 1)
        one = pynini.cross("1", "un")       # 1 milione → un milione
        many = pynini.difference(pynini.project(cardinal_number, "input"), "1") @ cardinal_number
        whole_with_scale = pynini.union(one, many) + quantity()
        # 4.0, 5.5 gigahertz: one digit after a point, as in versions and English-style decimals, read "punto"
        point = (strip_thousands() @ CARDINAL) + pynini.cross(".", " punto ") + (DIGIT @ CARDINAL)
        return self.wrap(text(sign + pynini.union(
            self.number + pynini.closure(quantity(), 0, 1), whole_with_scale,
            point + pynini.closure(quantity(), 0, 1)))).optimize()

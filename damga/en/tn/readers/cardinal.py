from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import NOT_YEAR
from ...numbers import CARDINAL, DIGITS_SPOKEN, YEAR, YEAR_SPOKEN, strip_thousands


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def other_number_words() -> pynini.Fst:
    """Variant readings of a four-digit number: every way a year is said (``2013`` → *twenty thirteen*)."""
    year_digits = pynini.project(YEAR_SPOKEN, "input").optimize()
    return (pynutil.delete(pynini.closure(NOT_YEAR, 0, 1)) + (year_digits @ YEAR_SPOKEN)).optimize()


def number_words() -> pynini.Fst:
    """``25,000`` → ``twenty five thousand``; a year-like number is read as a year unless the pre-hook marked it as
    a count.  Leading zeros and very long numbers are read digit by digit."""
    plain = (strip_thousands() @ CARDINAL).optimize()
    year_digits = pynini.project(YEAR, "input").optimize()
    year = YEAR
    not_year_plain = pynini.difference(pynini.project(plain, "input"), year_digits) @ plain
    digits = pynini.union("0" + pynini.closure(DIGIT, 1), pynini.closure(DIGIT, 16)) @ DIGITS_SPOKEN
    return pynini.union(
        year,
        not_year_plain,
        pynutil.delete(NOT_YEAR) + (year_digits @ plain),
        digits,
    ).optimize()


class CardinalReader(Rule):
    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = number_words()
        sign = pynini.closure(pynini.union(pynini.cross("-", "minus "), pynini.cross("−", "minus "),
                                           pynini.cross("+", "plus ")), 0, 1)
        graph = sign + self.number
        if variants:
            graph = pynini.union(graph, pynutil.add_weight(other_number_words(), 0.5))
        return self.wrap(text(graph)).optimize()

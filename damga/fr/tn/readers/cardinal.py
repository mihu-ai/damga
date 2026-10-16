from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import FEM
from ...numbers import CARDINAL, CARDINAL_FEM, DIGIT_WORD, TEEN, TENS, UNIT, strip_thousands


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def digits_spoken() -> pynini.Fst:
    return (DIGIT_WORD + pynini.closure(pynutil.insert(" ") + DIGIT_WORD)).optimize()


def number_words() -> pynini.Fst:
    """``15 000`` / ``15000`` → ``quinze mille``; a marked number takes the feminine (``⁤21`` → ``vingt et une``);
    leading zeros and very long numbers are read digit by digit."""
    plain = (strip_thousands() @ CARDINAL).optimize()
    fem = pynutil.delete(FEM) + (strip_thousands() @ CARDINAL_FEM)
    digits = pynini.union("0" + pynini.closure(DIGIT, 1), pynini.closure(DIGIT, 16)) @ digits_spoken()
    return pynini.union(plain, fem, digits).optimize()


def hundreds_year() -> pynini.Fst:
    """1100–1999 counted in hundreds: ``1971`` → *dix-neuf cent soixante et onze* (a variant reading only)."""
    head = (pynini.union(*[f"1{d}" for d in "123456789"]) @ TEEN) + pynutil.insert(" cent")
    rest = pynini.union(pynutil.delete("00"), pynutil.insert(" ") + pynutil.delete("0") + UNIT, pynutil.insert(" ") + TENS)
    return (head + rest).optimize()


class CardinalReader(Rule):
    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = number_words()
        sign = pynini.closure(pynini.union(pynini.cross("-", "moins "), pynini.cross("−", "moins "),
                                           pynini.cross("+", "plus ")), 0, 1)
        graph = sign + self.number
        if variants:
            graph = pynini.union(graph, pynutil.add_weight(hundreds_year(), 1.0))
        return self.wrap(text(graph)).optimize()

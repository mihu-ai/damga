from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import CARDINAL, CARDINAL_FEM, ZERO_WORD, strip_thousands
from .cardinal import FEM, digits_spoken, text


def fraction_words() -> pynini.Fst:
    """The part after the comma, read as a number after its leading zeros (``05`` → ``zéro cinq``); four digits
    and more one by one."""
    zeros = pynini.closure(ZERO_WORD + pynutil.insert(" "))
    short = pynini.union(zeros + ((NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2)) @ CARDINAL),
                         pynini.closure(ZERO_WORD + pynutil.insert(" ")) + ZERO_WORD)
    short = pynini.closure(DIGIT, 1, 3) @ short
    return pynini.union(short, pynini.closure(DIGIT, 4) @ digits_spoken()).optimize()


def decimal_words(fem: bool = False) -> pynini.Fst:
    """``3,5`` → ``trois virgule cinq``, ``0,14`` → ``zéro virgule quatorze``."""
    integer = strip_thousands() @ (CARDINAL_FEM if fem else CARDINAL)
    return (integer + pynini.cross(",", " virgule ") + fraction_words()).optimize()


def quantity() -> pynini.Fst:
    return pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS]).optimize()


def half_with_scale() -> pynini.Fst:
    """``2,5 millions`` → *deux millions et demi*, ``1,5 milliard`` → *un milliard et demi*, another reading."""
    return ((strip_thousands() @ CARDINAL) + pynutil.delete(",5") + quantity() + pynutil.insert(" et demi")).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, cardinal_number: pynini.Fst, variants: bool = False):
        sign = pynini.closure(pynini.union(pynini.cross("-", "moins "), pynini.cross("−", "moins ")), 0, 1)
        fem = pynutil.delete(FEM) + decimal_words(fem=True)
        number = pynini.union(decimal_words(), fem)
        graph = pynini.union(
            number + pynini.closure(quantity(), 0, 1),
            cardinal_number + quantity(),                     # 15 millions → quinze millions
        )
        if variants:
            graph = pynini.union(graph, pynutil.add_weight(half_with_scale(), 0.3))
        return self.wrap(text(sign + graph)).optimize()

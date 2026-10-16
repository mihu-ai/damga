from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import DIGIT_WORD, ZERO_WORD
from .cardinal import text


def spoken_decimal(number: pynini.Fst) -> pynini.Fst:
    """``sept virgule huit`` → ``7,8``, ``zéro virgule zéro cinq`` → ``0,05``: the digits after the comma are said
    one by one, in groups, or both; the split with fewer groups wins."""
    zeros = pynini.closure(pynini.invert(ZERO_WORD) + pynutil.delete(pynini.union(" ", "")))
    as_number = zeros + (number @ (pynini.union(*"123456789") + pynini.closure(DIGIT, 0, 2)))
    group = pynutil.add_weight(pynini.union(pynini.invert(DIGIT_WORD), number @ (pynini.union(*"123456789") + DIGIT)), 0.1)
    groups = group + pynini.closure(pynutil.delete(" ") + group, 1)
    after = pynini.union(as_number, pynini.closure(pynini.invert(ZERO_WORD) + pynutil.delete(" "), 0) + pynini.invert(ZERO_WORD),
                         groups)
    integer = number @ pynini.closure(DIGIT, 1)
    # "virgule sept" without the zero is 0,7
    return pynini.union(integer + pynini.cross(pynini.union(" virgule ", "virgule"), ",") + after,
                        pynini.cross("virgule ", "0,") + after).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        self.number = spoken_decimal(number)
        scale = pynini.closure(pynini.union(" ", pynini.cross("-", " "), pynutil.insert(" ")) + pynini.union(*QUANTITY_WORDS),
                               0, 1)
        sign = pynini.closure(pynini.cross("moins ", "-"), 0, 1)
        # deux millions et demi → 2,5 millions, un milliard et demi → 1,5 milliard
        whole = number @ pynini.closure(DIGIT, 1, 3)
        half = (whole + pynutil.insert(",5") + pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS])
                + pynutil.delete(pynini.union(" et demi", " et demie")))
        return self.wrap(text(sign + pynini.union(self.number + scale, half))).optimize()

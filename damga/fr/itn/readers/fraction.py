from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import ORDINAL, flexible
from .cardinal import text


class FractionReader(Rule):
    """``trois centièmes`` → ``3/100``, for denominators from ten up.  With *un* the fraction is told from an
    ordinal by the *de* that follows (``un treizième mois`` is an ordinal).  Halves to ninths stay words."""

    name = "fraction"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        ten_up = pynini.difference(pynini.closure(DIGIT, 2), "0" + pynini.closure(DIGIT))
        canon = ORDINAL @ flexible()
        singular = pynini.invert(canon).optimize() @ ten_up
        plural = pynini.invert(canon + pynutil.insert("s")).optimize() @ ten_up
        letters = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyzàâäæçéèêëîïôœùûüÿ"), 1)
        of = pynini.union(" de", " du", " des", " d'" + letters)
        one = pynini.cross("un ", "1/") + singular + of
        many = (number @ pynini.difference(pynini.closure(DIGIT, 1), pynini.union("0", "1"))) + pynini.cross(" ", "/") + plural
        return self.wrap(text(pynini.union(one, many))).optimize()

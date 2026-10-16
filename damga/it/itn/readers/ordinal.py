from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import ORDINAL
from .cardinal import text

_SMALL = ("primo", "secondo", "terzo", "quarto", "quinto", "sesto", "settimo", "ottavo", "nono")


def spoken_ordinal() -> pynini.Fst:
    """``ventunesimo`` → ``21º``, ``trentasettesima`` → ``37ª`` (masculine and feminine singular)."""
    marks = pynini.union(pynini.cross("o", "º"), pynini.cross("a", "ª"))
    return (pynini.invert(ORDINAL) @ (pynini.closure(DIGIT, 1) + marks)).optimize()


class OrdinalReader(Rule):
    """``ventesimo`` → ``20º``, ``trentasettesima sessione`` → ``37ª sessione``; primo to nono stay words."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = spoken_ordinal()
        small = pynini.union(*[pynini.union(w, w[:-1] + "a") for w in _SMALL])
        big = pynini.difference(pynini.project(self.number, "input"), small) @ self.number
        # a century is written in Roman numerals: il ventunesimo secolo → il XXI secolo
        from ...tn.readers.ordinal import _roman
        century = pynini.union(*[pynini.cross(say, _roman(n)) for n in range(1, 31)
                                 for say in [pynini.shortestpath(pynini.accep(f"{n}o") @ ORDINAL).string()]])
        century = pynutil.add_weight(century + pynini.accep(" secolo"), -0.1)
        return self.wrap(text(pynini.union(big, century))).optimize()

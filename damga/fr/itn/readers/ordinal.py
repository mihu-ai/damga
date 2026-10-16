from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import ORDINAL, ORDINAL_FEM, flexible, group_thousands
from ...tn.readers.ordinal import ROMAN
from .cardinal import text


def spoken_ordinal() -> pynini.Fst:
    """``dixième`` → ``10``, ``vingt et unième`` → ``21`` (digits only; the caller adds the ending)."""
    return pynini.invert(pynini.union(ORDINAL, ORDINAL_FEM) @ flexible()).optimize()


class OrdinalReader(Rule):
    """``dixième`` → ``10e``, ``cent cinquantième`` → ``150e``, ``vingtième siècle`` → ``XXe siècle``; premier to
    neuvième stay words (``la première fois``)."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False, group: bool = True):
        self.number = spoken_ordinal()
        big = self.number @ pynini.difference(pynini.closure(DIGIT, 1), pynini.union(*"123456789"))
        if group:
            big = big @ group_thousands(5)                     # vingt-cinq mille cent onzième → 25 111e
        century = (self.number @ pynini.union(*[pynini.cross(str(i), r) for i, r in enumerate(ROMAN, 1)])
                   + pynutil.insert("e") + pynini.accep(" siècle"))
        return self.wrap(text(pynini.union(big + pynutil.insert("e"), pynutil.add_weight(century, -0.1)))).optimize()

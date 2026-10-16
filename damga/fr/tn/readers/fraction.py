from __future__ import annotations

import pynini

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, ORDINAL
from .cardinal import text


class FractionReader(Rule):
    """``3/4`` → ``trois quarts``, ``1 1/2`` → ``un et demi``; denominators 2 to 20.  ``24/7`` is
    ``vingt-quatre sur sept``."""

    name = "fraction"
    kind = "read"

    def build(self, variants: bool = False):
        numerator = pynini.union(*[str(n) for n in range(1, 100)])
        one = pynini.accep("1") @ CARDINAL
        many = pynini.difference(numerator, "1") @ CARDINAL
        branches = [pynini.cross(k, v) for k, v in {"½": "un demi", "¼": "un quart", "¾": "trois quarts",
                                                     "⅓": "un tiers", "⅔": "deux tiers"}.items()]
        special = {2: ("demi", "demis"), 3: ("tiers", "tiers"), 4: ("quart", "quarts")}
        for d in range(2, 21):
            if d in special:
                sg, pl = special[d]
            else:
                sg = pynini.shortestpath(pynini.accep(str(d)) @ ORDINAL).string()
                pl = sg + "s"
            branches.append(one + pynini.cross(f"/{d}", f" {sg}"))
            branches.append(many + pynini.cross(f"/{d}", f" {pl}"))
        fractions = pynini.difference(pynini.project(pynini.union(*branches), "input"), "24/7") @ pynini.union(*branches)
        halves = pynini.union("1/2", "½")
        whole = pynini.closure(pynini.cross("-", "moins "), 0, 1) + ((NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2)) @ CARDINAL)
        part = pynini.union(pynini.cross(halves, "demi"), pynini.difference(pynini.project(fractions, "input"), halves) @ fractions)
        mixed = whole + pynini.cross(" ", " et ") + part
        return self.wrap(text(pynini.union(fractions, mixed, pynini.cross("24/7", "vingt-quatre sur sept")))).optimize()

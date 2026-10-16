from __future__ import annotations

import pynini

from ....core.rules import Rule
from ...numbers import CARDINAL
from .cardinal import text

# denominator: singular, plural
DENOMINATORS = {2: ("mezzo", "mezzi"), 3: ("terzo", "terzi"), 4: ("quarto", "quarti"), 5: ("quinto", "quinti"),
                6: ("sesto", "sesti"), 7: ("settimo", "settimi"), 8: ("ottavo", "ottavi"), 9: ("nono", "noni"),
                10: ("decimo", "decimi"), 100: ("centesimo", "centesimi")}


class FractionReader(Rule):
    """``3/4`` → ``tre quarti``, ``24/7`` → ``ventiquattro su sette``.

    Only proper fractions over 2 to 10 or 100: a slash between larger numbers is a day and month (``7/12``) or a
    reference, and stays as written."""

    name = "fraction"
    kind = "read"

    def build(self, variants: bool = False):
        branches = [pynini.cross("24/7", "ventiquattro su sette")]
        for d, (sg, pl) in DENOMINATORS.items():
            branches.append(pynini.cross(f"1/{d}", f"un {sg}"))
            if d > 2:
                many = pynini.union(*[str(n) for n in range(2, d)])
                branches.append((many @ CARDINAL) + pynini.cross(f"/{d}", f" {pl}"))
        return self.wrap(text(pynini.union(*branches))).optimize()

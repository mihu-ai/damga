from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from .cardinal import text


class TimeReader(Rule):
    """``alle nove e trenta`` → ``alle 9.30``, ``le nove e un quarto`` → ``le 9.15``.  Only after "alle", "le",
    "dalle", "delle", "verso le": "nove e trenta" alone may be two numbers."""

    name = "time"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        hour = pynini.union(number @ pynini.union(*[str(h) for h in range(0, 25)]), pynini.cross("una", "1"))
        minutes = number @ pynini.union(*[str(m) for m in range(1, 60)])
        mm = pynini.union(
            pynini.cross(" e ", ".") + (minutes @ pynini.union(*[str(m) for m in range(10, 60)])),
            pynini.cross(" e ", ".0") + (minutes @ pynini.union(*"123456789")),
            pynini.cross(pynini.union(" e mezza", " e mezzo"), ".30"),
            pynini.cross(pynini.union(" e un quarto", " e quarto"), ".15"),
            pynini.cross(" e tre quarti", ".45"),
        )
        lead = pynini.union("alle ", "le ", "dalle ", "delle ", "verso le ", "entro le ", "fino alle ", "sono le ")
        # An hour without minutes only after a word that asks for a time: "le due iniziative" is a count.
        hour_lead = pynini.union("alle ", "dalle ", "verso le ", "entro le ", "fino alle ", "sono le ")
        # … or with a time of day after it: "le venti di stasera", "delle nove del mattino"
        day_part = pynini.union(*[" " + w for w in ("di stasera", "di questa sera", "di oggi", "di domani", "di sera",
                                                     "di mattina", "del mattino", "del pomeriggio", "della sera",
                                                     "della mattina", "precise", "in punto")])
        graph = pynini.union(lead + hour + mm, hour_lead + hour + pynutil.insert(".00"),
                             lead + hour + pynutil.insert(".00") + day_part)
        return self.wrap(text(graph)).optimize()

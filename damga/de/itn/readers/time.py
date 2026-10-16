from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import text


class TimeReader(Rule):
    """``fünfzehn uhr dreißig`` → ``15.30 Uhr``, ``fünfzehn uhr`` → ``15 Uhr``."""

    name = "time"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        hour = number @ pynini.union(*[str(h) for h in range(0, 25)])
        minutes = number @ pynini.union(*[str(m) for m in range(1, 60)]) @ pynini.union(
            pynutil.insert("0") + pynini.union(*"123456789"), pynini.union(*"12345") + DIGIT)
        clock = hour + pynini.cross(" uhr ", ".") + minutes + pynutil.insert(" Uhr")
        plain = hour + pynini.cross(" uhr", " Uhr")
        return self.wrap(text(pynini.union(clock, plain))).optimize()

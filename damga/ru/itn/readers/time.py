from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import CASES, NOUNS
from ...numbers import counted
from .common import text


class TimeReader(Rule):
    """``семнадцать часов две минуты`` → 17:02, ``до восемнадцати часов тридцати минут`` → до 18:30, ``два часа и три
    минуты`` → 2:03."""

    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        branches = []
        for case in CASES:
            hours = pynini.invert(counted(NOUNS["час"], case)) @ pynini.union(*[str(h) for h in range(0, 25)])
            minutes = pynini.invert(counted(NOUNS["минута"], case)) @ pynini.union(
                pynutil.insert("0") + DIGIT, pynini.union(*"12345") + DIGIT)
            branches.append(hours + pynini.cross(pynini.union(" ", " и "), ":") + minutes)
        return self.wrap(text(pynini.union(*branches))).optimize()

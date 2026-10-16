from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import NOUNS
from ...numbers import counted
from .common import cased, text


class TimeReader(Rule):
    """``17:02`` → семнадцать часов две минуты, ``до 18:00`` → до восемнадцати часов."""

    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        hours = pynini.union(*[str(h) for h in range(0, 25)], *[f"0{h}" for h in range(0, 10)])
        strip = pynini.union(pynutil.delete("0") + DIGIT, pynini.union(*"123456789") + DIGIT, DIGIT)

        def build(case: str) -> pynini.Fst:
            h = (hours @ strip) @ counted(NOUNS["час"], case)
            m = pynini.union(pynutil.delete("00"),
                             pynutil.insert(" ") + ((pynini.union(*"012345") + DIGIT) @ strip @ counted(NOUNS["минута"], case)))
            return h + pynutil.delete(":") + m

        return self.wrap(text(cased(build, variants=variants))).optimize()

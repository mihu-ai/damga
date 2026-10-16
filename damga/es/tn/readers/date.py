from __future__ import annotations

import pynini

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS
from ...numbers import CARDINAL
from .cardinal import text


class DateReader(Rule):
    """``17/02/2008`` / ``17.02.2008`` / ``17-02-2008`` → ``diecisiete de febrero de dos mil ocho`` (day first).
    Written-out dates (``17 de febrero de 2008``) need nothing: their numbers are read as numbers; the pre-hook turns
    an ISO date (``2008-02-17``) into ``17/02/2008``."""

    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        year = (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT) @ CARDINAL
        branches = []
        for m in range(1, 13):
            for d in range(1, 32):
                said = f"{pynini.shortestpath(pynini.accep(str(d)) @ CARDINAL).string()} de {MONTHS[m - 1]} de "
                for sep in "/.-":
                    written = pynini.union(f"{d:02d}{sep}{m:02d}{sep}", f"{d}{sep}{m}{sep}")
                    branches.append(pynini.cross(written, said) + year)
        return self.wrap(text(pynini.union(*branches))).optimize()

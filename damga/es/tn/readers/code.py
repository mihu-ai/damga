from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL
from .cardinal import text

_UPPER = pynini.union(*"ABCDEFGHIJKLMNOPQRSTUVWXYZÑ")


class CodeReader(Rule):
    """Letters and a number written together: ``G20`` → ``G veinte``, ``5G`` → ``cinco G``."""

    name = "code"
    kind = "read"

    def build(self, variants: bool = False):
        letters = pynini.closure(_UPPER, 1, 6)
        number = (NONZERO_DIGIT + pynini.closure(DIGIT, 0, 3)) @ CARDINAL
        dash = pynini.closure(pynutil.delete(pynini.union("-", "‑")), 0, 1)
        graph = pynini.union(letters + dash + pynutil.insert(" ") + number,
                             number + pynutil.insert(" ") + letters)
        return self.wrap(text(graph)).optimize()

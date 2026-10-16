from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import UNESCAPED_CHAR, Rule


class WordWriter(Rule):
    name = "word"
    kind = "write"

    def build(self, variants: bool = False):
        return (pynutil.delete('word="') + pynini.closure(UNESCAPED_CHAR, 1) + pynutil.delete('"')).optimize()

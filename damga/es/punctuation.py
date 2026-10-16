"""Spanish punctuation tokens: the shared set plus the opening ¿ ¡, the « » quotes, typographic quotes and dashes."""
from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ..core.rules import Rule
from .lexicon import MARKS


class PunctuationReader(Rule):
    name = "punctuation"
    kind = "read"

    def build(self, variants: bool = False):
        punct = pynini.union(pynini.union(*[pynini.escape(c) for c in MARKS]), pynini.cross('"', '\\"')).optimize()
        return (pynutil.insert('word="') + punct + pynutil.insert('"')).optimize()

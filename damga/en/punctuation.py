"""Punctuation for the English grammars: the shared ASCII set plus typographic quotes and dashes, so a number right
next to one is still read (``“5 years”``)."""
from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ..core.rules import Rule

MARKS = '.,;:!?()[]…«»“”‘—–¿¡'


class PunctuationReader(Rule):
    name = "punctuation"
    kind = "read"

    def build(self, variants: bool = False):
        punct = pynini.union(pynini.union(*[pynini.escape(c) for c in MARKS]), pynini.cross('"', '\\"')).optimize()
        return (pynutil.insert('word="') + punct + pynutil.insert('"')).optimize()

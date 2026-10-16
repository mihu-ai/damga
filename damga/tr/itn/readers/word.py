from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import ESCAPED_CHAR, NON_SPACE, Rule
from ...lexicon import NUMBER_WORDS


class WordReader(Rule):
    name = "word"
    kind = "read"

    def build(self, variants: bool = False):
        return (pynutil.insert('word="') + pynini.closure(ESCAPED_CHAR, 1) + pynutil.insert('"')).optimize()

_TRAIL = pynini.closure(pynini.union(*[pynini.escape(c) for c in '.,;:!?)"']))
NON_NUMBER_WORD = pynini.difference(
    pynini.closure(NON_SPACE, 1),
    pynini.union(pynini.union(*NUMBER_WORDS) + _TRAIL, pynini.closure(pynini.union(*"0123456789.,-"), 1) + _TRAIL),
).optimize()

class PunctuationReader(Rule):

    name = "punctuation"
    kind = "read"

    def build(self, variants: bool = False):
        punct = pynini.union(pynini.union(*[pynini.escape(c) for c in '.,;:!?()[]…']), pynini.cross('"', '\\"')).optimize()
        return (pynutil.insert('word="') + punct + pynutil.insert('"')).optimize()

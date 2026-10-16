from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule
from ....tr.itn.writers.word import WordWriter
from ..categories import ALL_CATEGORIES


class SentenceWriter(Rule):
    """Every French TN class carries its reading in a ``text`` field: unwrapping is all that is left to do."""

    name = "sentence"
    kind = "write"

    def build(self, categories=ALL_CATEGORIES, variants: bool = False):
        classes = pynini.union(*[pynutil.delete(f'{c}(text="') + pynini.closure(NON_QUOTE) + pynutil.delete('")')
                                 for c in set(categories) | {"cardinal", "lexicon_entry", "bank", "telephone"}])
        token = pynini.union(classes, WordWriter(variants).fst).optimize()
        return (token + pynini.closure(pynini.accep(" ") + token)).optimize()

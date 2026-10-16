from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import TR_LOWER, Rule
from .cardinal import CardinalReader


class OrdinalReader(Rule):
    name = "ordinal"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        integer = pynutil.insert('integer="') + cardinal.number + pynutil.insert('"')
        marked = integer + pynutil.delete("º")

        vowel = pynini.union(*"ıiuü")
        ordinal_suffix = pynini.closure(vowel, 0, 1) + pynini.accep("nc") + vowel + pynini.closure(TR_LOWER)
        apostrophe = integer + pynutil.delete("'") + pynutil.insert(' suffix="') + ordinal_suffix + pynutil.insert('"')
        return self.wrap(pynini.union(marked, apostrophe))

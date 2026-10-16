from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NON_QUOTE, SIGMA, Rule, string_map
from ...itn.readers.ordinal import ORDINAL_SUFFIX
from .number import CARDINAL

_LAST_VOWEL_DROP = [("iki", "ik"), ("altı", "alt"), ("yedi", "yed"), ("yirmi", "yirm"), ("elli", "ell"), ("altmış", "altmış"), ("yetmiş", "yetmiş")]

class OrdinalWriter(Rule):
    name = "ordinal"
    kind = "write"

    def build(self, variants: bool = False):
        to_ordinal = string_map([(b, a) for a, b in ORDINAL_SUFFIX])
        spoken = pynini.closure(DIGIT, 1) @ CARDINAL
        plain = pynutil.delete('integer="') + (spoken @ (SIGMA + to_ordinal)) + pynutil.delete('"')

        vowel = pynini.union(*"ıiuü")
        core = pynutil.delete(pynini.closure(vowel, 0, 1) + pynini.accep("nc") + vowel)
        with_suffix = (pynutil.delete('integer="') + (spoken @ (SIGMA + to_ordinal)) + pynutil.delete('" suffix="')
                       + core + pynini.closure(NON_QUOTE) + pynutil.delete('"'))
        return self.unwrap(pynini.union(plain, with_suffix))

from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import ZERO
from ...numbers import NONZERO_DIGIT, cardinal
from .common import text

# Words a telephone number follows; after them a local number without a code (123-45-67) is a telephone number too.
KEYWORDS = ["телефон", "телефона", "телефону", "тел", "номер", "номеру", "номер телефона", "по номеру",
            "по телефону", "звоните", "позвоните", "звонить", "звоните по номеру", "позвоните по номеру",
            "факс", "мобильный"]


class TelephoneReader(Rule):
    """A Russian telephone number spoken in groups or digit by digit, written ``+7 495 123-45-67``: ``восемь восемьсот
    пятьсот пятьдесят пять тридцать пять тридцать пять`` → 8 800 555-35-35.  After a keyword (``телефон``, ``номер``
    …) a local number counts too.

    Without a keyword only ``плюс семь`` / ``восемь`` followed by exactly ten digits in the 3-3-2-2 layout counts,
    so ``восемь тысяч``, years and sums keep their own readings."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        sp = pynutil.delete(" ")
        words = pynini.invert(cardinal("nom", "m"))
        zero = pynini.cross(ZERO[0], "0")
        digit = pynini.union(zero, words @ DIGIT)
        teen_or_tens = words @ (NONZERO_DIGIT + DIGIT)
        hundreds = words @ (NONZERO_DIGIT + DIGIT + DIGIT)

        def singles(n: int) -> pynini.Fst:
            return digit + pynini.closure(sp + digit, n - 1, n - 1) if n > 1 else digit

        # two digits: сорок пять, ноль пять, or two digit words
        two = pynini.union(teen_or_tens, zero + sp + digit, singles(2))
        # three digits: сто двадцать три, ноль девяносто пять, ноль ноль пять, три digit words
        three = pynini.union(hundreds, zero + sp + teen_or_tens, zero + sp + zero + sp + digit, singles(3),
                             digit + sp + teen_or_tens)
        hyphen = pynutil.insert("-")
        local = three + sp + hyphen + two + sp + hyphen + two
        national = three + sp + pynutil.insert(" ") + local
        prefix = pynini.union(pynini.cross("плюс семь", "+7"), pynini.cross("восемь", "8"))
        full = prefix + sp + pynutil.insert(" ") + national

        keywords = pynini.union(*KEYWORDS)
        keyed = keywords + pynini.closure(":", 0, 1) + pynini.accep(" ") + pynini.union(full, local)
        return self.wrap(text(pynini.union(full, keyed))).optimize()

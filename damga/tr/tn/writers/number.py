from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, SIGMA
from ...itn.readers.cardinal import CardinalReader as ItnCardinal
from ...itn.readers.decimal import DecimalReader as ItnDecimal

_itn_cardinal = ItnCardinal()
_itn_decimal = ItnDecimal(_itn_cardinal)

# The ITN graph reads both ``bin`` and ``bir bin`` as 1000 (likewise ``yüz``/``bir yüz``) at the same weight, so the
# inverse would pick between them by state order.  Penalise the ``bir`` variants: 1000 → ``bin``, 100 → ``yüz``.
_PREFER_BARE = pynini.cdrewrite(pynutil.add_weight(pynini.union("bir bin", "bir yüz"), 0.5), "", "", SIGMA)
CARDINAL = (pynini.invert(_itn_cardinal.graph) @ _PREFER_BARE).optimize()

DIGIT_WORDS = pynini.invert(_itn_cardinal.zero).optimize()
_spoken_digit = pynini.union(pynini.invert(_itn_cardinal.digit), DIGIT_WORDS)
DIGIT_BY_DIGIT = (_spoken_digit + pynini.closure(pynutil.insert(" ") + _spoken_digit)).optimize()

GROUP = pynini.union(
    pynini.closure(pynini.cross("0", "sıfır ")) + (pynini.closure(DIGIT, 1) @ CARDINAL),
    pynini.closure(pynini.cross("0", "sıfır "), 1) + pynini.cross("0", "sıfır"),
).optimize()

FRACTIONAL = pynini.invert(_itn_decimal.fractional).optimize()

TWO_DIGIT = pynini.invert(_itn_cardinal.two_digit).optimize()

def strip_thousand_dots() -> pynini.Fst:
    head = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)
    triple = pynutil.delete(".") + DIGIT + DIGIT + DIGIT
    return pynini.union(head + pynini.closure(triple, 1), pynini.closure(DIGIT, 1)).optimize()

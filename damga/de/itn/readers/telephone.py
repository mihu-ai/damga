from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import AREA_CODES, COUNTRY_CODES, DIGITS, MOBILE_PREFIXES, ZERO
from .cardinal import spoken_cardinal, text


def _digit_words() -> pynini.Fst:
    """One spoken token of a dictated number → its digits: a single digit or a pair (``vierunddreißig`` → 34)."""
    single = pynini.union(pynini.cross(ZERO, "0"), pynini.cross("eins", "1"),
                          *[pynini.cross(w, d) for w, d in DIGITS if d != "1"])
    pair = spoken_cardinal() @ (NONZERO_DIGIT + DIGIT)
    return pynini.union(single, pair).optimize()


def _spoken(first: pynini.Fst | None = None) -> pynini.Fst:
    """Spoken digit tokens separated by a space (a trailing comma is dropped) → the digit string."""
    token = _digit_words()
    sep = pynutil.delete(pynini.closure(",", 0, 1) + " ")
    head = token if first is None else first
    return (head + pynini.closure(sep + token)).optimize()


def national(min_digits: int = 6, max_digits: int = 12) -> pynini.Fst:
    """German national digits (no trunk ``0``) → ``30 12345678`` when the area code is known, otherwise one group."""
    digits = pynini.closure(DIGIT, min_digits, max_digits)
    known = pynini.union(*AREA_CODES, *[p + DIGIT for p in MOBILE_PREFIXES])
    split = (digits @ (known + pynini.closure(DIGIT, 4))) @ (known + pynutil.insert(" ") + pynini.closure(DIGIT))
    rest = pynini.difference(digits, known + pynini.closure(DIGIT, 4))
    return pynini.union(split, rest).optimize()


def telephone() -> pynini.Fst:
    """``plus vier neun drei null …`` → ``+49 30 …``.  A number needs an anchor (``plus`` and a known country code,
    or a leading ``null``); otherwise a run of digits stays words."""
    cc = pynini.union(*COUNTRY_CODES)
    other_cc = pynini.union(*[c for c in COUNTRY_CODES if c != "49"])
    # +49: a spoken trunk 0 is dropped
    after_cc = pynini.union(
        "49" + pynutil.insert(" ") + pynutil.delete("0").ques + ((NONZERO_DIGIT + pynini.closure(DIGIT)) @ national()),
        other_cc + pynutil.insert(" ") + (NONZERO_DIGIT + pynini.closure(DIGIT, 5, 12)),
    )
    shape = cc + pynini.closure(DIGIT, 6, 13)
    plus = pynini.cross("plus ", "+") + ((_spoken() @ shape) @ after_cc)
    # "null null vier neun …" → 0049 30 12345678
    double_zero = (pynini.cross(ZERO + " " + ZERO + " ", "00") + ((_spoken() @ shape) @ after_cc))
    # domestic: "null drei null …" → 030 …
    domestic = _spoken(pynini.cross(ZERO, "0")) @ ("0" + (NONZERO_DIGIT + pynini.closure(DIGIT, 6, 11)))
    domestic = domestic @ ("0" + national())
    return pynini.union(plus, double_zero, domestic).optimize()


class TelephoneReader(Rule):
    """German telephone numbers dictated digit by digit: ``+49 30 12345678``, ``0171 1234567``."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(telephone())).optimize()

"""German number readings as finite-state transducers, digits → words; ITN uses the inverses.

Below a million a number is one word; "hundert" and "tausend" without "ein":

    25000       fünfundzwanzigtausend
    2500000     zwei Millionen fünfhunderttausend
"""
from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ..core.rules import DIGIT, NONZERO_DIGIT, SIGMA
from .lexicon import BIG_SCALES, DIGITS, TEENS, TIES, ZERO

ONES = pynini.union(*[pynini.cross(d, w) for w, d in DIGITS]).optimize()          # 1 → ein (inside a compound)
TEEN = pynini.union(*[pynini.cross(d, w) for w, d in TEENS]).optimize()
_TIE_WORD = dict((d, w) for w, d in TIES)
_ONE_WORD = dict((d, w) for w, d in DIGITS)

# 10..99, two digits: the unit is said before the tens (21 → einundzwanzig), so every pair is listed.
TENS = pynini.union(
    TEEN,
    *[pynini.cross(t + "0", _TIE_WORD[t]) for t in _TIE_WORD],
    *[pynini.cross(t + u, _ONE_WORD[u] + "und" + _TIE_WORD[t]) for t in _TIE_WORD for u in _ONE_WORD],
).optimize()
TWO = pynini.union(ONES, TENS).optimize()                                          # 1..99
_HUNDRED_LEAD = pynini.union(pynini.cross("1", ""), pynini.difference(NONZERO_DIGIT, "1") @ ONES)
HUNDREDS = (_HUNDRED_LEAD + pynutil.insert("hundert")
            + pynini.union(pynutil.delete("00"), pynutil.delete("0") + ONES, TENS)).optimize()   # 100..999
_GROUP = pynini.union(ONES, TENS, HUNDREDS).optimize()                             # 1..999, no leading zero
_THREE = pynini.union(pynutil.delete("00") + ONES, pynutil.delete("0") + TENS, HUNDREDS).optimize()  # 001..999
_THOUSAND_LEAD = pynini.union(pynini.cross("1", ""), pynini.difference(pynini.project(_GROUP, "input"), "1") @ _GROUP)
# 1..999999 as one word
_BELOW_MILLION = pynini.union(
    _GROUP,
    _THOUSAND_LEAD + pynutil.insert("tausend") + pynini.union(pynutil.delete("000"), _THREE),
).optimize()
# exactly six digits after a big scale word (never 000000, that is said as nothing by the caller)
_THOUSANDS3 = pynini.union(pynini.cross("001", ""),
                           pynini.difference(pynini.project(_THREE, "input"), "001") @ _THREE)
_SIX = pynini.union(
    pynutil.delete("000") + _THREE,
    _THOUSANDS3 + pynutil.insert("tausend") + pynini.union(pynutil.delete("000"), _THREE),
).optimize()


def _cardinal_raw() -> pynini.Fst:
    graphs = [_BELOW_MILLION]
    # 10^6 .. 10^15: groups of three digits for the big scales, each followed by the next six-digit tail
    for k, (sg, pl) in enumerate(BIG_SCALES):
        lead = pynini.union(pynini.cross("1", "eine " + sg), pynini.difference(pynini.project(_GROUP, "input"), "1") @ _GROUP + pynutil.insert(" " + pl))
        tail = pynini.union(pynutil.delete("000000"), pynutil.insert(" ") + _SIX)
        g = lead
        # the scales below this one, each a group of three digits ("000" says nothing)
        for sg2, pl2 in reversed(BIG_SCALES[:k]):
            g += pynini.union(pynutil.delete("000"),
                              pynutil.insert(" ") + pynini.union(pynutil.delete("00") + pynini.cross("1", "eine " + sg2),
                                                                 pynini.difference(pynini.project(_THREE, "input"), "001") @ _THREE + pynutil.insert(" " + pl2)))
        graphs.append(g + tail)
    return pynini.union(pynini.cross("0", ZERO), *graphs).optimize()


_RAW = _cardinal_raw()
# A number that ends in a bare "ein" says "eins" (1, 101, 1001, 2000001); inside a compound it stays "ein".
_FINAL_EINS = pynini.cdrewrite(pynini.cross("ein", "eins"), "", "[EOS]", SIGMA)
CARDINAL = (_RAW @ _FINAL_EINS).optimize()
# Before a noun: 1 Euro → ein Euro; 21 Euro → einundzwanzig Euro.
CARDINAL_ATTRIBUTIVE = _RAW

# Digit by digit (after the decimal comma, telephone numbers): 0532 → null fünf drei zwei
DIGIT_WORD = pynini.union(pynini.cross("0", ZERO), pynini.cross("1", "eins"),
                          pynini.difference(NONZERO_DIGIT, "1") @ ONES).optimize()
DIGITS_SPOKEN = (DIGIT_WORD + pynini.closure(pynutil.insert(" ") + DIGIT_WORD)).optimize()

# Years: 1100..1999 by hundreds, 2000..2019 as the number, from 2020 by pairs (zwanzig zwanzig).
_HUNDREDS_YEAR = ((pynini.union("11", "12", "13", "14", "15", "16", "17", "18", "19") + DIGIT + DIGIT)
                  @ (TEEN + pynutil.insert("hundert") + pynini.union(pynutil.delete("00"), pynutil.delete("0") + ONES, TENS))
                  @ _FINAL_EINS)
_PAIR_YEAR = (pynini.accep("20") + NONZERO_DIGIT + DIGIT) @ (pynini.cross("20", "zwanzig ") + TENS)
YEAR = pynini.union(
    _HUNDREDS_YEAR,
    (pynini.union("10", "200", "201") + pynini.closure(DIGIT, 1, 2)) @ (pynini.closure(DIGIT, 4, 4) @ CARDINAL),
    (pynini.accep("20") + pynini.union(*"23456789") + DIGIT) @ _PAIR_YEAR,
).optimize()
# Every way a year is said (ITN and TN variants): also pairs written apart or together, and 2020..2099 as a number.
_PAIRS = pynini.union((pynini.accep("20") + NONZERO_DIGIT + DIGIT) @ _PAIR_YEAR,
                      (pynini.accep("19") + NONZERO_DIGIT + DIGIT) @ (pynini.cross("19", "neunzehn ") + TENS))
YEAR_SPOKEN = pynini.union(
    YEAR,
    _PAIRS,
    _PAIRS @ pynini.cdrewrite(pynutil.delete(" "), "", "", SIGMA),
    (pynini.accep("20") + DIGIT + DIGIT) @ CARDINAL,
).optimize()

# Ordinal stems: 1 → erst, 3 → dritt, 7 → siebt, 8 → acht, other numbers below 20 + t, from 20 on + st.
_LETTERS = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüß "))
_ORD_END = pynini.union(
    pynini.cross("ein", "erst"), pynini.cross("drei", "dritt"), pynini.cross("sieben", "siebt"),
    pynini.accep("acht"),
    *[pynini.cross(w, w + "t") for w in ("zwei", "vier", "fünf", "sechs", "neun", "zehn", "elf", "zwölf")],
    pynini.cross("zig", "zigst"), pynini.cross("ßig", "ßigst"),
    pynini.cross("hundert", "hundertst"), pynini.cross("tausend", "tausendst"),
)
ORDINAL_STEM = (_RAW @ (_LETTERS + _ORD_END)).optimize()
ENDINGS = ("e", "en", "er", "es", "em")


def ordinal(ending: str) -> pynini.Fst:
    """digits → ordinal with an ending: ordinal("en")("3") = dritten"""
    return (ORDINAL_STEM + pynutil.insert(ending)).optimize()


def strip_thousands() -> pynini.Fst:
    """``25.000`` / ``25 000`` → ``25000``; a number without separators passes through."""
    head = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)
    sep = pynini.union(".", " ", " ", " ")
    return pynini.union(head + pynini.closure(pynutil.delete(sep) + DIGIT + DIGIT + DIGIT, 1),
                        "0", NONZERO_DIGIT + pynini.closure(DIGIT)).optimize()


def group_thousands(min_digits: int = 5) -> pynini.Fst:
    """``25000`` → ``25.000``; four digits stay as they are (``1300``, ``2012``)."""
    triple = pynutil.insert(".") + DIGIT + DIGIT + DIGIT
    head = pynini.union(DIGIT, DIGIT + DIGIT, DIGIT + DIGIT + DIGIT)
    return pynini.union(pynini.closure(DIGIT, 1, min_digits - 1),
                        pynini.closure(DIGIT, min_digits) @ (head + pynini.closure(triple))).optimize()

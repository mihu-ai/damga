"""English number readings as finite-state transducers, digits → words; ITN uses the inverses.

    105         one hundred and five
    1984 (year) nineteen eighty four
"""
from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ..core.rules import DIGIT, NONZERO_DIGIT
from .lexicon import DIGITS, ORDINAL_DIGITS, ORDINAL_TEENS, ORDINAL_TIES, SCALES, TEENS, TIES, ZERO


def _map(pairs: list[tuple[str, str]]) -> pynini.Fst:
    """digits → word"""
    return pynini.union(*[pynini.cross(d, w) for w, d in pairs]).optimize()


ONES = _map(DIGITS)                                   # 1 → one
TEEN = _map(TEENS)                                    # 13 → thirteen
TIE = _map(TIES)                                      # 2 → twenty (the tens digit)
ZERO_WORD = pynini.cross("0", ZERO)

# 10..99, two digits.
TENS = pynini.union(
    TEEN,
    TIE + pynutil.delete("0"),
    TIE + pynutil.insert(" ") + ONES,
).optimize()
# 1..99 as written (no leading zero).
TWO = pynini.union(ONES, TENS).optimize()
# 100..999
HUNDREDS = (ONES + pynutil.insert(" hundred")
            + pynini.union(pynutil.delete("00"),
                           pynutil.insert(" and ") + pynutil.delete("0") + ONES,
                           pynutil.insert(" and ") + TENS)).optimize()
# The American reading, without "and": 105 → one hundred five.
HUNDREDS_NO_AND = (ONES + pynutil.insert(" hundred")
                   + pynini.union(pynutil.delete("00"),
                                  pynutil.insert(" ") + pynutil.delete("0") + ONES,
                                  pynutil.insert(" ") + TENS)).optimize()
# A group of exactly three digits after a scale: "000" says nothing, "005" → "and five" when it is the last group.
_SMALL_LAST = pynini.union(pynutil.delete("00") + ONES, pynutil.delete("0") + TENS).optimize()


def _cardinal(and_word: bool = True, scales: list[str] = SCALES) -> pynini.Fst:
    hundreds = HUNDREDS if and_word else HUNDREDS_NO_AND
    three = pynini.union(_SMALL_LAST, hundreds)
    lead = pynini.union(ONES, TENS, hundreds)
    graphs = [lead]
    for n_groups in range(2, len(scales) + 2):
        g = lead + pynutil.insert(" " + scales[n_groups - 2])
        for k in range(n_groups - 2, 0, -1):          # middle groups, each with its scale
            g += pynini.union(pynutil.delete("000"), pynutil.insert(" ") + three + pynutil.insert(" " + scales[k - 1]))
        last = pynini.union(
            pynutil.delete("000"),
            (pynutil.insert(" and ") if and_word else pynutil.insert(" ")) + _SMALL_LAST,
            pynutil.insert(" ") + hundreds,
        )
        graphs.append(g + last)
    return pynini.union(ZERO_WORD, *graphs).optimize()


CARDINAL = _cardinal(True)
CARDINAL_NO_AND = _cardinal(False)
# ITN also hears the scales past a trillion (``ninety seven quadrillion …``); TN reads such long numbers digit by digit.
LONG_SCALES = SCALES + ["quadrillion", "quintillion", "sextillion"]
CARDINAL_LONG = _cardinal(True, LONG_SCALES)
CARDINAL_LONG_NO_AND = _cardinal(False, LONG_SCALES)
# 1100..9999 counted in hundreds (1500 → fifteen hundred), for ITN only; round thousands are excluded.
_LAST_TWO = pynini.union(pynutil.delete("0") + ONES, TENS)
HUNDREDS_COUNTED = ((NONZERO_DIGIT + NONZERO_DIGIT) @ TENS + pynutil.insert(" hundred")
                    + pynini.union(pynutil.delete("00"), pynutil.insert(" ") + _LAST_TWO,
                                   pynutil.insert(" and ") + _LAST_TWO)).optimize()

# Digit by digit: 0532 → zero five three two (telephone numbers, decimals after the point).
DIGIT_WORD = pynini.union(ZERO_WORD, ONES).optimize()
DIGITS_SPOKEN = (DIGIT_WORD + pynini.closure(pynutil.insert(" ") + DIGIT_WORD)).optimize()
DIGITS_OH = (pynini.union(pynini.cross("0", "oh"), ONES)
             + pynini.closure(pynutil.insert(" ") + pynini.union(pynini.cross("0", "oh"), ONES))).optimize()

# 1100..1999 and 2010..2099 as two pairs; 1900 → nineteen hundred; 1905 → nineteen oh five.
_PAIR = TENS
_PAIRS = pynini.union(
    (pynini.union("1", "2") + DIGIT) @ _PAIR + pynutil.insert(" ") + pynini.union(
        _PAIR, pynini.cross("00", "hundred"), pynutil.delete("0") + pynutil.insert("oh ") + ONES),
).optimize()
YEAR = pynini.union(
    (pynini.union("11", "12", "13", "14", "15", "16", "17", "18", "19") + DIGIT + DIGIT) @ _PAIRS,
    (pynini.accep("10") + NONZERO_DIGIT + DIGIT) @ _PAIRS,                     # 1066 → ten sixty six
    (pynini.accep("20") + pynini.union("2", "3", "4", "5", "6", "7", "8", "9") + DIGIT) @ _PAIRS,
    # 2000..2009 and 1000..1099: "two thousand and five"; 2010..2019 "two thousand thirteen"
    (pynini.union("200", "100") + DIGIT) @ CARDINAL,
    (pynini.accep("201") + DIGIT) @ CARDINAL_NO_AND,
).optimize()

# Every way a year is said, for ITN: the pairs for all of 1100..2099 as well as the default readings above.
YEAR_SPOKEN = pynini.union(
    YEAR,
    (pynini.union("10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20") + NONZERO_DIGIT + DIGIT) @ _PAIRS,
    (pynini.union("11", "12", "13", "14", "15", "16", "17", "18", "19", "20") + "0" + NONZERO_DIGIT) @ _PAIRS,
    (pynini.accep("20") + NONZERO_DIGIT + DIGIT) @ CARDINAL_NO_AND,
    (pynini.accep("200") + NONZERO_DIGIT) @ CARDINAL_NO_AND,
    (pynini.accep("20") + NONZERO_DIGIT + DIGIT) @ CARDINAL,
).optimize()

# Ordinals: the last word of the cardinal becomes its ordinal (twenty one → twenty first, a hundred → hundredth).
_LAST_WORD = pynini.union(
    *[pynini.cross(w, o) for (w, _), (o, _) in zip(DIGITS, ORDINAL_DIGITS)],
    *[pynini.cross(w, o) for (w, _), (o, _) in zip(TEENS, ORDINAL_TEENS)],
    *[pynini.cross(w, o) for (w, _), (o, _) in zip(TIES, ORDINAL_TIES)],
    pynini.cross("hundred", "hundredth"), *[pynini.cross(s, s + "th") for s in SCALES],
).optimize()
_WORDS = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyz "))
_TO_ORDINAL = (pynini.closure(_WORDS + " ", 0, 1) + _LAST_WORD).optimize()
ORDINAL = (CARDINAL @ _TO_ORDINAL).optimize()     # 21 → twenty first (written 21st; the suffix is checked by readers)
# Every way an ordinal is said, for ITN: with or without "and" (one hundred eleventh), in hundreds (eleven hundred
# twenty first).
ORDINAL_SPOKEN = (pynini.union(CARDINAL, CARDINAL_NO_AND, HUNDREDS_COUNTED) @ _TO_ORDINAL).optimize()

# Written ordinal suffix that goes with the last digit: 1st 2nd 3rd 4th 11th 12th 13th 21st 101st.
_LAST = pynini.union(
    pynini.closure(DIGIT) + "1" + DIGIT + "th",
    pynini.closure(DIGIT) + pynini.union("0", "2", "3", "4", "5", "6", "7", "8", "9") + "1" + "st",
    "1st",
    pynini.closure(DIGIT) + pynini.union("0", "2", "3", "4", "5", "6", "7", "8", "9") + "2" + "nd",
    "2nd",
    pynini.closure(DIGIT) + pynini.union("0", "2", "3", "4", "5", "6", "7", "8", "9") + "3" + "rd",
    "3rd",
    pynini.closure(DIGIT) + pynini.union("0", "4", "5", "6", "7", "8", "9") + "th",
    pynini.union("4", "5", "6", "7", "8", "9") + "th",
)
ORDINAL_WRITTEN = pynini.intersect(pynini.closure(DIGIT, 1) + pynini.union("st", "nd", "rd", "th"), _LAST).optimize()


def strip_thousands() -> pynini.Fst:
    """``25,000`` → ``25000``; a number with no commas passes through."""
    head = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)
    return pynini.union(head + pynini.closure(pynutil.delete(",") + DIGIT + DIGIT + DIGIT, 1),
                        "0", NONZERO_DIGIT + pynini.closure(DIGIT)).optimize()


def group_thousands(min_digits: int = 5) -> pynini.Fst:
    """``25000`` → ``25,000``; shorter numbers (``2012``, ``1000``) stay as they are."""
    triple = pynutil.insert(",") + DIGIT + DIGIT + DIGIT
    head = pynini.union(DIGIT, DIGIT + DIGIT, DIGIT + DIGIT + DIGIT)
    grouped = head + pynini.closure(triple)
    return pynini.union(pynini.closure(DIGIT, 1, min_digits - 1), pynini.closure(DIGIT, min_digits) @ grouped).optimize()


# International dialling codes; ITU codes are prefix-free, so a number starts with at most one of them.
COUNTRY_CODES = (
    "1", "7", "20", "27", "30", "31", "32", "33", "34", "36", "39", "40", "41", "43", "44", "45", "46", "47", "48",
    "49", "51", "52", "53", "54", "55", "56", "57", "58", "60", "61", "62", "63", "64", "65", "66", "81", "82", "84",
    "86", "90", "91", "92", "93", "94", "95", "98", "212", "213", "216", "234", "254", "351", "352", "353", "354",
    "355", "356", "357", "358", "359", "370", "371", "372", "380", "381", "385", "386", "420", "421", "852", "886",
    "966", "971", "972", "974",
)

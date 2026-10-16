"""Spanish number readings as finite-state transducers, digits → words; ITN uses the inverses.

``21`` is veintiuno, veintiún before a noun and veintiuna before a feminine noun.
"""
from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ..core.rules import DIGIT, NONZERO_DIGIT
from .lexicon import DIGITS, HUNDREDS, ORDINAL_TENS, ORDINAL_UNITS, ORDINALS, TEENS, TIES, TWENTIES, ZERO

_LOWER = "abcdefghijklmnopqrstuvwxyzáéíóúüñ"
WORDS = pynini.closure(pynini.union(*_LOWER, " ")).optimize()


def _map(pairs: list[tuple[str, str]]) -> pynini.Fst:
    return pynini.union(*[pynini.cross(d, w) for w, d in pairs]).optimize()


ONES = _map(DIGITS)
ZERO_WORD = pynini.cross("0", ZERO)
TENS = pynini.union(
    _map(TEENS), _map(TWENTIES),
    _map(TIES) + pynutil.delete("0"),
    _map(TIES) + pynutil.insert(" y ") + ONES,
).optimize()                                                    # 10..99
TWO = pynini.union(ONES, TENS).optimize()                       # 1..99
_HUNDREDS = _map(HUNDREDS) + pynini.union(pynutil.delete("00"), pynutil.insert(" ") + pynutil.delete("0") + ONES,
                                          pynutil.insert(" ") + TENS)
HUNDRED = pynini.union(pynini.cross("100", "cien"),
                       pynini.difference(pynini.project(_HUNDREDS, "input"), "100") @ _HUNDREDS).optimize()
UPTO999 = pynini.union(ONES, TENS, HUNDRED).optimize()          # 1..999, no leading zero
_EXACT3 = pynini.union(pynutil.delete("00") + ONES, pynutil.delete("0") + TENS, HUNDRED).optimize()   # 001..999
_ENDS_UNO = pynini.closure(WORDS + " ", 0, 1) + pynini.union("uno", "veintiuno")
_APOCOPE = pynini.union(
    pynini.difference(WORDS, _ENDS_UNO),
    pynini.closure(WORDS + " ", 0, 1) + pynini.union(pynini.cross("uno", "un"), pynini.cross("veintiuno", "veintiún")),
).optimize()


def apocope(fst: pynini.Fst) -> pynini.Fst:
    """"uno" before a noun, and before mil/millones, is "un": veintiún mil, treinta y un millones, ciento un mil."""
    return (fst @ _APOCOPE).optimize()


_STRIP = pynutil.delete(pynini.closure("0")) + NONZERO_DIGIT + pynini.closure(DIGIT)   # 000123 → 123
_REST3 = pynini.union(pynutil.delete("000"), pynutil.insert(" ") + _EXACT3)
_THOUSANDS = pynini.union(
    pynini.cross("1", "mil"),
    (pynini.difference(pynini.project(UPTO999, "input"), "1") @ apocope(UPTO999)) + pynutil.insert(" mil"),
)
BELOW_MILLION = pynini.union(UPTO999, _THOUSANDS + _REST3).optimize()                # 1..999999
_SIX = pynini.difference(DIGIT ** 6, "000000")
_REST6 = pynini.union(pynutil.delete("000000"), pynutil.insert(" ") + (_SIX @ _STRIP @ BELOW_MILLION))
_MULTIPLIER = pynini.difference(pynini.project(BELOW_MILLION, "input"), "1") @ apocope(BELOW_MILLION)
MILLIONS = pynini.union(pynini.cross("1", "un millón"), _MULTIPLIER + pynutil.insert(" millones")).optimize()
BILLIONS = pynini.union(pynini.cross("1", "un billón"), _MULTIPLIER + pynutil.insert(" billones")).optimize()
_MILLION_GROUP = pynini.union(pynutil.delete("000000"), pynutil.insert(" ") + (_SIX @ _STRIP @ MILLIONS))
CARDINAL = pynini.union(
    ZERO_WORD,
    BELOW_MILLION,
    MILLIONS + _REST6,                                          # < 10^12 (mil millones = 10^9)
    BILLIONS + _MILLION_GROUP + _REST6,                         # < 10^18
).optimize()
CARDINAL_APOC = apocope(CARDINAL)

# Feminine: only the part after the last millón/millones agrees (doscientos millones de personas).
_FEM_WORD = pynini.union(pynini.cross("uno", "una"), pynini.cross("veintiuno", "veintiuna"),
                         *[pynini.cross(w, w[:-2] + "as") for w, _ in HUNDREDS[1:]])
_NO_MILL = pynini.difference(WORDS, WORDS + "mill" + WORDS)
_FEM = pynini.cdrewrite(_FEM_WORD, pynini.union("[BOS]", " "), pynini.union("[EOS]", " " + _NO_MILL + "[EOS]"),
                        pynini.closure(pynini.union(*_LOWER, " ")))
CARDINAL_FEM = (CARDINAL @ _FEM).optimize()

DIGIT_WORD = pynini.union(ZERO_WORD, ONES).optimize()
DIGITS_SPOKEN = (DIGIT_WORD + pynini.closure(pynutil.insert(" ") + DIGIT_WORD)).optimize()

# Ordinals 1..99 (masculine; the feminine ends in -a): 13.º decimotercero, 21.º vigésimo primero.
ORDINAL = pynini.union(
    _map(ORDINALS),
    _map(ORDINAL_TENS) + pynutil.delete("0"),
    _map(ORDINAL_TENS) + pynutil.insert(" ") + _map(ORDINAL_UNITS),
    pynini.cross("100", "centésimo"),
).optimize()
ORDINAL = (pynini.difference(pynini.project(ORDINAL, "input"), pynini.project(_map(ORDINALS), "input"))
           @ ORDINAL | _map(ORDINALS)).optimize()
_FEM_ORD = pynini.cdrewrite(pynini.cross("o", "a"), "", pynini.union(" ", "[EOS]"), pynini.closure(pynini.union(*_LOWER, " ")))
ORDINAL_FEM = (ORDINAL @ _FEM_ORD).optimize()
# primero/tercero before a masculine noun: primer, tercer
ORDINAL_APOC = (ORDINAL @ pynini.cdrewrite(pynini.union(pynini.cross("primero", "primer"), pynini.cross("tercero", "tercer")),
                                           "", "[EOS]", pynini.closure(pynini.union(*_LOWER, " ")))).optimize()


def group_thousands(sep: str = ".", min_digits: int = 5) -> pynini.Fst:
    """``25000`` → ``25.000``; shorter numbers (``2008``, ``1500``) stay as they are."""
    triple = pynutil.insert(sep) + DIGIT + DIGIT + DIGIT
    head = pynini.union(DIGIT, DIGIT + DIGIT, DIGIT + DIGIT + DIGIT)
    return pynini.union(pynini.closure(DIGIT, 1, min_digits - 1),
                        pynini.closure(DIGIT, min_digits) @ (head + pynini.closure(triple))).optimize()


def strip_thousands() -> pynini.Fst:
    """``25.000`` / ``25 000`` → ``25000``; a number without separators passes through."""
    head = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)
    sep = pynutil.delete(pynini.union(".", " ", " ", " "))
    return pynini.union(head + pynini.closure(sep + DIGIT + DIGIT + DIGIT, 1), "0",
                        NONZERO_DIGIT + pynini.closure(DIGIT)).optimize()

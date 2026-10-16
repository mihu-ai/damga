"""French number readings as finite-state transducers, digits → words; ITN uses the inverses.

Traditional spelling: hyphens below a hundred, "et" for 21…71 (vingt et un, quatre-vingt-un, deux cents).
"""
from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ..core.rules import DIGIT, NONZERO_DIGIT
from .lexicon import TEENS, TIES, UNITS, ZERO

_LOWER = "abcdefghijklmnopqrstuvwxyzàâäæçéèêëîïôœùûüÿ"
LETTERS = pynini.union(*_LOWER).optimize()
WORDS = pynini.closure(pynini.union(LETTERS, " ", "-")).optimize()


def _map(pairs: list[tuple[str, str]]) -> pynini.Fst:
    return pynini.union(*[pynini.cross(d, w) for w, d in pairs]).optimize()


UNIT = _map(UNITS)                                          # 1..9
TEEN = _map(TEENS)                                          # 10..19
TIE = _map(TIES)                                            # tens digit 2..6
UNIT_NO_ONE = _map(UNITS[1:])                               # 2..9
ZERO_WORD = pynini.cross("0", ZERO)

# 10..99, exactly two digits
_REGULAR = (TIE + pynini.union(pynutil.delete("0"),
                               pynini.cross("1", " et un"),
                               pynutil.insert("-") + UNIT_NO_ONE)).optimize()          # 20..69
_SEVENTY = (pynini.cross("7", "soixante") + pynini.union(
    pynini.cross("1", " et onze"),
    pynutil.insert("-") + (pynini.difference(DIGIT, "1") @ (pynutil.insert("1") + DIGIT) @ TEEN))).optimize()
_EIGHTY = (pynini.cross("8", "quatre-vingt") + pynini.union(pynini.cross("0", "s"),
                                                             pynutil.insert("-") + UNIT)).optimize()
_NINETY = (pynini.cross("9", "quatre-vingt-") + ((pynutil.insert("1") + DIGIT) @ TEEN)).optimize()
TENS = pynini.union(pynutil.delete("1") + ((pynutil.insert("1") + DIGIT) @ TEEN), _REGULAR, _SEVENTY, _EIGHTY,
                    _NINETY).optimize()
TWO = pynini.union(UNIT, TENS).optimize()                  # 1..99

# 100..999
HUNDREDS = pynini.union(
    pynini.cross("1", "cent") + pynini.union(pynutil.delete("00"), pynutil.insert(" ") + pynutil.delete("0") + UNIT,
                                              pynutil.insert(" ") + TENS),
    UNIT_NO_ONE + pynini.union(pynini.cross("00", " cents"),
                               pynutil.insert(" cent ") + pynutil.delete("0") + UNIT,
                               pynutil.insert(" cent ") + TENS),
).optimize()
_THREE = pynini.union(pynutil.delete("00") + UNIT, pynutil.delete("0") + TENS, HUNDREDS).optimize()   # 001..999
_LEAD = pynini.union(UNIT, TENS, HUNDREDS).optimize()                                                    # 1..999

# "quatre-vingts" and "deux cents" lose their s before "mille" (an adjective), keep it before "millions" (a noun).
_DROP_S = pynini.cdrewrite(pynini.union(pynini.cross("vingts", "vingt"), pynini.cross("cents", "cent")), "",
                           " mille", pynini.closure(pynini.union(LETTERS, " ", "-"))).optimize()


def _scaled(word: str) -> pynini.Fst:
    """A group before a noun scale word: un million, deux millions."""
    return pynini.union(pynini.cross("1", "un " + word), (pynini.difference(pynini.project(_LEAD, "input"), "1") @ _LEAD) + pynutil.insert(f" {word}s"))


def _group_scaled(word: str) -> pynini.Fst:
    """The same for a middle group of exactly three digits; 000 says nothing."""
    return pynini.union(pynutil.delete("000"), pynutil.insert(" ") + (
        pynini.union(pynini.cross("001", "un " + word),
                     (pynini.difference(pynini.project(_THREE, "input"), "001") @ _THREE) + pynutil.insert(f" {word}s"))))


_THOUSANDS_LEAD = pynini.union(pynini.cross("1", "mille"), (pynini.difference(pynini.project(_LEAD, "input"), "1") @ _LEAD)
                               + pynutil.insert(" mille"))
_THOUSANDS_MID = pynini.union(pynutil.delete("000"), pynutil.insert(" ") + pynini.union(
    pynini.cross("001", "mille"), (pynini.difference(pynini.project(_THREE, "input"), "001") @ _THREE) + pynutil.insert(" mille")))
_LAST = pynini.union(pynutil.delete("000"), pynutil.insert(" ") + _THREE)


def _cardinal() -> pynini.Fst:
    graphs = [ZERO_WORD, _LEAD,
              _THOUSANDS_LEAD + _LAST,
              _scaled("million") + _THOUSANDS_MID + _LAST,
              _scaled("milliard") + _group_scaled("million") + _THOUSANDS_MID + _LAST,
              _scaled("billion") + _group_scaled("milliard") + _group_scaled("million") + _THOUSANDS_MID + _LAST]
    return (pynini.union(*graphs) @ _DROP_S).optimize()


CARDINAL = _cardinal()
# Feminine: the final "un" becomes "une" (vingt et une voix, une heure, cent une pages).
_FEM = (pynini.cdrewrite(pynini.cross("un", "une"), pynini.union(" ", "-"), "[EOS]", WORDS)
        @ pynini.cdrewrite(pynini.cross("un", "une"), "[BOS]", "[EOS]", WORDS))
CARDINAL_FEM = (CARDINAL @ _FEM).optimize()

DIGIT_WORD = pynini.union(ZERO_WORD, UNIT).optimize()

# Ordinals: the last word takes -ième; 1 is premier/première.
_ORD_LAST = pynini.union(
    pynini.cross("un", "unième"), pynini.cross("deux", "deuxième"), pynini.cross("trois", "troisième"),
    pynini.cross("quatre", "quatrième"), pynini.cross("cinq", "cinquième"), pynini.cross("six", "sixième"),
    pynini.cross("sept", "septième"), pynini.cross("huit", "huitième"), pynini.cross("neuf", "neuvième"),
    pynini.cross("dix", "dixième"), pynini.cross("onze", "onzième"), pynini.cross("douze", "douzième"),
    pynini.cross("treize", "treizième"), pynini.cross("quatorze", "quatorzième"), pynini.cross("quinze", "quinzième"),
    pynini.cross("seize", "seizième"), pynini.cross("vingt", "vingtième"), pynini.cross("vingts", "vingtième"),
    pynini.cross("trente", "trentième"), pynini.cross("quarante", "quarantième"),
    pynini.cross("cinquante", "cinquantième"), pynini.cross("soixante", "soixantième"),
    pynini.cross("cent", "centième"), pynini.cross("cents", "centième"), pynini.cross("mille", "millième"),
    pynini.cross("million", "millionième"), pynini.cross("millions", "millionième"),
    pynini.cross("milliard", "milliardième"), pynini.cross("milliards", "milliardième"),
).optimize()
# The ordinal of a round million has no "un": le millionième, le milliardième (as le millième).
_NO_ONE = pynini.cdrewrite(pynutil.delete("un "), "[BOS]", pynini.union("millionième", "milliardième") + "[EOS]", WORDS)
_TO_ORDINAL = ((pynini.closure(WORDS + pynini.union(" ", "-"), 0, 1) + _ORD_LAST) @ _NO_ONE).optimize()
ORDINAL = pynini.union(pynini.cross("1", "premier"),
                       (pynini.difference(pynini.project(CARDINAL, "input"), pynini.union("0", "1")) @ CARDINAL) @ _TO_ORDINAL
                       ).optimize()
ORDINAL_FEM = pynini.union(pynini.cross("1", "première"),
                           (pynini.difference(pynini.project(CARDINAL, "input"), pynini.union("0", "1")) @ CARDINAL)
                           @ _TO_ORDINAL).optimize()


def strip_thousands() -> pynini.Fst:
    """``15 000`` / ``15.000`` / ``15000`` → ``15000``."""
    head = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)
    sep = pynutil.delete(pynini.union(" ", ".", " ", " "))
    return pynini.union(head + pynini.closure(sep + DIGIT + DIGIT + DIGIT, 1), "0",
                        NONZERO_DIGIT + pynini.closure(DIGIT)).optimize()


def group_thousands(min_digits: int = 5) -> pynini.Fst:
    """``15000`` → ``15 000``; four digits stay together (``2016``, ``1500``)."""
    triple = pynutil.insert(" ") + DIGIT + DIGIT + DIGIT
    head = pynini.union(DIGIT, DIGIT + DIGIT, DIGIT + DIGIT + DIGIT)
    return pynini.union(pynini.closure(DIGIT, 1, min_digits - 1),
                        pynini.closure(DIGIT, min_digits) @ (head + pynini.closure(triple))).optimize()


def flexible() -> pynini.Fst:
    """Canonical spelling → every way it is written: a space or hyphen may be a space, a hyphen or nothing
    (``deuxmilleseize``), and the plural s of vingts/cents/millions/milliards/billions is optional.  Applied to the
    cardinal's output before it is inverted for ITN."""
    sep = pynini.union(pynini.cross(" ", pynini.union(" ", "-", "")), pynini.cross("-", pynini.union(" ", "-", "")))
    words = ("vingt", "cent", "million", "milliard", "billion")
    plural = pynini.union(*[pynini.cross(pynini.union(w, w + "s"), pynini.union(w, w + "s")) for w in words])
    return pynini.closure(pynini.union(LETTERS, sep, plural)).optimize()

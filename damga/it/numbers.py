"""Italian number readings as finite-state transducers, digits → words; ITN uses the inverses.

Numbers are written as one word up to the millions (``2016`` → ``duemilasedici``); ITN also reads the spaced forms.
"""
from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ..core.rules import DIGIT, NONZERO_DIGIT, SIGMA
from .lexicon import ORDINAL_UNITS, TEENS, TENS, UNITS, ZERO

_UNIT = dict((d, w) for w, d in UNITS)
_TEEN = dict((d, w) for w, d in TEENS)
_TENS = dict((d, w) for w, d in TENS)
_ORD_SMALL = dict((int(d), w) for w, d in ORDINAL_UNITS)
_LETTER = pynini.union(*"abcdefghijklmnopqrstuvwxyzàèéìòù").optimize()


def say_below_thousand(n: int) -> str:
    """1..999 as one word, without the accent on a final tre (added by ``ACCENT``)."""
    if n < 10:
        return _UNIT[str(n)]
    if n < 20:
        return _TEEN[str(n)]
    if n < 100:
        tens, unit = divmod(n, 10)
        word = _TENS[str(tens)]
        if unit == 0:
            return word
        u = _UNIT[str(unit)]
        return (word[:-1] if u[0] in "uo" else word) + u
    hundreds, rest = divmod(n, 100)
    head = "cento" if hundreds == 1 else _UNIT[str(hundreds)] + "cento"
    if rest == 8:                       # centotto, but centoottanta
        return head[:-1] + "otto"
    return head + (say_below_thousand(rest) if rest else "")


# tre at the end of a compound: ventitré, centotré, milletré (not tre alone, not tremila)
ACCENT = pynini.cdrewrite(pynini.cross("tre", "tré"), pynini.union(_LETTER, "|"), pynini.union(" ", "|", "[EOS]"), SIGMA).optimize()

_P3 = pynini.union(*[pynini.cross(f"{n:03d}", say_below_thousand(n)) for n in range(1, 1000)]).optimize()
_ZERO3 = pynini.cross("000", "")
_HUNDREDS3 = pynini.union(*[pynini.cross(f"{n:03d}", say_below_thousand(n)) for n in range(2, 1000)]).optimize()

# Twelve digits: miliardi | milioni | migliaia | the rest.  "|" marks where ITN also accepts a space or " e ".
_BILLIONS = pynini.union(_ZERO3, pynini.cross("001", "un miliardo "), _HUNDREDS3 + pynutil.insert(" miliardi "))
_MILLIONS = pynini.union(_ZERO3, pynini.cross("001", "un milione "), _HUNDREDS3 + pynutil.insert(" milioni "))
_THOUSANDS = pynini.union(_ZERO3, pynini.cross("001", "mille|"), _HUNDREDS3 + pynutil.insert("mila|"))
_REST = pynini.union(_ZERO3, _P3)

_PAD = pynini.union(*[pynutil.insert("0" * (12 - n)) + NONZERO_DIGIT + pynini.closure(DIGIT, n - 1, n - 1)
                      for n in range(1, 13)]).optimize()
_TIDY = (pynini.cdrewrite(pynutil.delete("|"), "", pynini.union(" ", "[EOS]"), SIGMA)
         @ pynini.cdrewrite(pynutil.delete(" "), "", "[EOS]", SIGMA)).optimize()
# With the "|" marks kept, for ITN.
CARDINAL_MARKED = pynini.union(
    pynini.cross("0", ZERO),
    _PAD @ (_BILLIONS + _MILLIONS + _THOUSANDS + _REST) @ _TIDY @ ACCENT,
).optimize()
CARDINAL = (CARDINAL_MARKED @ pynini.cdrewrite(pynutil.delete("|"), "", "", SIGMA)).optimize()

DIGIT_WORD = pynini.union(pynini.cross("0", ZERO), *[pynini.cross(d, w) for w, d in UNITS]).optimize()
DIGITS_SPOKEN = (DIGIT_WORD + pynini.closure(pynutil.insert(" ") + DIGIT_WORD)).optimize()


def say(n: int) -> str:
    return pynini.shortestpath(pynini.accep(str(n)) @ CARDINAL).string()


def say_ordinal(n: int, ending: str = "o") -> str:
    """primo, ventunesimo, ventitreesimo, centesimo, millesimo; ``ending`` is o, a, i or e."""
    if n in _ORD_SMALL:
        word = _ORD_SMALL[n]
    else:
        word = say(n).replace("tré", "tre")
        if word.endswith("tre") or word.endswith("sei"):
            word = word + "esimo"
        else:
            word = word[:-1] + "esimo"
    return word[:-1] + ending


ORDINAL_MAX = 2100
# 1..2100 in the four endings: digits + the ending letter → the ordinal word (21o → ventunesimo, 37a → trentasettesima)
ORDINAL = pynini.union(*[pynini.cross(f"{n}{e}", say_ordinal(n, e)) for n in range(1, ORDINAL_MAX + 1)
                         for e in "oaie"]).optimize()


def strip_thousands() -> pynini.Fst:
    """``25.000`` / ``25 000`` → ``25000``; the groups are apart by points or (no-break) spaces, the same all through."""
    head = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)

    def grouped(sep: pynini.Fst) -> pynini.Fst:
        return head + pynini.closure(pynutil.delete(sep) + DIGIT + DIGIT + DIGIT, 1)

    return pynini.union(grouped(pynini.accep(".")), grouped(pynini.union(" ", "\u00a0", "\u202f")),
                        "0", NONZERO_DIGIT + pynini.closure(DIGIT)).optimize()


# A round million or billion takes "di" before what it counts: tre miliardi di euro, un milione di chilometri.
SCALE_OF = pynini.cdrewrite(pynutil.insert(" di"), pynini.union("milione", "milioni", "miliardo", "miliardi"),
                            "[EOS]", SIGMA).optimize()


def group_thousands() -> pynini.Fst:
    """``25000`` → ``25.000``; four digits from 1000 to 2099 stay as they are (``2016``, a year), other four-digit
    numbers are grouped (``5.000``)."""
    triple = pynutil.insert(".") + DIGIT + DIGIT + DIGIT
    head = pynini.union(DIGIT, DIGIT + DIGIT, DIGIT + DIGIT + DIGIT)
    grouped = head + pynini.closure(triple)
    year_like = pynini.union("1" + DIGIT + DIGIT + DIGIT, "20" + DIGIT + DIGIT)
    four = pynini.difference(NONZERO_DIGIT + DIGIT + DIGIT + DIGIT, year_like)
    return pynini.union(pynini.closure(DIGIT, 1, 3), year_like, four @ grouped,
                        pynini.closure(DIGIT, 5) @ grouped).optimize()

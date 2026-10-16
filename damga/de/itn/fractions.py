"""Spoken fractions as digits (``drei viertel`` → ``3/4``), the opt-in ``fraction_digits`` of the German ITN.

Plain Python run on the ITN output, so it needs no grammar rebuild and works with the precompiled grammars
(no pynini at runtime).  The numerator is either still a word (ITN leaves lone numbers up to twelve as words)
or already digits (``23 viertel``).

What is converted:

* ``<number> <fraction word>``: ``ein drittel`` → ``1/3``, ``23 viertel`` → ``23/4``, ``ein hundertstel`` → ``1/100``
* ``ein halb`` / ``einhalb`` → ``1/2``; ``halbe`` only after a number of two or more and with no word after it:
  ``vier halbe`` → ``4/2``, but ``zwei halbe Brote`` stays
* joined: ``dreiviertel`` → ``3/4``
* mixed numbers: ``zwei ein halb``, ``zwei und ein halb``, ``zweieinhalb``, ``eineinhalb``, ``anderthalb``
  → ``2 1/2`` / ``1 1/2``; ``zwei und drei viertel`` → ``2 3/4``

What stays: a fraction noun without a number (``die Hälfte``, ``ein Viertel`` needs ``ein``, ``viertel nach``),
inflected ``halbe`` after ``ein``/``eine`` (``eine halbe Stunde``), a fraction followed by a genitive article
(``ein Viertel der Stadt``, ``drei viertel des Weges``) and a fraction followed by a number (clock time
``drei viertel acht``).
"""
from __future__ import annotations

import re

from ..lexicon import DIGITS, TEENS, TIES

_ONES = {w: int(d) for w, d in DIGITS} | {"eins": 1, "eine": 1}
_TEENS = {w: int(d) for w, d in TEENS}
_TIES = {w: int(d) * 10 for w, d in TIES}
_TIE_RE = "|".join(_TIES)
_ONE_RE = "|".join(w for w, _ in DIGITS)
_TWO = re.compile(f"(?:({_ONE_RE})und)?({_TIE_RE})")


def _below_hundred(word: str) -> int | None:
    if word in _ONES:
        return _ONES[word]
    if word in _TEENS:
        return _TEENS[word]
    m = _TWO.fullmatch(word)
    if m:
        return _TIES[m.group(2)] + (_ONES[m.group(1)] if m.group(1) else 0)
    return None


def _below_thousand(word: str) -> int | None:
    if "hundert" in word:
        lead, _, rest = word.partition("hundert")
        hundreds = _ONES.get(lead, None) if lead else 1
        if hundreds is None or lead in ("eins", "eine"):
            return None
        tail = _below_hundred(rest) if rest else 0
        return None if tail is None else hundreds * 100 + tail
    return _below_hundred(word)


def number_value(word: str) -> int | None:
    """The value of a German cardinal word below a million (``zweiundzwanzig`` → 22), or None."""
    word = word.lower()
    if "tausend" in word:
        lead, _, rest = word.partition("tausend")
        thousands = _below_thousand(lead) if lead else 1
        tail = _below_thousand(rest) if rest else 0
        if thousands is None or tail is None or lead in ("eins", "eine"):
            return None
        return thousands * 1000 + tail
    return _below_thousand(word)


# denominators 3..19 take "-tel" (drittel, siebtel, achtel), from twenty on "-stel" (zwanzigstel, hundertstel)
_TEL = {"drittel": 3, "viertel": 4, "fünftel": 5, "sechstel": 6, "siebtel": 7, "achtel": 8, "neuntel": 9,
        "zehntel": 10, "elftel": 11, "zwölftel": 12}
_TEL |= {w + "tel": int(d) for w, d in TEENS if int(d) > 12}
_BIG = {"millionstel": 1_000_000}


def denominator(word: str) -> int | None:
    """``viertel`` → 4, ``zwanzigstel`` → 20, ``hundertstel`` → 100; None for any other word."""
    word = word.lower()
    if word in _TEL:
        return _TEL[word]
    if word in _BIG:
        return _BIG[word]
    if word.endswith("stel"):
        value = number_value(word[:-4])
        if value is not None and value >= 20:
            return value
    return None


_DIGITS = re.compile(r"-?\d+")
_HALF = ("einhalb",)
_GENITIVE = {"der", "des", "dem", "eines", "einer"}
_NO_NUMERATOR = {"ein", "eine", "eins"}   # "ein" alone is an article: only ein halb / ein <fraction> read it as 1


def _split(token: str) -> tuple[str, str]:
    word = token.rstrip(",.;:!?")
    return word, token[len(word):]


def _whole(word: str) -> str | None:
    """A whole number as digits: ``2`` → ``2``, ``zwei`` → ``2``, ``-3`` → ``-3``."""
    if _DIGITS.fullmatch(word):
        return word
    value = number_value(word)
    return None if value is None else str(value)


def _is_number(word: str) -> bool:
    return _whole(word) is not None


def _joined_mixed(word: str) -> str | None:
    """``zweieinhalb`` → ``2 1/2``, ``eineinhalb`` → ``1 1/2``, ``anderthalb`` → ``1 1/2``."""
    low = word.lower()
    if low == "anderthalb":
        return "1 1/2"
    if low.endswith("einhalb") and len(low) > len("einhalb"):
        whole = _whole(low[:-len("einhalb")])
        if whole is not None:
            return f"{whole} 1/2"
    return None


def _joined_fraction(word: str) -> str | None:
    """``einhalb`` → ``1/2``, ``dreiviertel`` → ``3/4`` (numerator word up to twelve)."""
    low = word.lower()
    if low == "einhalb":
        return "1/2"
    for den_word, den in _TEL.items():
        if low.endswith(den_word) and len(low) > len(den_word):
            num = number_value(low[:-len(den_word)])
            if num is not None and num <= 12:
                return f"{num}/{den}"
    return None


def _fraction(tokens: list[str], i: int) -> tuple[str, int] | None:
    """A fraction starting at ``tokens[i]``: (digits, tokens used), or None."""
    num_word, punct = _split(tokens[i])
    joined = _joined_mixed(num_word) or _joined_fraction(num_word)
    if joined is not None:
        return joined, 1
    if punct or i + 1 >= len(tokens):
        return None
    num = _whole(num_word)
    if num is None:
        return None
    frac_word, _ = _split(tokens[i + 1])
    low = frac_word.lower()
    if low == "halb":
        return (f"{num}/2", 2) if num in ("1", "-1") and num_word.lower() != "eins" else None
    if low == "einhalb":
        return f"{num} 1/2", 2
    if low == "halbe":
        # "zwei halbe Brote" is two half loaves: halbe reads as a fraction only when no word follows
        nxt = _split(tokens[i + 2])[0] if i + 2 < len(tokens) and not _split(tokens[i + 1])[1] else ""
        if int(num) < 2 or nxt[:1].isalpha():
            return None
        return f"{num}/2", 2
    den = denominator(frac_word)
    if den is None:
        return None
    return f"{num}/{den}", 2


def _blocked(tokens: list[str], end: int) -> bool:
    """A genitive article or a number right after the fraction keeps it words (ein Viertel der Stadt, drei viertel acht)."""
    if end >= len(tokens) or _split(tokens[end - 1])[1]:
        return False
    nxt = _split(tokens[end])[0]
    return nxt.lower() in _GENITIVE or (_is_number(nxt) and nxt.lower() not in _NO_NUMERATOR)


def fractions_to_digits(text: str) -> str:
    """Spoken fractions in ITN output as digits with a slash; everything else unchanged."""
    if not text:
        return text
    tokens = text.split(" ")
    out: list[str] = []
    i = 0
    while i < len(tokens):
        mixed = _mixed(tokens, i)
        if mixed is not None:
            written, used = mixed
            out.append(written + _split(tokens[i + used - 1])[1])
            i += used
            continue
        frac = _fraction(tokens, i)
        if frac is not None and not _blocked(tokens, i + frac[1]):
            written, used = frac
            out.append(written + _split(tokens[i + used - 1])[1])
            i += used
            continue
        out.append(tokens[i])
        i += 1
    return " ".join(out)


def _mixed(tokens: list[str], i: int) -> tuple[str, int] | None:
    """``zwei ein halb`` / ``zwei und ein halb`` / ``zwei und drei viertel`` → whole + fraction."""
    word, punct = _split(tokens[i])
    if punct or i + 1 >= len(tokens):
        return None
    whole = _whole(word)
    if whole is None or word.lower() in _NO_NUMERATOR:
        return None
    j = i + 1
    with_und = _split(tokens[j]) == ("und", "")
    if with_und:
        j += 1
    if j >= len(tokens):
        return None
    frac = _fraction(tokens, j)
    if frac is None or " " in frac[0] or _blocked(tokens, j + frac[1]):
        return None
    written, used = frac
    # without "und" only the half joins a whole number (zwei ein halb); "zwei drei viertel" stays two numbers
    if not with_und and written != "1/2":
        return None
    return f"{whole} {written}", j + used - i

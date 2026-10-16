"""Word-level alternative readings for German TN with variants, applied to the readings the variants grammar
gives (the grammar holds the structural ones: the other ways to say a year):

    hundert, tausend          einhundert, eintausend
    zwei Komma fünf           zweieinhalb (eineinhalb, anderthalb)
    null Komma eins fünf      null Komma fünfzehn
    neunzehnhundertneunziger  neunziger
    zweitausendzehn           zweitausendundzehn, zwotausendzehn
"""
from __future__ import annotations

import re

from ..lexicon import DIGITS, TEENS, TIES

_DIGIT = {"null": 0, "eins": 1, **{w: int(d) for w, d in DIGITS if d != "1"}}
_UNITS = {int(d): w for w, d in DIGITS}
_TEEN = {int(d): w for w, d in TEENS}
_TIE = {int(d): w for w, d in TIES}


def _two(n: int) -> str:
    if n < 20:
        return _TEEN[n]
    tens, unit = divmod(n, 10)
    return _TIE[tens] if unit == 0 else _UNITS[unit] + "und" + _TIE[tens]


_END = r"(?=$|[ .,;:!?)](?![a-zäöüß])| [A-ZÄÖÜ]|[.,;:!?)]$)"
_WORDS = "|".join(_DIGIT)
_TWO_DIGITS = re.compile(rf"\bKomma ({_WORDS}) ({_WORDS}){_END}")
_HALF = re.compile(rf"\b(\w+) Komma fünf{_END}")
_CENTURY = re.compile(r"\b(?:" + "|".join(w for w, _ in TEENS) + r")hundert(?=(?:" + "|".join(w for w, _ in TIES) + r")er)")

_BELOW_HUNDRED = "|".join(sorted({_two(n) for n in range(10, 100)} | {w for w, _ in DIGITS} | {"eins"}, key=len, reverse=True))
_THOUSAND_AND = re.compile(rf"\b(\w*tausend)(?=(?:{_BELOW_HUNDRED})\b)")
# (rule, weight): applied one at a time to a reading, the lighter ones first
RULES = [
    (lambda t: re.sub(r"(?<![\wäöüß])hundert", "einhundert", t), 0.5),
    (lambda t: re.sub(r"(?<![\wäöüß])tausend", "eintausend", t), 0.6),
    (lambda t: _TWO_DIGITS.sub(lambda m: "Komma " + _two(10 * _DIGIT[m.group(1)] + _DIGIT[m.group(2)])
                               if _DIGIT[m.group(1)] else m.group(0), t), 0.6),
    (lambda t: _CENTURY.sub("", t), 0.5),
    (lambda t: _HALF.sub(lambda m: ("ein" if m.group(1) == "eins" else m.group(1)) + "einhalb", t), 1.0),
    (lambda t: re.sub(rf"\beins Komma fünf{_END}", "anderthalb", t), 1.2),
    (lambda t: _THOUSAND_AND.sub(r"\1und", t), 0.6),
    (lambda t: re.sub(r"\bzweitausend", "zwotausend", t), 0.7),
]


def expand(readings: list[str], n: int) -> list[str]:
    """The readings, each followed by its word-level alternatives, at most ``n``; readings that differ from an
    earlier one only in punctuation are left out."""
    out: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        key = " ".join(re.findall(r"\w+", t.lower()))
        if key not in seen:
            seen.add(key)
            out.append(t)

    for reading in readings:
        add(reading)
        for rule, _ in RULES:
            changed = rule(reading)
            if changed != reading:
                add(changed)
    return out[:n]

"""Word-level alternative readings of an Italian TN token (variants mode).

Each rule rewrites the default reading of one token, with a cost behind the default (``2016`` → *duemila e
sedici*, ``5-10`` → *dal cinque al dieci*).  The rules work on token readings rather than in a second grammar,
which would be far larger.
"""
from __future__ import annotations

import re
from typing import Callable

from ..lexicon import MONTHS, TEENS, TENS, UNITS, is_number_word

NUMBER_CLASSES = frozenset({"cardinal", "decimal", "range", "money", "measure", "date"})


def _two_digit_words() -> list[str]:
    """10..99 as said (pure Python: variants mode runs without the grammar toolchain)."""
    words = [w for w, _ in TEENS]
    for tens, _ in TENS:
        words.append(tens)
        for unit, _ in UNITS:
            word = (tens[:-1] if unit[0] in "uo" else tens) + unit
            words.append(word[:-3] + "tré" if word.endswith("tre") else word)
    return words


_TWO_DIGIT = "|".join(sorted(_two_digit_words(), key=len, reverse=True))
_MILA = re.compile(r"(mila|mille)(?=[a-zàèéìòù])")
_VENTI = re.compile(rf"^duemila({_TWO_DIGIT})$")
_DATE_DAY = re.compile(r"^(?!primo )(\S+) (" + "|".join(MONTHS) + r")\b")
_ELIDE = re.compile(r"\b(dal|al|il) (?=[aeiouàèéìòù])")
_ELIDED = {"dal": "dall'", "al": "all'", "il": "l'"}
# After these a range is part of a phrase already (del 5-10%, dall'8-11 marzo): its spans would repeat them.
_GOVERNED = {"del", "dal", "al", "il", "nel", "sul", "tra", "fra", "di", "da", "a", "un", "dei", "dai", "ai", "i",
             "l'", "dell'", "dall'", "all'", "nell'", "sull'"}


def _in_number_words(text: str, rewrite: Callable[[str], str]) -> str:
    return " ".join(rewrite(w) if is_number_word(w) else w for w in text.split(" "))


Rule = tuple[frozenset[str], Callable[[str], str], float]

RULES: list[Rule] = [
    (NUMBER_CLASSES, lambda t: _in_number_words(t, lambda w: _MILA.sub(r"\1 e ", w)), 0.4),
    (frozenset({"cardinal", "range", "date"}), lambda t: _in_number_words(t, lambda w: _VENTI.sub(r"venti \1", w)), 1.0),
    (NUMBER_CLASSES, lambda t: _in_number_words(t, lambda w: w.replace("centoottant", "centottant")), 0.5),
    (frozenset({"measure"}), lambda t: re.sub(r"\bpercento\b", "per cento", t), 0.3),
    (frozenset({"decimal", "measure"}), lambda t: re.sub(r"(?<!zero) virgola cinque(?= percento$|$)", " e mezzo", t), 0.8),
    # 2,5 km → due chilometri e mezzo
    (frozenset({"measure"}), lambda t: re.sub(r"^(?!zero )(\S+) virgola cinque ((?!percento$)\S+)$", r"\1 \2 e mezzo", t), 0.8),
    (frozenset({"decimal", "money"}),
     lambda t: re.sub(r" virgola cinque (milioni|miliardi)(?= di |$)", r" \1 e mezzo", t), 0.6),
    (frozenset({"time"}), lambda t: re.sub(r" e trenta$", " e mezza", t), 0.8),
    (frozenset({"time"}), lambda t: re.sub(r" e quindici$", " e un quarto", t), 0.8),
    (frozenset({"date"}), lambda t: _DATE_DAY.sub(r"\1 di \2", t), 0.8),
]


def _spans(text: str) -> list[tuple[str, float]]:
    """``cinque dieci`` → *dal cinque al dieci*, *tra il cinque e il dieci*, with elision."""
    words = text.split(" ")
    tail = " " + words.pop() if words and words[-1] == "percento" else ""
    if len(words) == 3 and words[1] in ("a", "al"):
        del words[1]
    if len(words) != 2 or not all(is_number_word(w) for w in words):
        return []
    a, b = words
    return [(_elide(f"dal {a} al {b}") + tail, 1.0), (_elide(f"tra il {a} e il {b}") + tail, 1.0)]


def _elide(text: str) -> str:
    return _ELIDE.sub(lambda m: _ELIDED[m.group(1)], text)


def alternatives(cls: str, text: str, previous: str = "") -> list[tuple[str, float]]:
    """Other readings of one token with their costs, cheapest first; two rules that both apply are also combined.
    ``previous`` is the word before the token."""
    single = []
    for classes, rewrite, cost in RULES:
        if cls in classes:
            alt = rewrite(text)
            if alt != text:
                single.append((rewrite, alt, cost))
    out = [(alt, cost) for _, alt, cost in single]
    for i, (r1, _, c1) in enumerate(single):
        for r2, _, c2 in single[i + 1:]:
            both = r2(r1(text))
            if both != text and all(both != a for a, _ in out):
                out.append((both, c1 + c2))
    if cls in ("range", "measure") and previous.lower() not in _GOVERNED:
        out += _spans(text)
    return sorted(out, key=lambda t: t[1])

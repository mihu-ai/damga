"""TN with variants: more than one spoken reading per written form.

Each token of the record string gets its default reading plus the alternatives the language lists for it; the
sentence variants are their combinations, default first.
"""
from __future__ import annotations

import itertools
import os
import re
import sys
import warnings
from dataclasses import dataclass, field
from types import FrameType
from typing import Callable, Sequence

from .unicode import tr_lower

_VALUE = r'"((?:[^"\\]|\\.)*)"'
_WORD_TOKEN = re.compile(r'word=' + _VALUE)
_FIELD_SRC = r'[a-z_]+=' + _VALUE.replace("(", "(?:", 1)
_CLASS = re.compile(r'([a-z_]+)\(((?:' + _FIELD_SRC + r'(?: ' + _FIELD_SRC + r')*)?)\)')
_FIELD = re.compile(r'([a-z_]+)=' + _VALUE)


def resolve_variants(variants: bool, deterministic: bool | None) -> bool:
    """``variants``, or its 1.0 name ``deterministic`` (``deterministic=False`` is ``variants=True``), which
    still works with a ``DeprecationWarning``."""
    if deterministic is None:
        return variants
    warnings.warn("deterministic= is deprecated, use variants= instead (deterministic=False is variants=True)",
                  DeprecationWarning, stacklevel=_caller_level())
    return not deterministic


def _caller_level() -> int:
    """The ``stacklevel`` of the first frame outside the damga package, so a warning names the user's line."""
    package = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frame: FrameType | None = sys._getframe(1)
    level = 1
    while frame is not None and os.path.abspath(frame.f_code.co_filename).startswith(package + os.sep):
        frame, level = frame.f_back, level + 1
    return level


def reject_variants(variants: bool, deterministic: bool | None) -> None:
    """ITN has one written form per spoken form: ``variants=True`` raises ``ValueError``."""
    if resolve_variants(variants, deterministic):
        raise ValueError("ITN has no variants: a spoken form has one written form, and guessing between several "
                         "(a phone number, an amount) is what ITN must not do; variants=True exists for TN "
                         "(TextNormalizer)")


@dataclass
class Token:
    """One token of a record string: ``cls`` is the semantic class (``word`` for plain words), ``raw`` the token
    exactly as it appears in the record string, so it can be written on its own."""

    cls: str
    raw: str
    fields: dict[str, str] = field(default_factory=dict)


def parse_record(record: str) -> list[Token] | None:
    """Split a record string into tokens; None when it does not follow the token protocol."""
    tokens, pos = [], 0
    while pos < len(record):
        if record[pos] == " ":
            pos += 1
            continue
        m = _WORD_TOKEN.match(record, pos)
        if m:
            tokens.append(Token("word", m.group(0), {"word": _unescape(m.group(1))}))
        else:
            m = _CLASS.match(record, pos)
            if not m:
                return None
            fields = {k: _unescape(v) for k, v in _FIELD.findall(m.group(2))}
            tokens.append(Token(m.group(1), m.group(0), fields))
        pos = m.end()
    return tokens


def _unescape(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def combine(options: Sequence[Sequence[str]], limit: int) -> list[str]:
    """Sentence variants from per-token options (each list starts with the default reading).

    Ordered by the number of tokens that deviate from their default, then left to right; at most ``limit``."""
    out: list[str] = []
    seen: set[str] = set()
    ambiguous = [i for i, o in enumerate(options) if len(o) > 1]
    for k in range(len(ambiguous) + 1):
        for chosen in itertools.combinations(ambiguous, k):
            for picks in itertools.product(*[range(1, len(options[i])) for i in chosen]):
                idx = dict(zip(chosen, picks))
                text = " ".join(o[idx.get(i, 0)] for i, o in enumerate(options))
                if text not in seen:
                    seen.add(text)
                    out.append(text)
                    if len(out) >= limit:
                        return out
    return out


_WORD = re.compile(r"\w+", re.UNICODE)
_HEARD = re.compile(r"[\w']+", re.UNICODE)


def _words(text: str) -> list[str]:
    return _WORD.findall(tr_lower(text))


def _edit_distance(a: Sequence[str], b: Sequence[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _wildcard_distance(spoken: Sequence[str], heard: Sequence[str | None], is_number: Callable[[str], bool]) -> int:
    """Word edit distance where a ``None`` in ``heard`` (digits written by the recognizer) stands for any run of
    number words, including none, at no cost: only the words around the digits count."""
    inf = len(spoken) + len(heard) + 1
    dp = [[inf] * (len(heard) + 1) for _ in range(len(spoken) + 1)]
    dp[0][0] = 0
    for i in range(len(spoken) + 1):
        for j in range(len(heard) + 1):
            if i == j == 0:
                continue
            best = inf
            h = heard[j - 1] if j else ""
            if j:
                best = dp[i][j - 1] + (0 if h is None else 1)
            if i:
                best = min(best, dp[i - 1][j] + 1)
                if j and h is None and is_number(spoken[i - 1]):
                    best = min(best, dp[i - 1][j], dp[i - 1][j - 1])
                elif j and h is not None:
                    best = min(best, dp[i - 1][j - 1] + (spoken[i - 1] != h))
            dp[i][j] = best
    return dp[-1][-1]


_DIGITS = re.compile(r"\d+")


def _digits(text: str) -> str:
    """All digits of a text in order; a one- or two-digit number loses its leading zero (``05:10`` and ``5-10`` are
    the same clock reading), longer runs keep it (the trunk ``0`` of a phone number is a spoken word)."""
    return "".join(r.lstrip("0") or "0" if len(r) <= 2 else r for r in _DIGITS.findall(text))


def closest(variants: Sequence[str], heard: str, is_number: Callable[[str], bool] = lambda w: False,
            written: Callable[[str], str] | None = None, zero: str | None = None) -> str:
    """The variant a transcript ``heard`` supports best (deterministic; ties keep the earlier variant).

    Sums two signals, case and punctuation ignored: word edit distance, where digits in ``heard`` stand for any
    number words (``is_number``), and, when ``written`` (the language's ITN) is given, edit distance between the
    digits of both written forms.  ``zero`` is the word for 0: a digit run starting with ``0`` stands for that word
    plus a wildcard, so ``is_number`` should not accept it."""
    return rank(variants, heard, is_number, written, zero)[0][0]


def _prepare(heard: str, written: Callable[[str], str] | None, zero: str | None) -> tuple[list[str | None], str]:
    heard_tokens: list[str | None] = []
    for t in _HEARD.findall(tr_lower(heard)):
        if not any(c.isdigit() for c in t):
            heard_tokens.append(t.strip("'"))
            continue
        if zero and t.startswith("0") and len(t) > 1 and t[1].isdigit():
            heard_tokens.append(zero)
        heard_tokens.append(None)
    return heard_tokens, _digits(written(heard)) if written else ""


def rank(variants: Sequence[str], heard: str, is_number: Callable[[str], bool] = lambda w: False,
         written: Callable[[str], str] | None = None, zero: str | None = None) -> list[tuple[str, float]]:
    """Every variant with its distance to ``heard``, closest first (ties in the given order); see ``closest``.

    The distance is the summed signals divided by the number of heard words (a digit run counts as one): 0 is a
    perfect match."""
    if not variants:
        raise ValueError("no variants to choose from")
    heard_tokens, heard_digits = _prepare(heard, written, zero)

    def score(v: str) -> int:
        d = _wildcard_distance(_words(v), heard_tokens, is_number)
        if written:
            d += _edit_distance(_digits(written(v)), heard_digits)
        return d

    size = max(len(heard_tokens), 1)
    scored = [(i, v, score(v)) for i, v in enumerate(variants)]
    scored.sort(key=lambda t: (t[2], t[0]))
    return [(v, d / size) for _, v, d in scored]


def best(variants: Sequence[str], heard: str, is_number: Callable[[str], bool] = lambda w: False,
         written: Callable[[str], str] | None = None, zero: str | None = None) -> tuple[str, float]:
    """``rank(...)[0]`` with fewer calls to ``written``: the value signal is never negative, so a variant whose
    wording alone is worse than the best total cannot win."""
    if not variants:
        raise ValueError("no variants to choose from")
    heard_tokens, heard_digits = _prepare(heard, written, zero)
    wording = sorted((_wildcard_distance(_words(v), heard_tokens, is_number), i) for i, v in enumerate(variants))
    best_score, best_index = None, -1
    for w, i in wording:
        if best_score is not None and w > best_score:
            break
        total = w + (_edit_distance(_digits(written(variants[i])), heard_digits) if written else 0)
        if best_score is None or (total, i) < (best_score, best_index):
            best_score, best_index = total, i
    assert best_score is not None
    return variants[best_index], best_score / max(len(heard_tokens), 1)


def pick_scored(variants: Sequence[str], scores: Sequence[float], margin: float = 0.0) -> str:
    """The highest-scoring variant, but the first (default) one unless another beats it by more than ``margin``."""
    if not variants:
        raise ValueError("no variants to choose from")
    if len(scores) != len(variants):
        raise ValueError(f"{len(scores)} scores for {len(variants)} variants")
    best = max(range(len(variants)), key=lambda i: (scores[i], -i))
    return variants[best] if scores[best] > scores[0] + margin else variants[0]

"""TN with variants for languages whose variants come from a grammar (``build_variants``).

The readings of a sentence are the n best paths of that grammar; the default reading always comes first and is
exactly ``normalize()``.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Sequence

from .variants import best, pick_scored, rank

_DIGIT = re.compile(r"\d")


_WORD = re.compile(r"\w+")


def _said(text: str) -> tuple[str, ...]:
    """What a reading says: its words, without punctuation or case."""
    return tuple(_WORD.findall(text.lower()))


def _zero(lexicon: Any) -> str | None:
    """The language's word for 0; a lexicon may list its case forms (Russian), the first is the base form."""
    zero = getattr(lexicon, "ZERO", None)
    return zero if zero is None or isinstance(zero, str) else next(iter(zero), None)


class Readings:
    """Mixin for a ``TextNormalizer`` with ``engine``, ``variants``, ``lang`` and ``normalize``."""

    engine: Any
    variants: bool
    lang: str
    _itn: Any = None

    def normalize(self, text: str) -> str:  # pragma: no cover - provided by the normalizer
        raise NotImplementedError

    def normalize_variants(self, text: str, n: int = 10) -> list[str]:
        """Spoken readings of ``text``, the default (``normalize(text)``) first, at most ``n``.

        With ``variants=False`` (the default) this is just ``[normalize(text)]``."""
        default = self.normalize(text)
        if not self.variants or n <= 1 or not self.engine.has_variants:
            return [default]
        out = [default]
        said = {_said(default)}
        # A reading that leaves digits the default read out is a word fallback of the grammar, not a reading; one
        # that differs only in punctuation or case says the same.
        default_digits = bool(_DIGIT.search(default))
        for reading in self.engine.readings(text, n * 3):
            if _said(reading) in said or (not default_digits and _DIGIT.search(reading)):
                continue
            said.add(_said(reading))
            out.append(reading)
            if len(out) == n:
                break
        return out

    def _is_number_word(self, word: str) -> bool:
        from ..api import language_lexicon

        lexicon = language_lexicon(self.lang)
        test: Callable[[str], bool] | None = getattr(lexicon, "is_number_word", None)
        if test is not None:
            return test(word)
        zero = _zero(lexicon)
        words = getattr(lexicon, "NUMBER_WORDS", ())
        return word != zero and any(word.startswith(w) for w in words if len(w) > 2 and w != zero)

    def rank_matching(self, text: str, heard: str, n: int = 50) -> list[tuple[str, float]]:
        """Every reading of ``text`` with its distance to ``heard``, closest first; the distance is about errors per
        heard word (0 is a perfect match)."""
        from ..api import InverseNormalizer, language_lexicon

        if self._itn is None:
            self._itn = InverseNormalizer(lang=self.lang, backend=self.engine.backend)
        zero = _zero(language_lexicon(self.lang))
        return rank(self.normalize_variants(text, n=n), heard, is_number=self._is_number_word,
                    written=self._itn.normalize, zero=zero)

    def normalize_matching(self, text: str, heard: str, n: int = 50, max_distance: float | None = None) -> str:
        """The reading of ``text`` closest to ``heard`` (e.g. a recognizer transcript); ties keep the default.
        ``max_distance``: when even the closest reading is further than this, the default is returned."""
        from ..api import InverseNormalizer, language_lexicon

        if self._itn is None:
            self._itn = InverseNormalizer(lang=self.lang, backend=self.engine.backend)
        zero = _zero(language_lexicon(self.lang))
        reading, distance = best(self.normalize_variants(text, n=n), heard, is_number=self._is_number_word,
                                 written=self._itn.normalize, zero=zero)
        if max_distance is not None and distance > max_distance:
            return self.normalize(text)
        return reading

    def normalize_in_context(self, text: str, score: Callable[[Sequence[str]], Sequence[float]], n: int = 10,
                             margin: float = 0.0) -> str:
        """The reading a scorer (e.g. a language model) finds most natural; the default unless another scores more
        than ``margin`` higher."""
        variants = self.normalize_variants(text, n=n)
        if len(variants) == 1:
            return variants[0]
        return pick_scored(variants, list(score(variants)), margin=margin)

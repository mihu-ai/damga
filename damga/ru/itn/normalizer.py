from __future__ import annotations

import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.tokens import NormalizationResult
from ...core.variants import reject_variants
from ..lexicon import CASES, CASING, GNUM, NUMBER_WORDS, ORD_SUFFIX, ORD_UNITS, adjective, is_number_word

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

_YO_WORD = re.compile(r"\b\w*ё\w*\b", re.IGNORECASE)
_NUMBER_SET = set(NUMBER_WORDS)


def _yo(m: re.Match) -> str:
    """трёх → трех, четырёхсот → четырехсот: number words with "ё" are read like those without."""
    word = m.group(0)
    plain = word.replace("ё", "е").replace("Ё", "Е")
    return plain if plain.lower() in _NUMBER_SET or plain.lower().startswith(("четырех", "трех")) else word


def plain_yo(text: str) -> str:
    return _YO_WORD.sub(_yo, text) if "ё" in text or "Ё" in text else text


# Every form of первый..девятый → (value, written ending): восьмого → (8, "го"), третьих → (3, "х").  The grammars
# write ordinals of ten and up with digits already (двадцать первого → 21-го); these are the ones they leave as words.
_ORD_FORMS: dict[str, tuple[int, str]] = {
    adjective(nom, case, gnum): (value, ORD_SUFFIX[gnum][i])
    for value, nom in ORD_UNITS.items() for i, case in enumerate(CASES) for gnum in GNUM}
_WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*|\d+")


def _write_ordinal_digits(text: str) -> str:
    """восьмого → 8-го, первая → 1-я, третьих → 3-х.  A word right after a number (``две третьих``, ``3 пятых``) is
    the denominator of a fraction and stays a word."""
    out: list[str] = []
    pos = 0
    prev: str | None = None
    for m in _WORD.finditer(text):
        word = m.group(0)
        hit = _ORD_FORMS.get(word.lower().replace("ё", "е"))
        if hit is not None and not (prev is not None and (prev[0].isdigit() or is_number_word(prev.lower()))):
            out.append(text[pos:m.start()] + f"{hit[0]}-{hit[1]}")
            pos = m.end()
        prev = word
    return "".join(out) + text[pos:] if out else text


def _reader(cats, custom_vocab, group):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab, group=group).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class InverseNormalizer:
    """Russian inverse text normalization (spoken → written), every case and gender: ``в две тысячи десятом году``
    → в 2010 году.  Zero, one and two stay words.

    ``ordinal_digits=True`` also writes the ordinals below ten with digits and the short ending (наращение), as the
    grammars do from ten up: ``восьмого`` → 8-го, ``первая`` → 1-я, ``третьих`` → 3-х.  Off by default (``второе
    место`` stays words); dates are unaffected (``восьмого марта`` → 8 марта either way)."""

    def __init__(
        self,
        categories: Sequence[str] | None = None,
        strict: bool = False,
        custom_vocab: dict[str, str] | None = None,
        cache_dir: str | pathlib.Path | None = None,
        use_cache: bool = True,
        group_thousands: bool = True,
        preserve_case: bool = True,
        diagnostics: bool = False,
        backend: str = "auto",
        variants: bool = False,
        deterministic: bool | None = None,
        ordinal_digits: bool = False,
    ):
        from .categories import ALL_CATEGORIES

        reject_variants(variants, deterministic)
        cats = resolve_categories(categories, ALL_CATEGORIES)
        if strict:
            cats = tuple(c for c in cats if c not in ("cardinal", "ordinal", "decimal"))
        self.categories = cats
        self.ordinal_digits = ordinal_digits and "ordinal" in cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="itn",
            build_reader=lambda: _reader(cats, self.custom_vocab, group_thousands),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=ru|cats={','.join(sorted(cats))}|group={group_thousands}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=True,
            preserve_case=preserve_case,
            diagnostics=diagnostics,
            pre_hook=plain_yo,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES and group_thousands),
            backend=backend,
            custom_vocab=self.custom_vocab,
            casing=CASING,
        )

    def normalize(self, text: str) -> str:
        return self.normalize_with_details(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        result = self.engine.normalize(text)
        if self.ordinal_digits:
            written = _write_ordinal_digits(result.text)
            if written != result.text:
                result.text = written
                result.changed = True
        return result

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

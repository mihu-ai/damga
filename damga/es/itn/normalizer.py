from __future__ import annotations

import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.tokens import NormalizationResult
from ...core.variants import reject_variants
from ..lexicon import CASING, reattach

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

# Accentless spellings of number words → the accented forms the grammars expect.
_ACCENTS = {"dieciseis": "dieciséis", "veintidos": "veintidós", "veintitres": "veintitrés", "veintiseis": "veintiséis",
            "veintiun": "veintiún", "millon": "millón", "billon": "billón", "decimo": "décimo"}
_ACCENT = re.compile(r"\b(" + "|".join(_ACCENTS) + r")\b")


def restore_accents(text: str) -> str:
    return _ACCENT.sub(lambda m: _ACCENTS[m.group(1)], text)


def _reader(cats, custom_vocab, group):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab, group=group).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class InverseNormalizer:
    """Spanish inverse text normalization (spoken → written): ``veinticinco mil`` → ``25.000``, ``cinco coma cuatro
    por ciento`` → ``5,4 %``.  Lone numbers up to ten stay words."""

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
    ):
        from .categories import ALL_CATEGORIES

        reject_variants(variants, deterministic)
        cats = resolve_categories(categories, ALL_CATEGORIES)
        if strict:
            cats = tuple(c for c in cats if c not in ("cardinal", "ordinal", "decimal"))
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="itn",
            build_reader=lambda: _reader(cats, self.custom_vocab, group_thousands),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=es|cats={','.join(sorted(cats))}|group={group_thousands}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=True,
            preserve_case=preserve_case,
            diagnostics=diagnostics,
            pre_hook=restore_accents,
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
        result.text = reattach(result.text)
        return result

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

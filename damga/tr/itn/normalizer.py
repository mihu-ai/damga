from __future__ import annotations

import pathlib
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.tokens import NormalizationResult
from ...core.variants import reject_variants
from .repair import colloquial_times, repair_spelling

HERE = pathlib.Path(__file__).resolve().parent
CORE = HERE.parent.parent / "core"
LEXICON = HERE.parent / "lexicon.py"

def _reader(cats, custom_vocab):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab).fst


def _writer(cats, **kw):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats, **kw).fst

class InverseNormalizer:

    def __init__(
        self,
        categories: Sequence[str] | None = None,
        strict: bool = False,
        custom_vocab: dict[str, str] | None = None,
        cache_dir: str | pathlib.Path | None = None,
        use_cache: bool = True,
        group_thousands: bool = True,
        group_four_digits: bool = True,
        scale_words: bool = False,
        preserve_case: bool = True,
        diagnostics: bool = False,
        backend: str = "auto",
        repair_spelling: bool = True,
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
        self.repair_spelling = repair_spelling
        cfg = f"cats={','.join(sorted(cats))}|group={group_thousands}|four={group_four_digits}|scale={scale_words}"
        self.engine = Engine(
            mode="itn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats, group_thousands=group_thousands, group_four_digits=group_four_digits,
                                               scale_words=scale_words),
            source_dirs=[HERE, CORE, LEXICON],
            config_key=cfg,
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=True,
            preserve_case=preserve_case,
            diagnostics=diagnostics,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES and group_thousands and group_four_digits and not scale_words),
            backend=backend,
            custom_vocab=self.custom_vocab,
        )

    def normalize(self, text: str) -> str:
        return self.normalize_with_details(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        """``repair_spelling`` restores diacritic-less (``yuz``, ``uc``) and glued (``onbeş``) number words first;
        ``yarım`` naming a time is written 12:30 (``yarımda geleceğim`` → ``12:30'da geleceğim``)."""
        fixed = colloquial_times(repair_spelling(text) if self.repair_spelling else text)
        result = self.engine.normalize(fixed)
        if fixed != text:
            result.original = text
            result.changed = True if result.text != text else result.changed
        return result

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

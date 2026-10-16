from __future__ import annotations

import pathlib
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.tokens import NormalizationResult
from ...core.variants import reject_variants
from ..lexicon import CASING

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

def _reader(cats, custom_vocab, group):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab, group=group).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class InverseNormalizer:
    """French inverse text normalization (spoken → written): ``quinze mille`` → ``15 000``, ``le premier janvier``
    → ``le 1er janvier``.  Zero to ten stay words."""

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
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS, ROOT / "tn" / "readers"],
            config_key=f"lang=fr|cats={','.join(sorted(cats))}|group={group_thousands}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=True,
            preserve_case=preserve_case,
            diagnostics=diagnostics,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES and group_thousands),
            backend=backend,
            custom_vocab=self.custom_vocab,
            casing=CASING,
        )

    def normalize(self, text: str) -> str:
        return self.engine.normalize(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        return self.engine.normalize(text)

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

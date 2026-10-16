from __future__ import annotations

import dataclasses
import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.tokens import NormalizationResult
from ...core.variants import reject_variants
from ..lexicon import CASING, DIGITS, TEENS, TIES
from .units import apply_unit_symbols

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

_HYPHEN = re.compile(r"\b(" + "|".join(w for w, _ in TIES) + r")-(" + "|".join(w for w, _ in DIGITS)
                     + r"|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b")


# Capital letters are kept as acronyms by the grammars, so "A M" after a number is lower-cased here.
_AM_PM = re.compile(r"\b(" + "|".join(w for w, _ in DIGITS + TEENS + TIES) + r"|o'clock) ([AaPp]) ?([Mm])\b")


def join_hyphens(text: str) -> str:
    """``twenty-one`` → ``twenty one``."""
    text = _AM_PM.sub(lambda m: f"{m.group(1)} {m.group(2).lower()} m", text)
    return _HYPHEN.sub(r"\1 \2", text)


def _reader(cats, custom_vocab, group):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab, group=group).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class InverseNormalizer:
    """English inverse text normalization (spoken → written): ``twenty five thousand`` → ``25,000``.

    Lone numbers below ten stay words. ``unit_symbols=True`` writes a number followed by a spelled unit with the
    unit symbol (``two hundred meters`` → ``200 m``); see ``damga/en/itn/units.py``."""

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
        unit_symbols: bool = False,
    ):
        from .categories import ALL_CATEGORIES

        reject_variants(variants, deterministic)
        cats = resolve_categories(categories, ALL_CATEGORIES)
        if strict:
            cats = tuple(c for c in cats if c not in ("cardinal", "ordinal", "decimal"))
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.unit_symbols = unit_symbols
        self.engine = Engine(
            mode="itn",
            build_reader=lambda: _reader(cats, self.custom_vocab, group_thousands),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS, ROOT / "tn" / "readers" / "email_url.py"],
            config_key=f"lang=en|cats={','.join(sorted(cats))}|group={group_thousands}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=True,
            preserve_case=preserve_case,
            diagnostics=diagnostics,
            pre_hook=join_hyphens,
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
        if self.unit_symbols:
            out = apply_unit_symbols(result.text)
            if out != result.text:
                result = dataclasses.replace(result, text=out, changed=True)
        return result

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

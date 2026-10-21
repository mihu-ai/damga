from __future__ import annotations

import importlib
from typing import Any, Iterable

from .core.tokens import NormalizationResult

LANGUAGES: dict[str, str] = {"tr": "damga.tr", "en": "damga.en", "de": "damga.de", "fr": "damga.fr", "es": "damga.es",
                              "it": "damga.it", "ru": "damga.ru"}
DEFAULT_LANG = "tr"


def available_languages() -> list[str]:
    return sorted(LANGUAGES)


def language_module(lang: str, mode: str):
    if lang not in LANGUAGES:
        raise ValueError(f"unsupported language {lang!r}; available: {available_languages()}")
    if mode not in ("itn", "tn"):
        raise ValueError(f"mode must be 'itn' or 'tn', got {mode!r}")
    return importlib.import_module(f"{LANGUAGES[lang]}.{mode}.normalizer")


def language_lexicon(lang: str):
    """Pure-data word lists of a language (no grammar toolchain needed); see damga/tr/lexicon.py."""
    if lang not in LANGUAGES:
        raise ValueError(f"unsupported language {lang!r}; available: {available_languages()}")
    return importlib.import_module(f"{LANGUAGES[lang]}.lexicon")


def InverseNormalizer(*args: Any, lang: str = DEFAULT_LANG, **kwargs: Any):
    return language_module(lang, "itn").InverseNormalizer(*args, **kwargs)


def TextNormalizer(*args: Any, lang: str = DEFAULT_LANG, **kwargs: Any):
    return language_module(lang, "tn").TextNormalizer(*args, **kwargs)


def shell_form(text: str, lang: str = DEFAULT_LANG) -> str:
    """Spoken command line -> shell text (``ls tire lah`` -> ``ls -lah``); run it on ITN output meant for a
    terminal, never on prose.  Turkish only; see damga/tr/shell.py."""
    if lang != "tr":
        raise ValueError(f"shell_form supports 'tr' only, got {lang!r}")
    from .tr.shell import shell_form as tr_shell_form
    return tr_shell_form(text)


class Normalizer:

    def __init__(self, mode: str = "itn", lang: str = DEFAULT_LANG, **kwargs):
        module = language_module(lang, mode)
        cls = module.InverseNormalizer if mode == "itn" else module.TextNormalizer
        self._impl: Any = cls(**kwargs)
        self.mode = mode
        self.lang = lang

    def normalize(self, text: str) -> str:
        return self._impl.normalize(text)

    def normalize_with_details(self, text: str) -> NormalizationResult:
        return self._impl.normalize_with_details(text)

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return self._impl.normalize_batch(texts)

    def normalize_variants(self, text: str, n: int = 10) -> list[str]:
        """TN only: every reading of ``text``, default first (see ``TextNormalizer.normalize_variants``)."""
        if self.mode != "tn":
            return [self.normalize(text)]
        return self._impl.normalize_variants(text, n=n)

    def __call__(self, text: str) -> str:
        return self.normalize(text)

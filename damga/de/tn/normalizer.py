from __future__ import annotations

import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.readings import Readings
from ...core.tokens import NormalizationResult
from ...core.variants import resolve_variants
from ..lexicon import CASING, MONTHS, NOT_YEAR

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

# A year-like number followed by a noun it counts is a cardinal: "1500 Menschen" → tausendfünfhundert.
_YEAR_WORDS = ("Jahr", "Jahre", "Jahres", "Jahren", "im", "seit", "bis", "von", "vor", "nach", "ab", "um", "Anfang",
               "Ende", "Mitte", "Sommer", "Herbst", "Winter", "Frühjahr", "Frühling", "zwischen", "und", "in")
_COUNT = re.compile(r"(\S+ )?\b(1[1-9]\d\d|20[2-9]\d)(?= ([A-ZÄÖÜ][a-zäöüß]+))")
# After a word of quantity ("rund 1800") the number counts, whatever follows.
_QUANTITY = re.compile(r"\b((?:mehr|weniger) als|rund|fast|etwa|circa|ca\.|knapp|nur|allein|insgesamt|mindestens|"
                       r"höchstens|bis zu) (1[1-9]\d\d|20[2-9]\d)\b(?! (?:Jahr|Jahre|Jahren)\b)")
_ISO_DATE = re.compile(r"\b((?:1[5-9]|20)\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
# 2003-03 → März 2003; a range of years runs upwards, so "2010-11" is not a month.
_ISO_MONTH = re.compile(r"\b((?:1[5-9]|20)(\d\d))-(0[1-9]|1[0-2])\b(?![-–]?\d)")


def _mark(m: re.Match) -> str:
    prev, year, nxt = (m.group(1) or ""), m.group(2), m.group(3)
    if prev.strip() in _YEAR_WORDS or nxt in MONTHS:
        return m.group(0)
    return f"{prev}{NOT_YEAR}{year}"


# Letters glued to digits are split for the grammars: "CO2" → "CO 2", "25.Mai" → "25. Mai".
_LETTER_DIGIT = re.compile(r"(?<=[A-Za-zÄÖÜäöüß])[—–-]?(?=\d)")
_DIGIT_LETTER = re.compile(r"(?<=\d)(?=[A-ZÄÖÜ]|[a-z]\b|(?:Millionen|Milliarden|Jahren?|Prozent)\b)")
_DOT_MONTH = re.compile(r"(?<=\d\.)(?=(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|"
                        r"Dezember)\b)")
# IBANs, e-mail and web addresses are read as written, so their letters and digits are not split.
_IBAN = re.compile(r"\b([A-Z]{2}\d{2}(?:(?: [A-Z0-9]{4}){2,7}(?: [A-Z0-9]{1,3})?|[A-Z0-9]{11,30}))\b")
_ADDRESS = re.compile(r"((?:https?://|www\.)[^\s]*[^\s.,;:!?)]|[\w.+-]+@[\w-]+(?:\.[\w-]+)+)")


def _prepare_text(text: str) -> str:
    text = _LETTER_DIGIT.sub(" ", text)
    text = _DIGIT_LETTER.sub(" ", text)
    text = _DOT_MONTH.sub(" ", text)
    text = _QUANTITY.sub(lambda m: f"{m.group(1)} {NOT_YEAR}{m.group(2)}", text)
    return _COUNT.sub(_mark, text).replace(NOT_YEAR + NOT_YEAR, NOT_YEAR)


def prepare(text: str) -> str:
    # an ISO date is read with the month's name
    text = _ISO_DATE.sub(lambda m: f"{int(m.group(3))}. {MONTHS[int(m.group(2)) - 1]} {m.group(1)}", text)
    text = _ISO_MONTH.sub(lambda m: f"{MONTHS[int(m.group(3)) - 1]} {m.group(1)}" if int(m.group(3)) <= int(m.group(2))
                          else m.group(0), text)
    # odd split pieces are IBAN candidates; kept whole when the bank grammar can spell them
    return "".join(p if i % 2 and sum(c.isdigit() for c in p) >= 8 else _prepare_plain(p)
                   for i, p in enumerate(_IBAN.split(text)))


def _prepare_plain(text: str) -> str:
    return "".join(p if i % 2 else _prepare_text(p) for i, p in enumerate(_ADDRESS.split(text)))


def _reader(cats, custom_vocab, variants=False):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, variants=variants, custom_vocab=custom_vocab).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class TextNormalizer(Readings):
    """German text normalization (written → spoken): ``1,50 €`` → *ein Euro fünfzig*.

    ``variants=True`` adds ``normalize_variants`` / ``normalize_matching`` for alternative readings;
    ``normalize()`` is the same in both modes."""

    def __init__(
        self,
        categories: Sequence[str] | None = None,
        custom_vocab: dict[str, str] | None = None,
        cache_dir: str | pathlib.Path | None = None,
        use_cache: bool = True,
        diagnostics: bool = False,
        lowercase: bool = False,
        backend: str = "auto",
        variants: bool = False,
        deterministic: bool | None = None,
    ):
        from .categories import ALL_CATEGORIES

        self.variants = resolve_variants(variants, deterministic)
        self.lang = "de"
        cats = resolve_categories(categories, ALL_CATEGORIES)
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="tn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=de|cats={','.join(sorted(cats))}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=lowercase,
            diagnostics=diagnostics,
            pre_hook=prepare,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES),
            backend=backend,
            custom_vocab=self.custom_vocab,
            casing=CASING,
            build_variants=lambda: _reader(cats, self.custom_vocab, variants=True),
        )

    def normalize(self, text: str) -> str:
        return self.engine.normalize(text).text

    def normalize_variants(self, text: str, n: int = 10) -> list[str]:
        """Spoken readings of ``text``, the default first, each with its word-level alternatives."""
        readings = super().normalize_variants(text, n=n)
        if not self.variants or n <= 1:
            return readings
        from .variants import expand
        return expand(readings, n)

    def normalize_with_details(self, text: str) -> NormalizationResult:
        return self.engine.normalize(text)

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

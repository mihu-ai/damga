from __future__ import annotations

import pathlib
import re
from typing import Any, Callable, Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.tokens import NormalizationResult
from ...core.variants import best, combine, parse_record, pick_scored, rank, resolve_variants

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"

# ``N.`` after a minus sign or ``0.`` is no ordinal the grammars read (``-3. kat``, ``0. kuvveti``): left unmarked.
_ORDINAL_MARK = re.compile(r"(?<![\w.,−])(?<!(?<![^\s(])-)(?!0\.)(\d+)\.(?= [a-zçğıöşü])")
# Before a capitalised word ``N.`` usually ends a sentence, so only these names make it an ordinal
# (``1. Dünya Savaşı``); other capitalised followers are a variant (``capital_ordinals``).
ORDINAL_NAMES = (
    "Dünya", "Haçlı", "Ordu", "Kolordu", "Tümen", "Lig", "Dönem", "Yasama", "Abdülhamit", "Abdülhamid",
    "Kılıç", "Alaaddin", "Keyhüsrev", "Keykubat", "Gıyaseddin", "Gıyasettin",
    "Wilhelm", "Louis", "Napolyon", "Elizabeth", "Henry", "Charles", "George", "Frederick", "Petro", "Katerina",
    "Nikola", "Ramses", "Viyana", "Meşrutiyet", "Balkan", "Kuşak", "Körfez",
)
_ORDINAL_NAME_MARK = re.compile(r"(?<![\w.,−])(?<!(?<![^\s(])-)(?!0\.)(\d+)\.(?= (?:" + "|".join(ORDINAL_NAMES) + r")(?![a-zçğıöşü]))")
# Common given names are ordinals only up to the last sultan of that name (``7. Mustafa`` is not).
SULTANS = {"Mehmet": 6, "Mehmed": 6, "Murat": 5, "Murad": 5, "Mustafa": 4, "Ahmet": 3, "Ahmed": 3, "Selim": 3,
           "Osman": 3, "Mahmut": 2, "Mahmud": 2, "Süleyman": 2, "Beyazıt": 2, "Bayezid": 2}
_SULTAN_MARK = re.compile(r"(?<![\w.,−])(?<!(?<![^\s(])-)([1-9])\.(?= (" + "|".join(SULTANS) + r")(?![a-zçğıöşü]))")


def _mark_sultans(text: str) -> str:
    return _SULTAN_MARK.sub(lambda m: m.group(1) + ("º" if int(m.group(1)) <= SULTANS[m.group(2)] else "."), text)


_ORDINAL_CAPITAL = re.compile(r"(?<![\w.,−])(?<!(?<![^\s(])-)(?!0\.)(\d+)\.(?= [A-ZÇĞİÖŞÜ])")
# ``6.sınıf`` (no space) and the first half of an ordinal range ``7.-8. sınıf``.
_ORDINAL_GLUED = re.compile(r"(?<![\w.,−])(?<!(?<![^\s(])-)(?!0\.)(\d+)\.(?=[a-zçğıöşü]{2,})")
_ORDINAL_RANGE = re.compile(r"(?<![\w.,−])(?<!(?<![^\s(])-)(?!0\.)(\d+)\.(?=-\d+\.(?: [a-zçğıöşü]|$))")
# A free-standing ``-`` is a minus only next to a one-letter variable (``x - 1``); between two plain numbers it is a
# range (``10 - 15``); elsewhere it stays a dash.  ``o`` is a Turkish word, not a variable.
_NUMBER = re.compile(r"^\(?[-+−]?\d[\d.,]*(?:'\w+)?\)?[.,;:]?$")
_RANGE_END = re.compile(r"^\d+$")
_RANGE_START = re.compile(r"^\d+(?:'\w+)?[.,;:]?$")  # whole numbers only: ``09.00 - 17.00`` is left as it is
_VARIABLE = re.compile(r"^\(?(?!o\b)(?:[a-zA-Z]|\d*[a-zA-Z]\d*)(?:'\w+)?\)?[.,;:]?$")


def _mark_minus(text: str) -> str:
    if " - " not in text:
        return text
    toks = text.split(" ")
    out: list[str] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        if tok == "-" and out and i + 1 < len(toks):
            prev, nxt = out[-1], toks[i + 1]
            if (_VARIABLE.match(prev) and (_NUMBER.match(nxt) or _VARIABLE.match(nxt))) or (
                _VARIABLE.match(nxt) and _NUMBER.match(prev)
            ):
                out.append("−")
                i += 1
                continue
            chain = (len(out) > 1 and out[-2] == "-") or (i + 2 < len(toks) and toks[i + 2] == "-")
            if _RANGE_END.match(prev) and _RANGE_START.match(nxt) and not chain:  # ``0532 - 123 - 45``: not a range
                out[-1] = f"{prev}-{nxt}"
                i += 2
                continue
        out.append(tok)
        i += 1
    return " ".join(out)


# ``3.50 TL``: a point with exactly two digits before a currency is the kuruş/cent separator, as ``3,50 TL``.
_POINT_MONEY = re.compile(r"(?<![\d.,])(\d+)\.(\d\d)(?= ?(?:TL|₺|\$|€|£|USD|EUR|GBP|lira|dolar|euro|avro|sterlin)(?![a-zçğıöşü]))")
# ``5-li``, ``3-lük``, ``2-nci``: a suffix written after a dash instead of an apostrophe.
_DASH_SUFFIX = re.compile(r"(?<=\d)-(?=(?:l[ıiuü]k?|l[ae]r|[ıiuü]?nc[ıiuü])(?![a-zçğıöşü]))")


def mark_ordinals(text: str) -> str:
    """The TN pre-hook: mark ordinal points as ``º`` and minus signs as ``−`` for the grammars."""
    text = _DASH_SUFFIX.sub("'", _POINT_MONEY.sub(r"\1,\2", text))
    text = _ORDINAL_RANGE.sub(r"\1º", text)
    text = _ORDINAL_GLUED.sub(r"\1º ", text)
    text = _ORDINAL_NAME_MARK.sub(r"\1º", text)
    text = _mark_sultans(text)
    return _mark_minus(_ORDINAL_MARK.sub(r"\1º", text))


def capital_ordinals(text: str) -> str:
    """Every ``N.`` before a capitalised word read as an ordinal: the alternative reading with variants."""
    return _ORDINAL_CAPITAL.sub(r"\1º", text)

def _reader(cats, custom_vocab):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab).fst


def _writer(cats, **kw):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats, **kw).fst

class TextNormalizer:

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
        self._say_cache: dict[str, str] = {}
        self._itn: Any = None

        cats = resolve_categories(categories, ALL_CATEGORIES)
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        cfg = f"cats={','.join(sorted(cats))}"
        self.engine = Engine(
            mode="tn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT / "itn", ROOT.parent / "core", LEXICON],
            config_key=cfg,
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=lowercase,
            diagnostics=diagnostics,
            pre_hook=mark_ordinals,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES),
            backend=backend,
            custom_vocab=self.custom_vocab,
        )

    def normalize(self, text: str) -> str:
        return self.engine.normalize(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        return self.engine.normalize(text)

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

    def normalize_variants(self, text: str, n: int = 10) -> list[str]:
        """Spoken readings of ``text``, the default (``normalize(text)``) first, at most ``n``.

        With ``variants=False`` (the default) this is just ``[normalize(text)]``; otherwise tokens add their
        alternative readings (``09:30`` → ``dokuz otuz``, ``dokuz buçuk``)."""
        default = self.normalize(text)
        if not self.variants or n <= 1:
            return [default]
        from .variants import alternatives

        engine = self.engine
        clean = engine.prepare(text)
        out = [default]
        cleans = [clean]
        alt = capital_ordinals(clean)
        if alt != clean:
            cleans.append(alt)
        for c in cleans:
            record = engine.read(c) if c else None
            tokens = parse_record(record) if record else None
            if not tokens:
                continue
            options = []
            for tok in tokens:
                first = engine.write_record(tok.raw)
                if first is None:
                    break
                options.append([first, *alternatives(tok, first, self._say)])
            else:
                for v in combine(options, n * 2):
                    v = engine.finish(text, c, v)
                    if "º" in v or "−" in v:  # a mark the grammars did not consume: not a reading
                        continue
                    if v not in out:
                        out.append(v)
        return out[:n]

    def normalize_matching(self, text: str, heard: str, n: int = 50, max_distance: float | None = None) -> str:
        """The reading of ``text`` closest to ``heard``, e.g. a recognizer transcript:
        ``("Saat 09:30", "saat dokuz buçuk")`` → ``Saat dokuz buçuk``.  Needs ``variants=True``; ties keep the
        default (see ``damga.core.variants.closest``).

        ``max_distance``: when even the closest reading is further from ``heard`` than this (the ``rank_matching``
        distance), the default is returned.  ``None`` (the default) always takes the closest reading."""
        from ..lexicon import ZERO
        from .variants import is_number_word

        if self._itn is None:
            from ..itn.normalizer import InverseNormalizer

            self._itn = InverseNormalizer(backend=self.engine.backend, use_cache=True)
        reading, distance = best(self.normalize_variants(text, n=n), heard, is_number=is_number_word,
                                 written=self._itn.normalize, zero=ZERO)
        if max_distance is not None and distance > max_distance:
            return self.normalize_variants(text, n=1)[0]
        return reading

    def rank_matching(self, text: str, heard: str, n: int = 50) -> list[tuple[str, float]]:
        """Every reading of ``text`` with its distance to ``heard`` (about errors per heard word), closest first."""
        from ..lexicon import ZERO
        from .variants import is_number_word

        if self._itn is None:
            from ..itn.normalizer import InverseNormalizer

            self._itn = InverseNormalizer(backend=self.engine.backend, use_cache=True)
        return rank(self.normalize_variants(text, n=n), heard, is_number=is_number_word,
                    written=self._itn.normalize, zero=ZERO)

    def normalize_in_context(self, text: str, score: Callable[[Sequence[str]], Sequence[float]], n: int = 10,
                             margin: float = 0.0) -> str:
        """The reading of ``text`` a scorer (e.g. a language model) finds most natural.

        ``score`` gets the readings (default first) and returns one number per reading, higher is better.  The default
        is kept unless another scores more than ``margin`` higher.  Needs ``variants=True``."""
        variants = self.normalize_variants(text, n=n)
        if len(variants) == 1:
            return variants[0]
        return pick_scored(variants, list(score(variants)), margin=margin)

    def _say(self, digits: str) -> str:
        if digits not in self._say_cache:
            spoken = self.engine.write_record(f'cardinal(integer="{digits}")')
            self._say_cache[digits] = spoken if spoken is not None else digits
        return self._say_cache[digits]

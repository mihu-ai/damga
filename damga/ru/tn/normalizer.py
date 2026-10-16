from __future__ import annotations

import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.readings import Readings
from ...core.tokens import NormalizationResult
from ...core.variants import resolve_variants
from ..lexicon import CASE_MARKS, CASING, GENDER_MARKS, MONTHS_GEN, PREPOSITIONS, RANGE_DASH, RANGE_TO

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

_PREP_CASE = {p: case for case, words in PREPOSITIONS.items() for p in words}
_PREP_CASE["в"] = _PREP_CASE["во"] = "v"
_PREP_CASE["ок."] = "gen"                                    # ок. 1475 г. → около … пятого года
_NUMBER = re.compile(r"(?<![\w.,—–⁣-])([−-]?)([$€£₽]?)(\d{1,3}(?: \d{3})+(?![\d,.]\d)|\d+)")
_PREV = re.compile(r"(\S+)\s+$")
_NEXT = re.compile(r"\s+([а-яё]{2,})(?![\w-])")
_ISO = re.compile(r"\b((?:1[5-9]|20)\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
_SPACED_RANGE = re.compile(r"(?<![\d,.])(\d[\d,]*)(?: ?[—–] ?| -(?=\d)|- (?=\d))(?=\d)")
_HEADING = re.compile(r"\s+(?:" + "|".join(MONTHS_GEN) + r")(?: \d{4}(?: года| г\.)?)? [—–-] ")
# The ending of the noun after a number shows an oblique case the preposition leaves open: в 20 километрах.
_NOUN_CASE = (("ами", "ins"), ("ями", "ins"), ("ьми", "ins"), ("ах", "prep"), ("ях", "prep"), ("ам", "dat"), ("ям", "dat"))
_FROM_RANGE = re.compile(r"\b([Оо]т (?:[$€£₽])?\d[\d,]*(?: \d{3})*) ?[—–-] ?(?=[$€£₽]?\d)")
# Words that follow a number but are not the counted noun, so they say nothing about its gender.
_NOT_NOUNS = {"года", "году", "год", "годы", "тыс", "млн", "млрд", "трлн", "раза", "и", "или", "по", "до", "из", "на",
              "км", "кг", "мм", "см", "га", "мл", "мин", "сек", "руб", "коп", "долл", "евро", "чел", "экз", "стр"}


# Verbs whose object is the number, in the accusative: составляет тысячу двести человек.
_ACC_VERB = re.compile(r"^(?:составля|составит|составил|насчитыва|насчитал|достига|достиг|превыша|превысил|превысит)"
                       r"\w*(?<!сь)(?<!ся)$")
# The second word of a two-word preposition that governs the genitive: в течение пяти лет, в возрасте двадцати лет.
_GEN_AFTER = {"течение", "возрасте", "размере", "количестве", "пределах", "протяжении", "объеме", "объёме",
              "ходе", "результате", "отличие"}
_DIST = re.compile(r"(?:км|м|километр\w*|метр\w*|верст\w*|миль\w*)\.? +(?:к|от|на|юго|северо|севернее|южнее|западнее|"
                   r"восточнее|выше|ниже|вверх|вниз)\b")
# 1997 -98 годах: the second year with its last two digits, expanded only where the span is read as years
_SHORT_SPAN = re.compile(r"(?<![\d,.])(1\d|20)(\d\d) ?([—–-]) ?(\d\d)(?![\d,.]?\d)(?= ?(?:годах|годов|годы|годам|гг\.?))")
_DASH_DATE = re.compile(r"\b(0?[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-((?:1[5-9]|20)\d\d)\b"
                        r"|\b(0?[1-9]|[12]\d|3[01])/(0?[1-9]|1[0-2])/((?:1[5-9]|20)\d\d)\b"     # 2/3/1906
                        r"|(?<![\d.,-])(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-(\d\d)(?![\d-])")  # 01-01-86
# 03-фев-2002: the month abbreviated between dashes
_MONTH_ABBR = {"янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "мая": 5, "июн": 6, "июл": 7, "авг": 8, "сен": 9,
               "сент": 9, "окт": 10, "ноя": 11, "дек": 12}
_ABBR_DATE = re.compile(r"\b(0?[1-9]|[12]\d|3[01])-(" + "|".join(_MONTH_ABBR) + r")-((?:1[5-9]|20)\d\d)\b",
                        re.IGNORECASE)


def _dash_date(m: re.Match) -> str:
    day, month, year = [g for g in m.groups() if g is not None]
    return f"{day}.{month}.{year}"
# 25-ти, 5-и, 4-х (the case ending written after the digits): the ending says the number is oblique; "-х" after a
# number above four is an ordinal (1990-х, 5-х классов).
_CASE_SUFFIX = re.compile(r"(?<![\w.,])(\d+)-(?:ти|и)(?![\w-])|(?<![\w.,])([234])-х(?![\w-])")
# Орден 3 степени → третьей степени: an ordinal, genitive feminine
_DEGREE = re.compile(r"(?<![\w.,\ue100-\ue1ff-])([1-4]) степени(?!\w)")


def _short_span(m: re.Match) -> str:
    """1997—98 → 1997—1998: the second year written with its last two digits only."""
    century, first, dash, second = m.groups()
    return f"{century}{first}{RANGE_DASH}{century}{second}" if int(second) > int(first) else m.group(0)


_MASCULINE_A = {"мужчина", "мужчины", "папа", "дедушка", "юноша", "дядя", "судья", "коллега", "слуга", "староста"}


def _gender(number: str, following: str) -> str:
    """The gender of the noun after a number ending in 1 or 2 (not 11, 12), from the noun's ending: 21 тонна,
    1 окно, 2 тонны (genitive singular -ы/-и is feminine; masculine and neuter take -а/-я)."""
    if following in _NOT_NOUNS:
        return ""
    last, last2 = number[-1], number[-2:]
    if last == "1" and last2 != "11":
        if following.endswith(("а", "я")) and following not in _MASCULINE_A:
            return GENDER_MARKS["f"]
        if following.endswith(("о", "е")) and len(following) > 2:
            return GENDER_MARKS["n"]
    if last == "2" and last2 != "12" and following.endswith(("ы", "и")):
        return GENDER_MARKS["f"]
    return ""


def mark_context(text: str) -> str:
    """Put a case mark before a number a preposition governs and a gender mark before a number whose noun is
    feminine or neuter; the grammars read the marks, a mark nothing reads makes the engine retry without them."""
    text = _ISO.sub(r"\3.\2.\1", text)
    text = _DASH_DATE.sub(_dash_date, text)
    text = _ABBR_DATE.sub(lambda m: f"{m.group(1)}.{_MONTH_ABBR[m.group(2).lower()]:02d}.{m.group(3)}", text)
    text = _SHORT_SPAN.sub(_short_span, text)
    text = _FROM_RANGE.sub(r"\1 " + RANGE_TO + " ", text)
    text = _SPACED_RANGE.sub(r"\1" + RANGE_DASH, text)
    text = _DEGREE.sub(CASE_MARKS["gen"] + r"\1-й степени", text)
    # в 25-ти томах → двадцати пяти: genitive, which dative and prepositional read the same
    text = _CASE_SUFFIX.sub(lambda m: CASE_MARKS["gen"] + (m.group(1) or m.group(2)), text)
    out, pos = [], 0
    last_case, last_end = "", -1
    for m in _NUMBER.finditer(text):
        sign, currency, digits = m.groups()
        prev = _PREV.search(text[:m.start()])
        word = prev.group(1).lower().strip("(«\"") if prev else ""
        case = "gen" if word == RANGE_TO else _PREP_CASE.get(word, "")
        if not case and last_case and re.fullmatch(r" (?:или|и) ", text[last_end:m.start()]):
            case = last_case                                 # в возрасте 18 или 19 лет: both in the genitive
        if not case and _ACC_VERB.match(word) and not _MONTH_NEXT.match(text[m.end():]):
            case = "acc"                                     # составляет тысячу …, but достигнуто 24 января
        if word in _GEN_AFTER:
            case = "gen"                                     # в течение пяти лет
        rest = text[m.end():]
        nxt = _NEXT.match(rest)
        if nxt and not currency and nxt.group(1) not in _NOT_NOUNS and (case in ("", "v", "acc") or word in ("с", "со")):
            for ending, noun_case in _NOUN_CASE:
                if nxt.group(1).endswith(ending) and len(nxt.group(1)) > len(ending) + 2:
                    if word in ("с", "со") and noun_case != "ins":
                        break
                    case = noun_case
                    break
        if (word in ("в", "во") and _DIST.match(re.sub(r"^[,.]\d+", "", rest).lstrip())
                and not text[:m.start()].rstrip()[:-1].rstrip().endswith("расстоянии")):
            case = "prep"                                    # в 26,5 км к юго-востоку: a distance, prepositional
        if not case and _HEADING.match(rest) and not text[:m.start()].strip():
            case = "nom"                                     # "8 марта — …" opening a line: a date as a heading
        mark = CASE_MARKS[case] if case else ""
        if not currency and not re.match(r"[,.]\d|-", rest):
            if nxt:
                mark += _gender(digits.replace(" ", ""), nxt.group(1))
        out.append(text[pos:m.start()] + sign + mark + currency + digits)
        pos = m.end()
        last_case, last_end = case, m.end()
    out.append(text[pos:])
    return "".join(out)


_MONTH_NEXT = re.compile(r"\s+(?:" + "|".join(MONTHS_GEN) + r")\b")
# The private-use characters the pre-hook uses as marks; written by a user they would read as marks, so they go.
_USER_MARKS = re.compile(r"[\ue100-\ue1ff]")
_LEAKED = re.compile(r"\S*[\ue100-\ue1ff]\S*")
_UNMARK = {**{ord(c): None for c in (*CASE_MARKS.values(), *GENDER_MARKS.values())}, ord(RANGE_DASH): " — ",
           ord(RANGE_TO): "до"}


def _reader(cats, custom_vocab, variants=False):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, variants=variants, custom_vocab=custom_vocab).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class TextNormalizer(Readings):
    """Russian text normalization (written → spoken), with case and gender agreement: ``в 1961 году`` → *в тысяча
    девятьсот шестьдесят первом году*, ``21 тонна`` → *двадцать одна тонна*.

    ``variants=True`` adds ``normalize_variants`` / ``normalize_matching`` (``damga.core.readings``): other
    cases a number can take, *полтора* / *два с половиной*, ё spellings, acronyms spelled out; ``normalize()`` is the
    same in both modes."""

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
        self.lang = "ru"
        cats = resolve_categories(categories, ALL_CATEGORIES)
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="tn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=ru|cats={','.join(sorted(cats))}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=lowercase,
            diagnostics=diagnostics,
            pre_hook=mark_context,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES),
            backend=backend,
            custom_vocab=self.custom_vocab,
            casing=CASING,
            build_variants=lambda: _reader(cats, self.custom_vocab, variants=True),
        )

    def normalize(self, text: str) -> str:
        return self.normalize_with_details(text).text

    def normalize_variants(self, text: str, n: int = 10) -> list[str]:
        return super().normalize_variants(_USER_MARKS.sub("", text), n=n)

    def rank_matching(self, text: str, heard: str, n: int = 50) -> list[tuple[str, float]]:
        """As ``Readings.rank_matching``, with *ноль* as the word for a leading 0 (Russian keeps all case forms of
        it in ``ZERO``)."""
        from ...core.variants import rank
        from ..itn.normalizer import InverseNormalizer
        from ..lexicon import ZERO, is_number_word

        if self._itn is None:
            self._itn = InverseNormalizer(backend=self.engine.backend)
        return rank(self.normalize_variants(text, n=n), heard, is_number=is_number_word, written=self._itn.normalize,
                    zero=ZERO[0])

    def normalize_with_details(self, text: str) -> NormalizationResult:
        """A mark the grammars leave unread (a number written in a form no grammar knows, ``14,0``, ``1880е``) is
        taken off that number only, and the sentence is read again: the other numbers keep their case."""
        engine = self.engine
        text = _USER_MARKS.sub("", text)
        clean = engine.prepare(text)
        for _ in range(4):
            record = engine.read(clean) if clean else None
            spoken = engine.write_record(record) if record is not None else None
            if spoken is None:
                break
            leaked = _LEAKED.findall(spoken)
            if not leaked:
                out = engine.finish(text, clean, spoken)
                return NormalizationResult(text=out, original=text, record=record if engine.diagnostics else None,
                                           changed=out != text)
            for piece in leaked:
                clean = clean.replace(piece, piece.translate(_UNMARK))
        return engine.normalize(text)

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

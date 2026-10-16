from __future__ import annotations

import itertools
import pathlib
import re
from typing import Callable, Iterable, Sequence, Union

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.readings import Readings
from ...core.tokens import NormalizationResult
from ...core.variants import resolve_variants
from ..lexicon import BEFORE_NOUN, CASING, FEMININE, ORDINAL_TENS, ORDINAL_UNITS, ORDINALS, reattach
from .units import AFTER_ONLY, CURRENCY_SYMBOLS, load_units

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

# Words after a number that are no noun: "el 1 de enero" stays *uno*, "21 y 22" *veintiuno y veintidós*.
FUNCTION_WORDS = set("""de del a al y e o u en por para con sin que como entre sobre hasta desde contra según durante
mediante tras ante bajo ni pero sino más menos ya se lo la las los el un una es son fue ha han había hay este esta""".split())
# Masculine nouns in -a and feminine nouns that the endings below would get wrong.
MASCULINE_IN_A = set("""día días problema problemas programa programas sistema sistemas tema temas mapa mapas clima
idioma idiomas planeta planetas poema poemas dilema dilemas esquema esquemas lema lemas diploma diplomas""".split())
FEMININE_WORDS = set("""mujer mujeres vez veces parte partes ley leyes red redes fase fases clase clases
mano manos imagen imágenes muerte muertes noche noches tarde tardes sede sedes""".split())
_FEMININE_END = re.compile(r"(?:a|as|ión|iones|dad|dades|tad|tades|tud|tudes|umbre|umbres|sis)$")
UNITS = {written for written, *_ in load_units()} | set(CURRENCY_SYMBOLS)

_NUMBER_WORD = re.compile(r"(?<![\w.,:\u2062\u2064])(\d{1,3}(?:[.  ]\d{3})+|\d+)(?=(?:,\d+)? ([^\W\d_]+))")
# Clock times written with a point: "a las 11.45", "11.45 horas"
_DOT_TIME = re.compile(r"\b((?:[Aa] |[Dd]e |[Hh]asta )?las )([01]?\d|2[0-3])\.([0-5]\d)\b(?![.,]\d)")
_DOT_TIME_HOURS = re.compile(r"\b([01]?\d|2[0-3])\.([0-5]\d)(?= ?(?:horas\b|h\b|[ap]\.? ?m\b))")
# "en 2020—que": a dash glued between a number and a word is a pause; the number is read on its own.
_CODE_DASH = re.compile(r"(?<=[A-Z])[—–](?=\d)")          # COVID—19 is COVID-19
_GLUED_DASH = re.compile(r"(\d)([—–])(?=[^\W\d_])")
# A bare "9.00" or "15.30" is a clock time too (Spanish writes decimals with a comma); other minutes stay decimals.
_DOT_TIME_BARE = re.compile(r"(?<![\d.,])([01]?\d|2[0-3])\.(00|15|30|45)(?!\d)(?![.,]\d)(?! ?%)")


def _gender(word: str) -> str:
    w = word.lower()
    if word in UNITS or w in FUNCTION_WORDS or (word.isupper() and len(word) > 1):
        return ""
    if w in MASCULINE_IN_A:
        return BEFORE_NOUN
    if w in FEMININE_WORDS or _FEMININE_END.search(w):
        return FEMININE
    return BEFORE_NOUN


_MONTHS = "(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
_DAY = r"(0?[1-9]|[12]\d|3[01])"
# "5 febrero 2020" / "30 julio del 2020": the "de" a date is said with ("cinco de febrero de dos mil veinte")
_DAY_MONTH = re.compile(r"(?<![\d.,:/])\b" + _DAY + r" (" + _MONTHS + r")\b(?:,? (de |del )?(\d{4})\b)?", re.IGNORECASE)
# Month first ("abril 30") only before a year or at the end of a phrase, so "en abril 30 personas" keeps its number
_MONTH_DAY = re.compile(r"(?<!\bde )\b(" + _MONTHS + r") " + _DAY + r"\b(?:,? (\d{4})\b|(?=\s*(?:[.,;:!?)](?!\d)|$)))",
                        re.IGNORECASE)
# "el siglo XIX" → "el siglo 19" (read as a cardinal: "siglo diecinueve")
_CENTURY = re.compile(r"\b([Ss]iglos?) ([IVXLC]+|[ivxlc]+)\b")
# A currency written before its amount is moved after it ("€5" → "5 €"), where the money grammar reads it
_AMOUNT = r"(\d{1,3}(?:[.  ]\d{3})+(?:,\d+)?|\d+(?:,\d+)?)((?: (?:mil millones|millones|millón|billones))?)"
_CURRENCY_FIRST = re.compile(r"(?<![\w$€£¥₩₧₹₽₡₲/])(" + "|".join(re.escape(s) for s in CURRENCY_SYMBOLS if s not in AFTER_ONLY) + r") ?"
                             + _AMOUNT + r"(?![\d.,]?\d)")
# ISO 8601 "2008-02-17" → "17/02/2008", which the date grammar reads
_ISO_DATE = re.compile(r"(?<![\d.,/-])\b([12]\d{3})-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])\b(?![-/.]?\d)")
_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def _roman(numeral: str) -> int:
    values = [_ROMAN[c] for c in numeral.lower()]
    return sum(-v if i + 1 < len(values) and v < values[i + 1] else v for i, v in enumerate(values))


def _day_month(m: re.Match[str]) -> str:
    year = f" {m.group(3) or 'de '}{m.group(4)}" if m.group(4) else ""
    return f"{m.group(1)} de {m.group(2)}{year}"


def _month_day(m: re.Match[str]) -> str:
    return f"{m.group(2)} de {m.group(1)}" + (f" de {m.group(3)}" if m.group(3) else "")


def mark(text: str) -> str:
    """Prepare written Spanish for the grammars: clock times with a point, the "de" of a date, a century in Roman
    numerals, and the gender of a number from the word after it (``21 personas`` → *veintiuna*)."""
    text = _CODE_DASH.sub("-", text)
    text = _GLUED_DASH.sub(r"\1 \2 ", text)
    text = _DOT_TIME.sub(r"\1\2:\3", text)
    text = _DOT_TIME_HOURS.sub(r"\1:\2", text)
    text = _DOT_TIME_BARE.sub(r"\1:\2", text)
    text = _CURRENCY_FIRST.sub(r"\2\3 \1", text)
    text = _ISO_DATE.sub(r"\3/\2/\1", text)
    text = _DAY_MONTH.sub(_day_month, text)
    text = _MONTH_DAY.sub(_month_day, text)
    text = _CENTURY.sub(lambda m: f"{m.group(1)} {_roman(m.group(2))}" if _roman(m.group(2)) <= 30 else m.group(0), text)
    return _NUMBER_WORD.sub(lambda m: ("" if _is_year(text, m) else _gender(m.group(2))) + m.group(1), text)


_YEAR_BEFORE = re.compile(r"(?:\b(?:en|desde|de|del|hasta|entre|y|a|para|antes|después|año|años|el)\s+)$", re.IGNORECASE)
_CENTURY_BEFORE = re.compile(r"\bsiglos?\s+$", re.IGNORECASE)


def _is_year(text: str, m: re.Match[str]) -> bool:
    """A four-digit number after a preposition is a year and has no gender (``desde 1999 numerosas sanciones``)."""
    digits = m.group(1)
    if _CENTURY_BEFORE.search(text[:m.start()]):        # "el siglo 21 europeo": no "veintiún"
        return True
    return (len(digits) == 4 and digits.isdigit() and 1100 <= int(digits) <= 2099
            and bool(_YEAR_BEFORE.search(text[:m.start()])))


def _span_alternatives(reading: str, limit: int) -> list[str]:
    """``reading`` with the sentence alternatives applied span by span, so two years in one sentence vary
    independently; fewest changes first."""
    spans: dict[tuple[int, int], list[str]] = {}
    for pattern, repl in SENTENCE_ALTERNATIVES:
        for m in pattern.finditer(reading):
            alt = m.expand(repl) if isinstance(repl, str) else repl(m)
            spans.setdefault((m.start(), m.end()), []).append(alt)
    pieces: list[list[str]] = []
    pos = 0
    for (start, end), alts in sorted(spans.items()):
        if start < pos:                      # overlaps a span already taken
            continue
        pieces += [[reading[pos:start]], [reading[start:end], *dict.fromkeys(alts)]]
        pos = end
    pieces.append([reading[pos:]])
    varying = [i for i, p in enumerate(pieces) if len(p) > 1]
    out: list[str] = []
    for k in range(1, len(varying) + 1):
        for chosen in itertools.combinations(varying, k):
            for picks in itertools.product(*[range(1, len(pieces[i])) for i in chosen]):
                pick = dict(zip(chosen, picks))
                out.append("".join(p[pick.get(i, 0)] for i, p in enumerate(pieces)))
                if len(out) >= limit:
                    return out
    return out


# formal_ordinals: a written ordinal from 11 to 100 is read as the ordinal word ("80.º" → "octogésimo").
_FORMAL_ORDINAL = re.compile(r"(?<![\w.,:/\u2062\u2064])(\d{2,3})\.?(º|ᵒ|ª|ᵃ|ᵉʳ|er)(?![\w\u00ba\u00aa])")
_ORDINAL_WORDS = dict((int(n), w) for w, n in ORDINALS)
_TENS_WORDS = dict((int(n), w) for w, n in ORDINAL_TENS)
_UNIT_WORDS = dict((int(n), w) for w, n in ORDINAL_UNITS)


def ordinal_words(n: int, mark: str = "º") -> str | None:
    """``13`` → *decimotercero*; ``mark`` ``ª``/``ᵃ`` gives the feminine (*vigésima primera*), ``ᵉʳ``/``er`` the
    form before a masculine noun (*vigésimo primer*, like ``1.ᵉʳ`` → *primer*).  ``None`` outside 1..100."""
    if n in _ORDINAL_WORDS:
        word = _ORDINAL_WORDS[n]
    elif n == 100:
        word = "centésimo"
    elif 20 < n < 100:
        word = _TENS_WORDS[n // 10] + (" " + _UNIT_WORDS[n % 10] if n % 10 else "")
    else:
        return None
    if mark in ("ª", "ᵃ"):
        return " ".join(w[:-1] + "a" for w in word.split())
    if mark in ("ᵉʳ", "er"):
        return re.sub(r"(primer|tercer)o$", r"\1", word)
    return word


def _formal_ordinal(m: re.Match[str]) -> str:
    n = int(m.group(1))
    if not 11 <= n <= 100 or m.group(1).startswith("0"):
        return m.group(0)
    return ordinal_words(n, m.group(2)) or m.group(0)


def mark_formal_ordinals(text: str) -> str:
    """``mark`` with written ordinals from 11 to 100 read as words: ``el 80.º aniversario`` → *el octogésimo
    aniversario*, ``la 21.ª edición`` → *la vigésima primera edición*."""
    return mark(_FORMAL_ORDINAL.sub(_formal_ordinal, text))


def _reader(cats, custom_vocab, variants=False):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, variants=variants, custom_vocab=custom_vocab).fst


_MONTH = "(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
_DANGLING_DE = re.compile(r"\bmillón de(?=\s*(?:[.,;:!?)»”\]]|$))")
_YEAR = r"((?:dos mil|mil novecientos|mil ochocientos)\b)"
_BEFORE_YEAR = r"\b([Ee]n|[Dd]esde|[Hh]asta|[Pp]ara|[Aa]) "
# Readings that span several tokens (variants mode): "en el (año) dos mil doce", "del dos mil ocho", "primero de enero".
SENTENCE_ALTERNATIVES: list[tuple[re.Pattern[str], Union[str, Callable[[re.Match[str]], str]]]] = [
    (re.compile(_BEFORE_YEAR + _YEAR), r"\1 el \2"),
    (re.compile(r"\b([Dd])e " + _YEAR), r"\1el \2"),
    (re.compile(_BEFORE_YEAR + _YEAR), r"\1 el año \2"),
    (re.compile(r"\b([Dd])e " + _YEAR), r"\1el año \2"),
    (re.compile(r"\b([Uu])no de (" + _MONTH + r")\b"), lambda m: ("P" if m.group(1) == "U" else "p") + f"rimero de {m.group(2)}"),
]


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class TextNormalizer(Readings):
    """Spanish text normalization (written → spoken): ``21 personas`` → *veintiuna personas*, ``5,4 %`` → *cinco
    coma cuatro por ciento*.

    ``variants=True`` adds ``normalize_variants`` / ``normalize_matching`` / ``normalize_in_context``
    (``damga.core.readings``); ``normalize()`` is the same in both modes.

    ``formal_ordinals=True`` reads a written ordinal from 11 to 100 as the ordinal word, its gender from the
    indicator: ``el 80.º aniversario`` → *el octogésimo aniversario*, ``la 11.ª edición`` → *la undécima edición*,
    ``el 23.ᵉʳ puesto`` → *el vigésimo tercer puesto*.  By default (and above 100) such an ordinal is read as the
    cardinal (*ochenta aniversario*).  Works on the precompiled grammars: the rewrite is done before them."""

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
        formal_ordinals: bool = False,
    ):
        from .categories import ALL_CATEGORIES

        self.variants = resolve_variants(variants, deterministic)
        self.formal_ordinals = formal_ordinals
        self.lang = "es"
        cats = resolve_categories(categories, ALL_CATEGORIES)
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="tn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=es|cats={','.join(sorted(cats))}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=lowercase,
            diagnostics=diagnostics,
            pre_hook=mark_formal_ordinals if formal_ordinals else mark,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES),
            backend=backend,
            custom_vocab=self.custom_vocab,
            casing=CASING,
            build_variants=lambda: _reader(cats, self.custom_vocab, variants=True),
        )

    def normalize(self, text: str) -> str:
        return self.normalize_with_details(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        result = self.engine.normalize(text)
        result.text = reattach(result.text)
        return result

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

    def normalize_variants(self, text: str, n: int = 10) -> list[str]:
        """Spoken readings of ``text``, the default (``normalize(text)``) first, at most ``n``.  With
        ``variants=True``: the readings of the variants grammar (``2,5 millones`` → *dos millones y medio*),
        then the ones that span tokens (``en 2012`` → *en el dos mil doce*)."""
        readings = Readings.normalize_variants(self, text, n=n)
        if not self.variants:
            return readings
        out: list[str] = []
        for r in readings:
            r = reattach(r)
            if r not in out:
                out.append(r)
        for r in list(out):
            for alt in _span_alternatives(r, n * 2):
                if alt not in out:
                    out.append(alt)
        # "medio millón de" needs a noun after it ("unos 500.000." is not "unos medio millón de.")
        return [r for i, r in enumerate(out) if i == 0 or not _DANGLING_DE.search(r)][:n]

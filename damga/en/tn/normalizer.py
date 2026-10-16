from __future__ import annotations

import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.readings import Readings
from ...core.tokens import NormalizationResult
from ...core.variants import resolve_variants
from ..lexicon import CASING, NOT_YEAR

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

# A year-like number before a counted noun is a cardinal, not a year: ``1300 persons``.
COUNTED = (
    "people persons men women children workers jobs members citizens refugees migrants deaths victims cases companies "
    "firms farmers employees students patients households families homes houses projects times units "
    "tonnes tons hectares kilometres kilometers km metres meters kg miles euros dollars pounds"
).split()
_COUNT = re.compile(r"(?<![\w.,$€£])(1\d{3}|20\d{2})(?= (?:" + "|".join(COUNTED) + r")\b)")
_NUMBER_SIGN = re.compile(r"\bNo\. ?(?=\d)")
# "at 20.30", "15.00 hours" are clock times, not decimals.
_DOT_TIME_AFTER = re.compile(r"\b(at|from|until|till|by|before|after|between|and|to|around|about|since) "
                             r"([01]?\d|2[0-3])\.([0-5]\d)\b(?![.,]\d)(?! ?(?:%|per ?cent|million|billion|trillion|km|kg|m|cm|mm|g|t|l|ml|ha|GW|MW|kW|kWh|°)(?!\w))",
                             re.IGNORECASE)
_DOT_TIME_HOURS = re.compile(r"\b([01]?\d|2[0-3])\.([0-5]\d)(?= ?(?:hours|hrs|h)\b)")


_DOUBLE_THE = re.compile(r"\b([Tt]he) the\b")
_OPEN_QUOTE = re.compile(r"([«“‘¿¡]) ")
_CLOSE_QUOTE = re.compile(r" ([»”])")


def _tidy(text: str) -> str:
    """"the 13 October" → "the thirteenth of October", not "the the thirteenth …"; quotes stay on their words."""
    text = _DOUBLE_THE.sub(r"\1", text)
    return _CLOSE_QUOTE.sub(r"\1", _OPEN_QUOTE.sub(r"\1", text))


_ISO_DATE = re.compile(r"\b((?:1[5-9]|20)\d\d)([-/])(0[1-9]|1[0-2])\2(0[1-9]|[12]\d|3[01])\b")   # 2012-12-06, 2012/12/06


# Roman numerals: ordinals after a ruler (Henry VIII), cardinals after a numbering word (Article II); a lone "I"
# is the pronoun otherwise.
_ROMAN = r"(?:XXX|XX|X)?(?:IX|IV|VI{0,3}|I{1,3})|XXX|XX|X"
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10}
RULERS = ("Henry", "Louis", "Charles", "George", "Edward", "William", "Elizabeth", "Richard", "James", "Mary",
          "Benedict", "Pius", "Leo", "Gregory", "Clement", "Innocent", "Boniface", "Urban", "Paul", "Napoleon",
          "Frederick", "Philip", "Felipe", "Carlos", "Peter", "Catherine", "Alexander", "Nicholas", "Ivan", "Constantine",
          "Gustav", "Gustavus", "Christian", "Harald", "Olav", "Haakon", "Carl", "Ludwig", "Otto", "Wilhelm", "Franz",
          "Rainier", "Albert", "Baudouin", "Juan", "Victor", "Umberto", "Ferdinand", "Isabella", "Pedro", "Manuel",
          "Sigismund", "Casimir", "Stephen", "Matthias", "Bela", "Ladislaus", "Ramesses", "Ptolemy", "Cleopatra")
NUMBERED = ("Article", "Articles", "Chapter", "Part", "Title", "Annex", "Section", "Volume", "Book", "Phase", "Stage",
            "Pillar", "Protocol", "Schedule", "Basel", "Solvency", "Brussels", "Rome", "Dublin", "Schengen", "Lomé",
            "Type", "Class", "Category", "Act", "Tier", "Level", "Grade", "Mark", "War", "Vatican", "Gulf", "Chapter")
_RULER_ROMAN = re.compile(r"\b(" + "|".join(RULERS) + r") (" + _ROMAN + r")\b(?![-'’]\w)")
_NUMBERED_ROMAN = re.compile(r"\b(" + "|".join(NUMBERED) + r") (" + _ROMAN + r")\b(?![-'’]\w)")
_NAME_ROMAN = re.compile(r"\b([A-Z][a-z]+) (II|III|IV|VI|VII|VIII|IX|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI)\b(?![-'’]\w)")


def roman_value(numeral: str) -> int:
    total = 0
    for i, c in enumerate(numeral):
        v = _ROMAN_VALUES[c]
        total += -v if i + 1 < len(numeral) and _ROMAN_VALUES[numeral[i + 1]] > v else v
    return total


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# Letters glued to a number are read apart (G20 → G twenty), except units and forms the grammars read whole.
_UNITS = {"km", "m", "cm", "mm", "kg", "g", "mg", "ml", "l", "h", "min", "ms", "mph", "kWh", "MWh", "GWh", "TWh", "kW",
          "MW", "GW", "W", "V", "Hz", "kHz", "MHz", "GHz", "GB", "MB", "TB", "kB", "Mbps", "t", "ha", "ft", "mi", "oz",
          "lb", "lbs", "No", "Nos", "p", "am", "pm", "AM", "PM", "EUR", "USD", "GBP", "CHF", "JPY", "INR", "US"}
_UNIT_WORDS = _UNITS | {line.split("\t")[0] for line in (HERE / "data" / "units.tsv").read_text(encoding="utf-8").splitlines()
                         if line and not line.startswith("#")}
_LETTERS_DIGITS = re.compile(r"\b([A-Za-z]{1,6})-?(\d{1,3})\b(?![.,:/]\d)")
_NUMBER_WORD = re.compile(r"(?<![\w/.@])((?:\d+\.)?\d+)-(?=[A-Za-z]{2})")   # 45-year-old → 45 year-old (not in a URL)
_DECADE = re.compile(r"(?<![\w'’])['’]([2-9])0s\b")                   # '90s → nineties
_SHORT_DECADE = re.compile(r"(?<![\w'’.,$€£-])([2-9])0['’]?s\b")       # 80s, 80's → eighties
_MID = re.compile(r"\bmid-(?=(?:1\d|20)?\d0s\b|['’]\d0s\b)")              # mid-1980s → mid 1980s
_TENS = {"2": "twenties", "3": "thirties", "4": "forties", "5": "fifties", "6": "sixties", "7": "seventies",
         "8": "eighties", "9": "nineties"}
_BN = re.compile(r"(\d)(?: ?bn)\b")                                    # 5bn → 5 billion
_MILLIONS = re.compile(r"\b(\d+(?:\.\d+)?)m(?= (?:people|persons|jobs|users|citizens|households|homes|children|"
                       r"refugees|euros|dollars|pounds|tonnes|barrels|visitors|tourists|workers|members|cases|deaths|"
                       r"votes|voters|inhabitants|customers|patients|vehicles|cars)\b)")
_PENCE = re.compile(r"\b(\d+)p\b")
_DASH_AFTER = re.compile(r"(\d)([—–])(?=[^\W\d])")                    # 2020—the → 2020 — the
_DASH_BEFORE = re.compile(r"(?<=[^\W\d])([—–])(\d)")
_NUMBERS_SIGN = re.compile(r"\bNos\. ?(?=\d)")
# An IBAN written in groups (MT84 MALT 0110 … AST0 01S) keeps its groups whole for the bank grammar.
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: [A-Z0-9]{4}){2,7}(?: [A-Z0-9]{1,3})?\b")


# Mixed letter/digit codes (B2A23C) are read in pieces; up to three digits as a number, longer groups digit by
# digit.  _CODE_KEEP lists the forms the grammars read whole (21st, 1990s, 5pm, 5bn, 2x8).
_CODE = re.compile(r"(?<![\w@/.:#+$€£¥₹₩-])(?=[A-Za-z]*\d)(?=\d*[A-Za-z])[A-Za-z0-9]+(?![\w@/:+-]|[.,]\w)")
_CODE_KEEP = re.compile(r"\d+(?:st|nd|rd|th|s|am|pm|AM|PM|bn|p|ST|ND|RD|TH)|\d+[x×]\d+")
_GROUPS = re.compile(r"\d+|[A-Za-z]+")
# A number said digit by digit after the words that ask for one: "card ending in 8876", "your PIN is 4421".
_DIGIT_BY_DIGIT = re.compile(r"\b((?:ending|ends) (?:in|with)|last (?:four|4) digits(?: are| of)?|PIN(?: is)?|pin is|OTP"
                             r"(?: is)?|otp is|passcode(?: is)?|(?:verification|confirmation|security) code(?: is)?) "
                             r"(\d{3,8})\b")
# "Elm St." → "Elm Street"; "St." before a name is a saint (St. Louis) and is left to the lexicon.
_ADDRESS_WORDS = {"St": "Street", "Ave": "Avenue", "Rd": "Road", "Blvd": "Boulevard", "Ct": "Court", "Ln": "Lane",
                  "Hwy": "Highway", "hwy": "Highway", "Expy": "Expressway", "Pkwy": "Parkway", "st": "Street"}
_COMPASS = {"N": "North", "S": "South", "E": "East", "W": "West"}
# A ZIP code after a state's two letters is read digit by digit: "CA 95051", "NY 10001-1234".
US_STATES = ("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND "
             "OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY").split()
_ZIP = re.compile(r"\b((?:" + "|".join(US_STATES) + r"),? )(\d{5})(-\d{4})?\b(?![-.,]\d)")
_ADDRESS = re.compile(r"\b(\d+ )((?:[NSEW] )?)((?:(?:\d+(?:st|nd|rd|th)|[A-Z][a-z]+) ){1,3})("
                      + "|".join(_ADDRESS_WORDS) + r")\b\.?")
_STREET_END = re.compile(r"\b([A-Z][a-z]+) St\b(\.?)(?=\s*[,;]|\s*$|\s+[a-z])")


def _code(m: re.Match) -> str:
    tok = m.group(0)
    lead = re.match(r"\d+([A-Za-z]+\d*)$", tok)
    if (_CODE_KEEP.fullmatch(tok) or tok in _UNIT_WORDS or (lead and lead.group(1) in _UNIT_WORDS)
            or re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", tok)):          # an IBAN in one piece
        return tok
    parts = []
    for g in _GROUPS.findall(tok):
        parts.append(" ".join(g) if g.isdigit() and (len(g) > 3 or (g[0] == "0" and len(g) > 1)) else g)
    return " ".join(parts)


def _sentence_end(m: re.Match) -> str:
    """The point of an abbreviation that also ends the sentence stays: ``Elm St. It was`` → ``Elm Street. It was``."""
    rest = m.string[m.end():]
    return "." if m.group(0).endswith(".") and (not rest.strip() or re.match(r"\s+[A-Z]", rest)) else ""


def _address(m: re.Match) -> str:
    compass = _COMPASS[m.group(2).strip()] + " " if m.group(2) else ""
    return f"{m.group(1)}{compass}{m.group(3)}{_ADDRESS_WORDS[m.group(4)]}{_sentence_end(m)}"


_MONTH_NAMES = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Sept", "Oct", "Nov", "Dec", "June",
                "July"}


def _letters_digits(m: re.Match, keep: Sequence[tuple[int, int]] = ()) -> str:
    if m.group(1) in _UNITS or m.group(1).capitalize() in _MONTH_NAMES or any(a <= m.start() < b for a, b in keep):
        return m.group(0)
    return f"{m.group(1)} {m.group(2)}"


def mark_counts(text: str) -> str:
    text = _ISO_DATE.sub(r"\4/\3/\1", text)
    text = _DIGIT_BY_DIGIT.sub(lambda m: f"{m.group(1)} {' '.join(m.group(2))}", text)
    text = _ADDRESS.sub(_address, text)
    text = _STREET_END.sub(lambda m: f"{m.group(1)} Street{_sentence_end(m)}", text)
    text = _ZIP.sub(lambda m: m.group(1) + " ".join(m.group(2)) + (", " + " ".join(m.group(3)[1:]) if m.group(3) else ""),
                    text)
    text = _RULER_ROMAN.sub(lambda m: f"{m.group(1)} the {_ordinal(roman_value(m.group(2)))}", text)
    text = _NUMBERED_ROMAN.sub(lambda m: f"{m.group(1)} {roman_value(m.group(2))}", text)
    text = _NAME_ROMAN.sub(lambda m: f"{m.group(1)} {roman_value(m.group(2))}", text)
    ibans = [m.span() for m in _IBAN.finditer(text)]
    text = _LETTERS_DIGITS.sub(lambda m: _letters_digits(m, ibans), text)
    text = _NUMBER_WORD.sub(r"\1 ", text)
    text = _MID.sub("mid ", text)
    text = _SHORT_DECADE.sub(lambda m: _TENS[m.group(1)], text)
    text = _DASH_BEFORE.sub(r" \1 \2", _DASH_AFTER.sub(r"\1 \2 ", text))
    text = _DECADE.sub(lambda m: _TENS[m.group(1)], text)
    text = _BN.sub(r"\1 billion", text)
    text = _MILLIONS.sub(r"\1 million", text)
    text = _PENCE.sub(lambda m: f"{m.group(1)} {'penny' if m.group(1) == '1' else 'pence'}", text)
    text = _NUMBERS_SIGN.sub("numbers ", text)
    text = _NUMBER_SIGN.sub("number ", text)
    ibans = [m.span() for m in _IBAN.finditer(text)]
    text = _CODE.sub(lambda m: m.group(0) if any(a <= m.start() < b for a, b in ibans) else _code(m), text)
    text = _DOT_TIME_AFTER.sub(r"\1 \2:\3", text)
    text = _DOT_TIME_HOURS.sub(r"\1:\2", text)
    return _COUNT.sub(NOT_YEAR + r"\1", text)


def _reader(cats, custom_vocab, variants=False):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, variants=variants, custom_vocab=custom_vocab).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class TextNormalizer(Readings):
    """English text normalization (written → spoken): ``$5.50`` → *five dollars fifty cents*.

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
        self.lang = "en"
        cats = resolve_categories(categories, ALL_CATEGORIES)
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="tn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=en|cats={','.join(sorted(cats))}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=lowercase,
            diagnostics=diagnostics,
            pre_hook=mark_counts,
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
        result.text = _tidy(result.text)
        return result

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

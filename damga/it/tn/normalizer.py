from __future__ import annotations

import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.readings import Readings
from ...core.tokens import NormalizationResult
from ...core.variants import resolve_variants
from ..lexicon import CASING, MONTHS

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

# "1" before a noun is the article: un anno, una persona, uno studente.  Nouns in -a are feminine except these.
_MASCULINE_A = {"problema", "sistema", "programma", "tema", "clima", "pianeta", "poeta", "dramma", "diploma",
                "schema", "telegramma", "pilota", "collega", "papa", "giorno", "cinema", "idioma", "panorama",
                "trauma", "dilemma", "enigma", "emblema", "teorema", "stratagemma", "sistemi"}
_ONE = re.compile(r"(?<![\w.,])1 (?=([A-Za-zÀ-ÿ]+)\b)")
_NUMBER_SIGN = re.compile(r"\b[Nn]r?\. ?(?=\d)")
_ISO_DATE = re.compile(r"\b((?:1[5-9]|20)\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
_MONTHS = set(MONTHS)


_ELIDED_GAP = re.compile(r"(?i)\b((?:l|dell|all|dall|nell|sull|un|quell|coll)') (?=\w)")
# l'1% → l'un per cento: "un" after an elided article
_ELIDED_ONE = re.compile(r"(?i)\b((?:l|dell|all|dall|nell|sull|coll)')uno (?=percento\b|per cento\b)")


def _finish(text: str) -> str:
    """What is left after writing: the elided article joined to its number, and "l'un per cento"."""
    return _ELIDED_ONE.sub(r"\1un ", _ELIDED_GAP.sub(r"\1", text))
# 1 eur: the money grammar says it (un euro)
_CURRENCY_WORDS = {"eur"}
_UNITS = {line.split("\t")[0] for line in (HERE / "data" / "units.tsv").read_text(encoding="utf-8").splitlines()
          if line and not line.startswith("#")}


# A number after these names something (l'articolo 1, la rubrica 1a): it stays a number, said as written.
REFERENCE_WORDS = ("articolo", "articoli", "paragrafo", "comma", "punto", "rubrica", "capitolo", "allegato",
                   "emendamento", "emendamenti", "numero", "linea", "considerando", "titolo", "sezione", "parte",
                   "pagina", "lettera", "voce", "asse", "priorità", "obiettivo", "fase", "livello", "pilastro")
_REFERENCE = re.compile(r"\b(?:" + "|".join(REFERENCE_WORDS) + r") $", re.IGNORECASE)
# rubrica 1a, articolo 3b: a label, "uno a"
_LABEL = re.compile(r"(?i)\b((?:" + "|".join(REFERENCE_WORDS) + r") \d+)([a-z])\b")
# Words after "1" that are no noun: l'articolo 1 della Costituzione is "uno della", not "una della".
_FUNCTION_WORDS = {"per", "con", "dei", "del", "della", "delle", "dello", "degli", "di", "da", "dal", "dalla",
                   "dalle", "dallo", "dagli", "nel", "nella", "nelle", "nello", "negli", "sul", "sulla", "sulle",
                   "sullo", "sugli", "al", "alla", "alle", "allo", "agli", "ai", "tra", "fra", "che", "come", "non",
                   "anche", "sia", "una", "uno", "sono", "era", "ogni", "più", "meno", "contro", "verso"}


def _article(m: re.Match) -> str:
    noun = m.group(1)
    low = noun.lower()
    if _REFERENCE.search(m.string[:m.start()]):
        return m.group(0)
    if (low in _MONTHS or noun in _UNITS or len(low) < 3 or noun.isupper() or low in _FUNCTION_WORDS
            or low in _CURRENCY_WORDS):
        return m.group(0)
    if low.endswith("a") and low not in _MASCULINE_A:
        return "una "
    if re.match(r"s[^aeiouàèéìòù]|z|gn|ps|x|y", low):
        return "uno "
    return "un "


# Letters and digits glued (CO2, 5G) are read apart; an ordinal (37a, 70o) stays whole.
_LETTER_DIGIT = re.compile(r"(?<=[A-Za-zÀ-ÿ])(?=\d)")
_DIGIT_LETTER = re.compile(r"(?<=\d)(?=[A-Za-zÀ-ÿ])(?![ao]\b)(?![ºª°])")
# An IBAN or an account number after its name is read by readers/bank.py: its letters and digits stay together.
IBAN_COUNTRIES = ("AD AE AL AT AZ BA BE BG BH BI BR BY CH CR CY CZ DE DJ DK DO EE EG ES FI FK FO FR GB GE GI GL GR "
                  "GT HN HR HU IE IL IQ IS IT JO KW KZ LB LC LI LT LU LV LY MC MD ME MK MN MR MT MU NI NL NO OM PK "
                  "PL PS PT QA RO RS RU SA SC SD SE SI SK SM SO ST SV TL TN TR UA VA VG XK YE").split()
_IBAN = re.compile(r"\b(?:" + "|".join(IBAN_COUNTRIES)
                   + r")\d{2}(?:(?: [A-Z0-9]{4}){2,7}(?: [A-Z0-9]{1,4})?|[A-Z0-9]{11,30})\b")
_MARK = r"(?::? (?:n\.|n°|nr\.) ?|:? )"
# An address (mario92@libero.it) is read by readers/email_url.py: its letters and digits stay together too.
_ELECTRONIC = re.compile(r"(?:https?://|www\.)[^\s]+[^\s.,;:!?)]|[\w.+-]*@[\w-]+(?:\.[\w-]+)*")
_ACCOUNT = re.compile(r"\b(?:(?i:conto corrente|numero di conto|c/c)" + _MARK + r"[A-Z0-9]{6,12}"
                      r"|(?i:conto)" + _MARK + r"[A-Z0-9]{12})\b")


def _split_letters_digits(text: str) -> str:
    kept = [m.span() for m in _IBAN.finditer(text) if 15 <= len(m.group(0).replace(" ", "")) <= 34]
    kept += [m.span() for m in _ACCOUNT.finditer(text)]
    kept += [m.span() for m in _ELECTRONIC.finditer(text)]
    out, at = [], 0
    for start, end in sorted(kept):
        if start < at:
            continue
        out.append(_DIGIT_LETTER.sub(" ", _LETTER_DIGIT.sub(" ", text[at:start])))
        out.append(text[start:end])
        at = end
    out.append(_DIGIT_LETTER.sub(" ", _LETTER_DIGIT.sub(" ", text[at:])))
    return "".join(out)


# anni '70, del '94, dell''800: an abbreviated year or century is the number
_SHORT_YEAR = re.compile(r"(?:(?<=\s)|(?<=^)|(?<=\w'))'(?=\d{2,3}\b)")


# "alle 1.30" is "all'una e trenta"
_AT_ONE = re.compile(r"\b([Aa])lle (0?1[.:]\d\d)\b")

# "5 mln" / "2,5 mld." → "5 milioni" / "2,5 miliardi"
_SCALE_ABBR = re.compile(r"(?<![\w.,])(\d+(?:,\d+)?) ?(mln|mld|mrd)\b\.?")
_SCALE_WORDS = {"mln": ("milione", "milioni"), "mld": ("miliardo", "miliardi"), "mrd": ("miliardo", "miliardi")}


def _scale(m: re.Match) -> str:
    one, many = _SCALE_WORDS[m.group(2)]
    return f"{m.group(1)} {one if m.group(1) == '1' else many}"


def prepare(text: str) -> str:
    text = _SCALE_ABBR.sub(_scale, text)
    text = _LABEL.sub(r"\1 \2", text)
    text = _AT_ONE.sub(r"\1ll'\2", text)
    text = _SHORT_YEAR.sub("", text)
    text = _split_letters_digits(text)
    text = _ISO_DATE.sub(r"\3/\2/\1", text)
    text = _NUMBER_SIGN.sub("numero ", text)
    return _ONE.sub(_article, text)


def _reader(cats, custom_vocab):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab).fst


def _writer(cats):
    from ...en.tn.writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class TextNormalizer(Readings):
    """Italian text normalization (written → spoken): ``2016`` → *duemilasedici*, ``1,50 €`` → *un euro e cinquanta*.

    ``variants=True`` adds ``normalize_variants`` / ``normalize_matching`` (``damga.core.readings``) for the
    other ways a form is read (``2016`` → *duemila e sedici*); ``normalize()`` is the same in both modes."""

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
        self.lang = "it"
        cats = resolve_categories(categories, ALL_CATEGORIES)
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="tn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=it|cats={','.join(sorted(cats))}",
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
        )

    def normalize(self, text: str) -> str:
        return self.normalize_with_details(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        result = self.engine.normalize(text)
        result.text = _finish(result.text)
        return result

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

    def normalize_variants(self, text: str, n: int = 10) -> list[str]:
        """Spoken readings of ``text``, the default (``normalize(text)``) first, at most ``n``, cheapest first.

        Each token of the default record is varied with the rules of ``damga.it.tn.variants``."""
        default = self.normalize(text)
        if not self.variants or n <= 1:
            return [default]
        from ...core.variants import parse_record
        from .variants import alternatives

        engine = self.engine
        clean = engine.prepare(text)
        record = engine.read(clean) if clean else None
        tokens = parse_record(record) if record else None
        if not tokens:
            return [default]
        options = []
        prev = ""
        for tok in tokens:
            opts = [(tok.raw, 0.0)]
            said = tok.fields.get("text")
            if said is not None:
                old = 'text="' + said.replace("\\", "\\\\").replace('"', '\\"') + '"'
                for alt, extra in alternatives(tok.cls, said, prev):
                    opts.append((tok.raw.replace(old, 'text="' + alt + '"', 1), extra))
            prev = tok.fields.get("word", said or "")
            options.append(opts)
        out = [default]
        for raws, _ in _cheapest(options, n * 2):
            spoken = engine.write_record(" ".join(raws))
            if spoken is None:
                continue
            spoken = _finish(engine.finish(text, clean, spoken))
            if spoken not in out:
                out.append(spoken)
            if len(out) == n:
                break
        return out


def _cheapest(options: list[list[tuple[str, float]]], limit: int) -> list[tuple[list[str], float]]:
    """The ``limit`` cheapest combinations of per-token options (each list starts with its default at cost 0)."""
    import heapq
    import itertools

    varied = [i for i, o in enumerate(options) if len(o) > 1]
    combos: list[tuple[float, tuple[int, ...]]] = []
    # cap the product of per-token options
    for picks in itertools.islice(itertools.product(*[range(len(options[i])) for i in varied]), 5000):
        combos.append((sum(options[i][p][1] for i, p in zip(varied, picks)), picks))
    out = []
    for cost, picks in heapq.nsmallest(limit, combos, key=lambda t: (t[0], t[1])):
        chosen = dict(zip(varied, picks))
        out.append(([o[chosen.get(i, 0)][0] for i, o in enumerate(options)], cost))
    return out

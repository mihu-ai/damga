from __future__ import annotations

import dataclasses
import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.tokens import NormalizationResult
from ...core.variants import reject_variants
from ..lexicon import BIG_SCALES, CASING, DIGITS, TEENS, TIES
from .fractions import fractions_to_digits

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

# Spellings folded into the form the grammars read: "einhundert" → "hundert", "zwo" → "zwei".
_EIN = re.compile(r"\bein(hundert|tausend)", re.IGNORECASE)
_ZWO = re.compile(r"\bzwo(?=\b|hundert|tausend|und)", re.IGNORECASE)
_EIN_INNER = re.compile(r"(?<=tausend)ein(hundert)", re.IGNORECASE)


# A number written in pieces is joined into one word.  "fünf und zwanzig" alone can mean two numbers, so
# "unit und ten" is joined only next to a scale word, after "minus", or as an ordinal.
_U = "|".join(w for w, _ in DIGITS)
_TEEN = "|".join(w for w, _ in TEENS)
_TIE = "|".join(w for w, _ in TIES)
_TWO = f"(?:(?:{_U})und(?:{_TIE})|{_TIE}|{_TEEN}|eins|{_U})"
_GROUP = f"(?:(?:{_U})?hundert(?:{_TWO})?|{_TWO})"
_NUMBER = re.compile(f"(?:(?:{_GROUP})?tausend(?:{_GROUP})?|{_GROUP}|(?:{_TEEN})hundert(?:{_TWO})?)")
_TWO_RE = re.compile(_TWO)
_TIE_RE = re.compile(f"(?:{_TIE})(?:st(?:e|en|er|es|em))?")
# ordinal ending → cardinal stem (dritten → drei), to validate the whole word
_ORDINAL = re.compile(r"(erst|zweit|dritt|viert|fünft|sechst|siebt|acht|neunt|zehnt|elft|zwölft|zigst|ßigst|"
                      r"hundertst|tausendst)(e|en|er|es|em)$")
_ORDINAL_STEMS = {"erst": "eins", "zweit": "zwei", "dritt": "drei", "viert": "vier", "fünft": "fünf", "sechst": "sechs",
                  "siebt": "sieben", "acht": "acht", "neunt": "neun", "zehnt": "zehn", "elft": "elf", "zwölft": "zwölf",
                  "zigst": "zig", "ßigst": "ßig", "hundertst": "hundert", "tausendst": "tausend"}
_SCALE_END = ("hundert", "tausend")
_SCALE_NEXT = _SCALE_END + tuple(w.lower() for s in BIG_SCALES for w in s)


def _cardinal_of(word: str) -> str | None:
    """The cardinal a joined number word reads (an ordinal as its cardinal), or None when it is no number."""
    m = _ORDINAL.search(word)
    card = word[:m.start()] + _ORDINAL_STEMS[m.group(1)] if m else word
    return card if _NUMBER.fullmatch(card) else None


def _is_ordinal(word: str) -> bool:
    return bool(_ORDINAL.search(word)) and _cardinal_of(word) is not None


def _split(token: str) -> tuple[str, str]:
    word = token.rstrip(",.;:!?")
    return word, token[len(word):]


def join_number_pieces(text: str) -> str:
    """``zwei hundert vier und fünfzig`` → ``zweihundertvierundfünfzig``; pieces that make no number stay apart."""
    tokens = text.split(" ")
    out: list[str] = []
    i = 0
    while i < len(tokens):
        cur, j = tokens[i], i + 1
        after_minus = i > 0 and tokens[i - 1] == "minus"
        between = "zwischen" in tokens[max(0, i - 2):i]          # zwischen fünf und zwanzig millionen: two numbers
        if _cardinal_of(cur) is not None and not _is_ordinal(cur):
            while j < len(tokens) and not _is_ordinal(cur):
                word, punct = _split(tokens[j])
                if word != "und":
                    if not ((cur.endswith(_SCALE_END) or word.startswith(_SCALE_END))
                            and _cardinal_of(cur + word) is not None):
                        break
                    cur, j = cur + word, j + 1
                elif not punct and j + 1 < len(tokens):
                    word, punct = _split(tokens[j + 1])
                    later = tokens[j + 2] if j + 2 < len(tokens) else ""
                    if (cur.endswith(_SCALE_END) and _TWO_RE.fullmatch(_cardinal_of(word) or "")
                            and _cardinal_of(cur + word) is not None):
                        cur, j = cur + word, j + 2               # hundert und zwanzig → hundertzwanzig
                    elif (_TIE_RE.fullmatch(word) and _cardinal_of(cur + "und" + word) is not None
                          and (any(s in cur for s in _SCALE_END) or _is_ordinal(word) or after_minus
                               or later.startswith(_SCALE_NEXT) and not between)):
                        cur, j = cur + "und" + word, j + 2       # vier und zwanzig tausend, ein und zwanzigste
                    else:
                        break
                else:
                    break
                if punct:
                    cur += punct
                    break
        out.append(cur)
        i = j
    return " ".join(out)


def respell(text: str) -> str:
    text = join_number_pieces(_ZWO.sub("zwei", text))
    # "ein" leading a number, also after "tausend" in a joined one: ein tausend ein hundert → tausendhundert
    return _EIN_INNER.sub(r"\1", _EIN.sub(r"\1", text))


def _reader(cats, custom_vocab, group):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, custom_vocab=custom_vocab, group=group).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class InverseNormalizer:
    """German inverse text normalization (spoken → written): ``fünfundzwanzigtausend`` → ``25.000``.

    Lone numbers up to twelve stay words.

    ``fraction_digits=True`` (opt-in) writes spoken fractions as digits with a slash: ``drei viertel`` → ``3/4``,
    ``ein halb`` → ``1/2``, ``zweieinhalb`` → ``2 1/2``; a fraction noun without a number (``die Hälfte``) or
    followed by a genitive article (``ein Viertel der Stadt``) stays.  It runs on the ITN output in plain
    Python, so it works with the precompiled grammars; see ``fractions.py``."""

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
        fraction_digits: bool = False,
    ):
        from .categories import ALL_CATEGORIES

        reject_variants(variants, deterministic)
        cats = resolve_categories(categories, ALL_CATEGORIES)
        if strict:
            cats = tuple(c for c in cats if c not in ("cardinal", "ordinal", "decimal"))
        self.categories = cats
        self.fraction_digits = fraction_digits
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="itn",
            build_reader=lambda: _reader(cats, self.custom_vocab, group_thousands),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS, ROOT / "tn" / "data"],
            config_key=f"lang=de|cats={','.join(sorted(cats))}|group={group_thousands}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=True,
            preserve_case=preserve_case,
            diagnostics=diagnostics,
            pre_hook=respell,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES and group_thousands),
            backend=backend,
            custom_vocab=self.custom_vocab,
            casing=CASING,
        )

    def normalize(self, text: str) -> str:
        return self.normalize_with_details(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        res = self.engine.normalize(text)
        if self.fraction_digits:
            out = fractions_to_digits(res.text)
            if out != res.text:
                res = dataclasses.replace(res, text=out, changed=True)
        return res

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]

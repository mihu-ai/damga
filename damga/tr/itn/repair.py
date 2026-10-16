"""Spelling repair applied to ITN input before the grammars (pure Python, no pynini).

Restores dropped diacritics (``yuz elli``) and splits glued number words (``yirmibeş``).  Only the closed vocabulary
below is touched: a token is rewritten only when it folds to exactly one known word that is not itself another word.
"""
from __future__ import annotations

import re

from ...core.unicode import tr_upper
from ..lexicon import CURRENCY_WORDS, MONTHS, NUMBER_WORDS

_FOLD = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")

# Words whose ASCII fold is another real word: never rewrite these.
_AMBIGUOUS = {"uç"}
# Idioms / titles that read as one word although they are made of number words: never split these.
_NO_SPLIT = {"binbir"}

_ORDINALS = [
    "birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yedinci", "sekizinci", "dokuzuncu", "onuncu",
    "yirminci", "otuzuncu", "kırkıncı", "ellinci", "altmışıncı", "yetmişinci", "sekseninci", "doksanıncı", "yüzüncü",
    "bininci",
]
_EXTRA = ["buçuk", "çeyrek", "yüzde", "binde", "kuruş", "çizgi", "saat", "türk", "lirası", "kilometre", "yüz"]

_VOCAB: set[str] = set(NUMBER_WORDS) | set(MONTHS) | set(CURRENCY_WORDS) | set(_ORDINALS) | set(_EXTRA)
_FOLDED: dict[str, str] = {}
for _w in sorted(_VOCAB):
    if _w in _AMBIGUOUS or " " in _w:
        continue
    _FOLDED.setdefault(_w.translate(_FOLD), _w)

# Glue splitting uses only cardinal words; "on"/"bin" are short, so require the whole token to segment.
_GLUE_WORDS: list[str] = sorted(
    {w for w in NUMBER_WORDS if w not in ("artı", "eksi", "virgül")} | set(_ORDINALS), key=len, reverse=True
)
_GLUE_FOLDED: dict[str, str] = {w.translate(_FOLD): w for w in _GLUE_WORDS}


_BACK = "aıou"
_VOICELESS = "çfhkpsşt"
_VOWELS = "aeıioöuü"


def _case_suffixes(stem: str) -> list[str]:
    """Ablative / locative / dative forms of ``stem`` with Turkish vowel harmony.

    Accusative and genitive are left out on purpose: ``besi`` (feeding, or the letter name "be" + i) and similar
    folded forms are real words, and the recognizer produces them as letter spellings.
    """
    v = next(c for c in reversed(stem) if c in _VOWELS)
    two = "a" if v in _BACK else "e"
    d = "t" if stem[-1] in _VOICELESS else "d"
    vowel_end = stem[-1] in _VOWELS
    y = "y" if vowel_end else ""
    return [stem + d + two + "n", stem + d + two, stem + y + two]


# Suffixed folded forms (``sifirdan``, ``bese``, ``dortte``): only stems that actually lose a diacritic, and never
# ``yüz`` (``yuzu`` = face as often as hundred) or the ambiguous ``uç``; ``beste`` (composition) is a real word.
_FOLDED_SUFFIXED: dict[str, str] = {}
for _w in sorted(_VOCAB):
    if " " in _w or _w in _AMBIGUOUS or _w in ("yüz",) or _w.translate(_FOLD) == _w or len(_w) < 3:
        continue
    for _form in _case_suffixes(_w):
        if _form.translate(_FOLD) != "beste":
            _FOLDED_SUFFIXED.setdefault(_form.translate(_FOLD), _form)

_TOKEN = re.compile(r"^([^\wçğıöşüÇĞİÖŞÜ']*)([\wçğıöşüÇĞİÖŞÜ]+)([^\wçğıöşüÇĞİÖŞÜ]*)$")


def _lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def _ascii_lower(s: str) -> str:
    """Lower-case for matching only: recognizers and all-caps text do not keep the i / ı distinction."""
    return s.replace("İ", "i").replace("I", "i").lower().translate(_FOLD)


def _segment(folded: str) -> list[str] | None:
    """Split ``folded`` into >= 2 cardinal words, fewest segments first; None if impossible."""
    n = len(folded)
    best: list[list[str] | None] = [None] * (n + 1)
    best[0] = []
    for i in range(1, n + 1):
        for fw, w in _GLUE_FOLDED.items():
            L = len(fw)
            if L <= i and folded.startswith(fw, i - L) and best[i - L] is not None:
                cand = best[i - L] + [w]  # type: ignore[operator]
                if best[i] is None or len(cand) < len(best[i]):  # type: ignore[arg-type]
                    best[i] = cand
    seg = best[n]
    return seg if seg and len(seg) >= 2 else None


def _match_case(src: str, out: str) -> str:
    if src.isupper() and len(src) > 1:
        return tr_upper(out)
    if src[:1].isupper():
        return out[:1].upper() + out[1:]
    return out


def repair_token(core: str) -> str:
    low = _lower(core)
    if low in _VOCAB or low in _AMBIGUOUS:
        return core
    folded = _ascii_lower(core)
    if folded in _NO_SPLIT:
        return core
    hit = _FOLDED.get(folded)
    if hit is not None:
        return _match_case(core, hit)
    suffixed = _FOLDED_SUFFIXED.get(folded)
    if suffixed is not None:
        return _match_case(core, suffixed)
    seg = _segment(folded)
    if seg is not None:
        return _match_case(core, " ".join(seg))
    return core


# Letter names that are not ordinary words.  ``ve``/``de``/``da``/``ne``/``se``/``te``/``me``/``ye``/``e`` and the
# vowel names are left out, so three of these in a row are a spelled acronym ("a be ce" → ABC, "ka pe ka" → KPK).
_LETTER_NAMES = {"be": "B", "ce": "C", "çe": "Ç", "fe": "F", "ge": "G", "he": "H", "je": "J", "ke": "K", "ka": "K",
                 "le": "L", "pe": "P", "re": "R", "şe": "Ş", "ze": "Z"}
_LETTER_A = "a"


def _join_letter_names(tokens: list[str]) -> list[str]:
    """Join runs of >= 3 spelled letter names into one upper-case token (no two equal letters in a row, so a laugh
    like ``he he he`` is not an acronym; ``a`` only counts next to consonant names)."""
    out: list[str] = []
    i, n = 0, len(tokens)
    while i < n:
        j = i
        letters: list[str] = []
        while j < n and (tokens[j] == "" or tokens[j].lower() in _LETTER_NAMES or tokens[j].lower() == _LETTER_A):
            if tokens[j] == "":
                break
            low = tokens[j].lower()
            letter = "A" if low == _LETTER_A else _LETTER_NAMES[low]
            if letters and letters[-1] == letter:
                break
            letters.append(letter)
            j += 1
        consonants = sum(1 for tok in tokens[i:j] if tok.lower() != _LETTER_A)
        if len(letters) >= 3 and consonants >= 2:
            out.append("".join(letters))
            i = j
        else:
            out.append(tokens[i])
            i += 1
    return out


def repair_spelling(text: str) -> str:
    """Return ``text`` with folded / glued number words restored and spelled-out letters joined; everything else is
    left byte-identical."""
    out = []
    for tok in text.split(" "):
        m = _TOKEN.match(tok)
        out.append(tok if m is None else m.group(1) + repair_token(m.group(2)) + m.group(3))
    return " ".join(_join_letter_names(out))


# ``yarım`` is 12:30 only where it clearly names a time (``saat yarımda``), not ``yarımda kaldı`` or ``yarım saat``.
_HALF_PAST_TWELVE = [
    (re.compile(r"\b(saat )yarım(da|dan|a)?\b(?! (?:saat|kilo|ekmek|kürede|küre))", re.IGNORECASE),
     lambda m: m.group(1) + "12:30" + (f"'{m.group(2)}" if m.group(2) else "")),
    (re.compile(r"(?<!saat )\byarımda\b(?! kal)", re.IGNORECASE), lambda m: "12:30'da"),
    (re.compile(r"\byarıma(?= kadar\b)", re.IGNORECASE), lambda m: "12:30'a"),
    (re.compile(r"\byarımdan(?= (?:sonra|önce|itibaren)\b)", re.IGNORECASE), lambda m: "12:30'dan"),
]


def colloquial_times(text: str) -> str:
    """``yarımda geleceğim`` → ``12:30'da geleceğim``; ``yarım`` meaning half is left alone."""
    for pattern, repl in _HALF_PAST_TWELVE:
        text = pattern.sub(repl, text)
    return text

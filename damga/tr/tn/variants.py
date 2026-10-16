"""Alternative Turkish readings of a TN token, for variants mode.

Each function gets the parsed token, its default reading and ``say`` (digits → the default cardinal reading) and
returns the other readings of the same written form (never the default), e.g.:

    09:30   dokuz otuz          dokuz buçuk
    250 TL  … Türk lirası       … lira
"""
from __future__ import annotations

import re
from typing import Callable

from ...core.variants import Token
from ..lexicon import NUMBER_WORDS, ZERO
from ..morph import reinflect

Say = Callable[[str], str]

# Hour words in the 12-hour clock (1–12 end in one of these) with the accusative (``dokuzu çeyrek geçe``) and the
# dative (``ona çeyrek var``) the clock idioms need.
_ACC = {"bir": "biri", "iki": "ikiyi", "üç": "üçü", "dört": "dördü", "beş": "beşi", "altı": "altıyı",
        "yedi": "yediyi", "sekiz": "sekizi", "dokuz": "dokuzu", "on": "onu"}
_DAT = {"bir": "bire", "iki": "ikiye", "üç": "üçe", "dört": "dörde", "beş": "beşe", "altı": "altıya",
        "yedi": "yediye", "sekiz": "sekize", "dokuz": "dokuza", "on": "ona"}


def _inflect(words: str, table: dict[str, str]) -> str | None:
    head, _, last = words.rpartition(" ")
    if last not in table:
        return None
    return (head + " " if head else "") + table[last]


def _bucuk(suffix: str) -> str | None:
    """``buçuk`` with the case suffix the default reading carried (``09:30'da`` → ``dokuz buçukta``)."""
    if not suffix:
        return "buçuk"
    s = suffix[1:] if suffix[:1] in ("y", "n") else suffix
    for pattern, form in ((r"[dt][ae]", "buçukta"), (r"[dt][ae]n", "buçuktan"), (r"[dt][ae]ki", "buçuktaki"),
                          (r"[ae]", "buçuğa"), (r"[ıiuü]", "buçuğu"), (r"[ıiuü]n", "buçuğun"),
                          (r"l[ıiuü]k", "buçukluk"), (r"l[ıiuü]", "buçuklu"), (r"l[ae]", "buçukla")):
        if re.fullmatch(pattern, s):
            return form
    return None


def _yarim(suffix: str) -> str | None:
    """``yarım`` (12:30 in everyday speech) with the case suffix the default reading carried: ``12:30'da`` →
    ``yarımda``."""
    if not suffix:
        return "yarım"
    s = suffix[1:] if suffix[:1] in ("y", "n") else suffix
    for pattern, form in ((r"[dt][ae]", "yarımda"), (r"[dt][ae]n", "yarımdan"), (r"[dt][ae]ki", "yarımdaki"),
                          (r"[ae]", "yarıma"), (r"[ıiuü]", "yarımı"), (r"[ıiuü]n", "yarımın"), (r"l[ae]", "yarımla")):
        if re.fullmatch(pattern, s):
            return form
    return None


def _time(tok: Token, default: str, say: Say) -> list[str]:
    f = tok.fields
    if not (f.get("hours", "").isdigit() and f.get("minutes", "").isdigit()):
        return []
    h, m, suffix = int(f["hours"]), int(f["minutes"]), f.get("suffix", "")
    if h > 23 or m > 59:
        return []
    h12 = h % 12 or 12
    hour_words = say(f["hours"].lstrip("0") or "0")
    out = []
    # 21:45 → dokuz kırk beş: the minutes (and their suffix) stay as they are.
    if h12 != h and default.startswith(hour_words) and (m or not suffix):
        out.append(say(str(h12)) + default[len(hour_words):])
    if m == 30:
        b = _bucuk(suffix)
        if b:
            out += [f"{say(str(x))} {b}" for x in dict.fromkeys((h, h12))]
        y = _yarim(suffix) if h12 == 12 else None
        if y:
            out.append(y)                                   # 12:30'da → yarımda
    elif not suffix and 0 < m < 30:
        hour = _inflect(say(str(h12)), _ACC)
        if hour:
            out.append(f"{hour} {'çeyrek' if m == 15 else say(str(m))} geçe")
    elif not suffix and m > 30:
        hour = _inflect(say(str(h12 % 12 + 1)), _DAT)
        if hour:
            out.append(f"{hour} {'çeyrek' if m == 45 else say(str(60 - m))} var")
    return out


_SEP = {"": " virgül ", "nokta": " nokta ", "bare": " "}


def _decimal(tok: Token, default: str, say: Say) -> list[str]:
    """``2,5`` → ``iki buçuk``, ``0,5`` → ``yarım``; the separator read three ways (``nokta``, ``virgül``, bare), and a
    point decimal that is a valid clock time read as one."""
    f = tok.fields
    integer, frac = f.get("integer", ""), f.get("fractional", "")
    if not integer.isdigit() or not frac.isdigit():
        return []
    unit = f.get("units")
    suffix = f.get("suffix", "")
    sep = f.get("sep", "")
    sign = f"{f['negative']} " if f.get("negative") else ""
    head = f"{f['symbol']} " if f.get("symbol") else ""
    tail = f" {unit}{suffix}" if unit else ""
    out = []
    if frac == "5":
        # The suffix sits on the unit when there is one, so it stays valid; otherwise it moves onto ``buçuk``.
        b = "buçuk" if unit or f.get("quantity") else _bucuk(suffix)
        if b is not None:
            if integer != "0":
                out.append(f"{head}{sign}{say(integer)} {b}{tail}")
            elif not sign and (unit or not suffix):
                out.append(f"{head}yarım{tail}")
    prefix = f"{head}{sign}{say(integer)}"
    current = prefix + _SEP.get(sep, " virgül ")
    if default.startswith(current):
        rest = default[len(current):]
        others = ["nokta", ""] if sep == "" else ["nokta", "", "bare"]
        if sep == "" and len(frac) == 2:
            others.append("bare")
        for other in others:
            if other != sep:
                out.append(prefix + _SEP[other] + rest)
    if sep and not sign and not head and not unit and not f.get("quantity") and len(frac) == 2:
        clock = Token("time", "", {"hours": integer, "minutes": frac, **({"suffix": suffix} if suffix else {})})
        bare = prefix + " " + default[len(current):] if default.startswith(current) else default
        out += _time(clock, bare, say)
    return out


def _money(tok: Token, default: str, say: Say) -> list[str]:
    f = tok.fields
    currency, suffix = f.get("currency", ""), f.get("suffix", "")
    if not f.get("integer", "").isdigit() or f.get("negative"):
        return []
    amount = say(f["integer"])
    out = []
    # The suffix is built again on the word that is said (``250 TL'ye`` → *iki yüz elli liraya*).
    def unit(word: str) -> str | None:
        return reinflect(word, suffix) if suffix else word
    if "minor" not in f:
        lira = unit("lira")
        if currency == "Türk lirası" and lira and "fractional" not in f:
            out.append(f"{amount} {lira}")
        return out
    major = "lira" if currency == "Türk lirası" else currency
    if currency == "Türk lirası" and f"{amount} lira " in default:
        out.append(default.replace(f"{amount} lira ", f"{amount} Türk lirası ", 1))
    whole = unit(major)
    if f["minor"] == "50" and whole:
        out.append(f"{amount} buçuk {whole}")
    return out


def _telephone(tok: Token, default: str, say: Say) -> list[str]:
    number = tok.fields.get("number", "")
    out = []
    if number.startswith("0") and default.startswith("sıfır "):
        out.append(default[len("sıfır "):])                     # beş yüz otuz iki … (the trunk 0 left out)
    prefix, rest = ("artı doksan ", number[3:]) if number.startswith("+90") else ("", number)
    digits = [c for c in rest if c.isdigit()]
    if digits:
        out.append(prefix + " ".join(say(c) for c in digits))   # digit by digit
    return out


def _date(tok: Token, default: str, say: Say) -> list[str]:
    """``28.10.2024`` → ``yirmi sekiz on iki bin yirmi dört``: a month written as digits is also read as a number
    (``04`` → ``sıfır dört`` · ``dört``)."""
    f = tok.fields
    digits, month = f.get("month_digits", ""), f.get("month", "")
    if not digits.isdigit() or not month or f" {month} " not in f" {default} ":
        return []
    readings = [say(digits.lstrip("0"))]
    if digits.startswith("0"):
        readings.insert(0, f"{say('0')} {readings[0]}")
    padded = f" {default} "
    return [padded.replace(f" {month} ", f" {r} ", 1).strip() for r in readings]


_RULES: dict[str, Callable[[Token, str, Say], list[str]]] = {
    "time": _time,
    "date": _date,
    "decimal": _decimal,
    "measure": _decimal,
    "percent": _decimal,
    "money": _money,
    "telephone": _telephone,
}


_NUMBER_STEMS = tuple(sorted((set(NUMBER_WORDS) | {"dörd"}) - {ZERO}, key=len, reverse=True))


def is_number_word(word: str) -> bool:
    """A number word, possibly inflected (``kırka``, ``dokuzu``, ``beşte``): what recognizer digits can stand for.
    ``sıfır`` is left out on purpose, it is matched against a leading ``0`` instead (see ``closest``)."""
    return word.startswith(_NUMBER_STEMS)


def alternatives(tok: Token, default: str, say: Say) -> list[str]:
    rule = _RULES.get(tok.cls)
    if rule is None:
        return []
    return [a for a in dict.fromkeys(rule(tok, default, say)) if a != default]

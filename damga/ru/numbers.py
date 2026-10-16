"""Russian number readings as finite-state transducers, digits → words, in every case and gender.

    21 (gen)             двадцати одного
    21 + тонна           двадцать одна тонна

ITN reads the inverses (any case, any gender).
"""
from __future__ import annotations

import functools

import pynini
from pynini.lib import pynutil

from ..core.rules import DIGIT, NONZERO_DIGIT
from .lexicon import (
    CASES,
    HUNDREDS,
    ONE,
    ORD_HUNDREDS,
    ORD_TEENS,
    ORD_TENS,
    ORD_THOUSANDS,
    ORD_UNITS,
    SCALES,
    TEENS,
    TENS,
    TWO,
    UNITS,
    ZERO,
    Noun,
    adjective,
)

ANY_DIGITS = pynini.closure(DIGIT, 1).optimize()
# Agreement classes of a whole number: 1, 21, 101 (one) · 2–4, 22–24 (few) · 0, 5–20, 25–30, 11–14 (many).
ONE_CLASS = pynini.difference(pynini.closure(DIGIT) + "1", pynini.closure(DIGIT) + "11").optimize()
FEW_CLASS = pynini.difference(pynini.closure(DIGIT) + pynini.union("2", "3", "4"),
                              pynini.closure(DIGIT) + "1" + pynini.union("2", "3", "4")).optimize()
MANY_CLASS = pynini.difference(ANY_DIGITS, pynini.union(ONE_CLASS, FEW_CLASS)).optimize()


def _i(case: str) -> int:
    return CASES.index(case)


def noun_form(noun: Noun, case: str, cls: str, few: str | None = None) -> str:
    """The form a counted noun takes after a number of agreement class ``cls`` (one/few/many/frac).  ``few`` is the
    nominative after 2–4 when it is not the genitive singular: an adjective in front takes the genitive plural
    (два квадратных километра)."""
    _, sg, pl = noun
    if cls == "frac":
        return sg[1]                                          # 3,5 процента: genitive singular
    if case in ("nom", "acc"):
        return {"one": sg[_i(case)], "few": few or sg[1], "many": pl[1]}[cls]
    return sg[_i(case)] if cls == "one" else pl[_i(case)]


@functools.cache
def _unit(case: str, gender: str) -> pynini.Fst:
    i = _i(case)
    pairs = [("1", ONE[gender][i]), ("2", TWO[gender][i])] + [(str(d), f[i]) for d, f in UNITS.items()]
    return pynini.union(*[pynini.cross(d, w) for d, w in pairs]).optimize()


@functools.cache
def _tens(case: str, gender: str) -> pynini.Fst:
    """10..99, two digits"""
    i = _i(case)
    teens = pynini.union(*[pynini.cross(str(n), f[i]) for n, f in TEENS.items()])
    round_tens = pynini.union(*[pynini.cross(str(n), f[i]) for n, f in TENS.items()])
    mixed = pynini.union(*[pynini.cross(str(n)[0], f[i]) for n, f in TENS.items()]) + pynutil.insert(" ") + _unit(case, gender)
    return pynini.union(teens, round_tens, mixed).optimize()


@functools.cache
def _hundreds(case: str, gender: str) -> pynini.Fst:
    """100..999, three digits"""
    i = _i(case)
    head = pynini.union(*[pynini.cross(str(n)[0], f[i]) for n, f in HUNDREDS.items()])
    tail = pynini.union(pynutil.delete("00"), pynutil.insert(" ") + pynutil.delete("0") + _unit(case, gender),
                        pynutil.insert(" ") + _tens(case, gender))
    return (head + tail).optimize()


@functools.cache
def group(case: str, gender: str) -> pynini.Fst:
    """1..999 written without leading zeros"""
    return pynini.union(_unit(case, gender), _tens(case, gender), _hundreds(case, gender)).optimize()


@functools.cache
def _group3(case: str, gender: str) -> pynini.Fst:
    """001..999, exactly three digits"""
    return pynini.union(pynutil.delete("00") + _unit(case, gender), pynutil.delete("0") + _tens(case, gender),
                        _hundreds(case, gender)).optimize()


def _counted(words: pynini.Fst, noun: Noun, case: str, digits_domain: pynini.Fst, few: str | None = None) -> pynini.Fst:
    """``words`` (digits → number words) followed by ``noun`` in the form the number asks for."""
    out = []
    for cls, acceptor in (("one", ONE_CLASS), ("few", FEW_CLASS), ("many", MANY_CLASS)):
        form = noun_form(noun, case, cls, few)
        out.append((pynini.intersect(digits_domain, acceptor) @ words) + pynutil.insert(" " + form))
    return pynini.union(*out).optimize()


@functools.cache
def cardinal(case: str = "nom", gender: str = "m") -> pynini.Fst:
    """Digits (no leading zeros, no separators) → words, up to 15 digits."""
    lead_digits = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)
    graphs = [group(case, gender), pynini.cross("0", ZERO[_i(case)])]
    for n_groups in range(2, len(SCALES) + 2):
        g: pynini.Fst | None = None
        for k in range(n_groups - 1, 0, -1):             # scale of each group, highest first
            exp, noun = SCALES[k - 1]
            ng = noun[0]
            if g is None:
                # the leading group: "1" alone is just the noun (тысяча, миллион), 2..999 agree with it
                one_alone = pynini.cross("1", noun_form(noun, case, "one"))
                counted = _counted(group(case, ng), noun, case, pynini.difference(lead_digits, "1"))
                g = pynini.union(one_alone, counted)
            else:
                three = pynini.closure(DIGIT, 3, 3)
                said = _counted(_group3(case, ng), noun, case, pynini.difference(three, "000"))
                g = g + pynini.union(pynutil.delete("000"), pynutil.insert(" ") + said)
        assert g is not None
        last = pynini.union(pynutil.delete("000"), pynutil.insert(" ") + _group3(case, gender))
        graphs.append(g + last)
    return pynini.union(*graphs).optimize()


@functools.cache
def counted(noun: Noun, case: str = "nom", few: str | None = None) -> pynini.Fst:
    """digits → number + the counted noun: 5 → пять рублей, 21 → двадцать один рубль, 2 → две тонны."""
    return _counted(cardinal(case, noun[0]), noun, case, ANY_DIGITS, few)


_WORDS = pynini.closure(pynini.union(*"абвгдеёжзийклмнопрстуфхцчшщъыьэюя "))


@functools.cache
def ordinal(case: str = "nom", gnum: str = "m") -> pynini.Fst:
    """digits → ordinal: 21 → двадцать первый, 1961 (prep) → тысяча девятьсот шестьдесят первом.  The words before the
    last stay in the nominative, as Russian says them."""
    last = {}
    for table, src in ((ORD_UNITS, UNITS), (ORD_TEENS, TEENS), (ORD_TENS, TENS), (ORD_HUNDREDS, HUNDREDS)):
        for n, nom in table.items():
            card = ONE["m"][0] if n == 1 else TWO["m"][0] if n == 2 else src[n][0]
            last[card] = adjective(nom, case, gnum)
    last_word = pynini.union(*[pynini.cross(c, o) for c, o in last.items()])
    to_ordinal = pynini.closure(_WORDS + " ", 0, 1) + last_word
    special = pynini.union(*[pynini.cross(str(n), adjective(nom, case, gnum)) for n, nom in ORD_THOUSANDS.items()])
    domain = pynini.difference(ANY_DIGITS, pynini.union(*[str(n) for n in ORD_THOUSANDS])).optimize()
    regular = domain @ cardinal("nom", "m") @ to_ordinal
    return pynini.union(regular, special).optimize()


_DENOMINATORS = {1: "десятый", 2: "сотый", 3: "тысячный", 4: "десятитысячный", 5: "стотысячный", 6: "миллионный"}


@functools.cache
def fraction(case: str = "nom") -> pynini.Fst:
    """``3,5`` → три целых и пять десятых, ``1,1`` → одна целая и одна десятая (a decimal point is accepted too)."""
    def part(word: str) -> list[tuple[pynini.Fst, str]]:
        forms = []
        for cls, acceptor in (("one", ONE_CLASS), ("few", FEW_CLASS), ("many", MANY_CLASS)):
            if cls == "one":
                form = adjective(word, case, "f")
            elif case in ("nom", "acc"):
                form = adjective(word, "gen", "pl")
            else:
                form = adjective(word, case, "pl")
            forms.append((acceptor, form))
        return forms

    integer_digits = pynini.union("0", NONZERO_DIGIT + pynini.closure(DIGIT))
    whole = []
    for acceptor, form in part("целый"):
        whole.append((pynini.intersect(integer_digits, acceptor) @ pynini.union(cardinal(case, "f")))
                     + pynutil.insert(" " + form))
    whole.append(pynini.cross("0", ZERO[_i(case)] + " " + (adjective("целый", "gen", "pl") if case in ("nom", "acc")
                                                            else adjective("целый", case, "pl"))))
    integer = pynini.union(*whole)
    fracs = []
    for k, denom in _DENOMINATORS.items():
        digits = pynini.closure(DIGIT, k, k)
        stripped = digits @ (pynutil.delete(pynini.closure("0")) + NONZERO_DIGIT + pynini.closure(DIGIT))
        for acceptor, form in part(denom):
            num = pynini.intersect(pynini.project(stripped, "output"), acceptor) @ cardinal(case, "f")
            fracs.append((stripped @ num) + pynutil.insert(" " + form))
    sep = pynini.cross(pynini.union(",", "."), " и ")
    return (integer + sep + pynini.union(*fracs)).optimize()


def strip_groups() -> pynini.Fst:
    """``14 191`` / ``1 000 000`` → digits; a number without spaces passes through."""
    head = pynini.union(NONZERO_DIGIT, NONZERO_DIGIT + DIGIT, NONZERO_DIGIT + DIGIT + DIGIT)
    return pynini.union(head + pynini.closure(pynutil.delete(" ") + DIGIT + DIGIT + DIGIT, 1),
                        "0", NONZERO_DIGIT + pynini.closure(DIGIT)).optimize()


def _roman(n: int) -> str:
    out = ""
    for value, letters in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += letters
            n -= value
    return out


# Centuries and similar are written in Roman numerals: XXI → 21.
ROMAN = pynini.union(*[pynini.cross(_roman(n), str(n)) for n in range(1, 40)]).optimize()
CENTURY_FORMS = {"век": ("nom", "m"), "века": ("gen", "m"), "веку": ("dat", "m"), "веком": ("ins", "m"),
                 "веке": ("prep", "m"), "веков": ("gen", "pl"), "векам": ("dat", "pl"), "веках": ("prep", "pl"),
                 "вв.": ("gen", "pl"), "в.": ("gen", "m")}


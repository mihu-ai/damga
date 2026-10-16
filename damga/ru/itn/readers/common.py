from __future__ import annotations

import functools

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT
from ...lexicon import CASES, GENDERS, GNUM, ONE, ORD_SUFFIX, TWO, UNITS, ZERO, adjective
from ...numbers import cardinal, fraction, ordinal


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


@functools.cache
def spoken_cardinal() -> pynini.Fst:
    """Words in any case and gender → digits: двадцати пяти → 25, двумястами → 200, одной тысячи → 1000."""
    plain = pynini.union(*[pynini.invert(cardinal(c, g)) for c in CASES for g in GENDERS]).optimize()
    # "тысячью", the other instrumental of "тысяча"
    sigma = pynini.closure(pynini.union(*"абвгдеёжзийклмнопрстуфхцчшщъыьэюя ")).optimize()
    tysyachyu = pynini.cdrewrite(pynini.cross("тысячей", "тысячью"), "", "", sigma)
    plain = pynini.union(plain, *[pynini.invert(cardinal("ins", g) @ tysyachyu) for g in GENDERS]).optimize()
    # "одна тысяча", "одного миллиона": the one before a leading scale word is said in formal speech
    ones = pynini.union(*{w for c in range(6) for w in (ONE["f"][c], ONE["m"][c])})
    scale_start = pynini.union("тысяч", "миллион", "миллиард", "триллион") + pynini.closure(
        pynini.union(*"абвгдеёжзийклмнопрстуфхцчшщъыьэюя "))
    with_one = pynutil.delete(ones + " ") + (scale_start @ plain)
    # тридцать одного рубля, сорок пяти: in speech only the last word may take the case
    colloquial = []
    for g in GENDERS:
        last = {f: forms[0] for forms in (ONE[g], TWO[g], *UNITS.values()) for f in forms[1:] if f != forms[0]}
        to_nom = pynini.union(*[pynini.cross(f, nom) for f, nom in last.items()])
        colloquial.append((sigma + " " + to_nom) @ pynini.invert(cardinal("nom", g)))
    return pynini.union(plain, with_one, *colloquial).optimize()


def written(group: bool = True) -> pynini.Fst:
    """Digits as Russian writes them: four digits together (1543), five and more in groups of three with a space
    (14 191, 1 000 000)."""
    if not group:
        return pynini.closure(DIGIT, 1).optimize()
    triple = pynutil.insert(" ") + DIGIT + DIGIT + DIGIT
    head = pynini.union(DIGIT, DIGIT + DIGIT, DIGIT + DIGIT + DIGIT)
    return pynini.union(pynini.closure(DIGIT, 1, 4), pynini.closure(DIGIT, 5) @ (head + pynini.closure(triple, 1))).optimize()


@functools.cache
def spoken_ordinal() -> pynini.Fst:
    """Ordinal words in any case and gender → digits with the written suffix: двадцать первого → 21-го."""
    out = []
    for gnum in GNUM:
        for i, case in enumerate(CASES):
            out.append(pynini.invert(ordinal(case, gnum)) + pynutil.insert("-" + ORD_SUFFIX[gnum][i]))
    return with_one_thousand(pynini.union(*out)).optimize()


def with_one_thousand(fst: pynini.Fst) -> pynini.Fst:
    """``одна тысяча девятьсот девяносто шестого`` read as ``тысяча девятьсот девяносто шестого``."""
    sigma = pynini.closure(pynini.union(*"абвгдеёжзийклмнопрстуфхцчшщъыьэюя "))
    return pynini.union(fst, pynutil.delete("одна ") + (("тысяча " + sigma) @ fst))


@functools.cache
def spoken_ordinal_digits() -> pynini.Fst:
    """Ordinal words in any case and gender → plain digits (a year, a day of the month)."""
    return with_one_thousand(pynini.union(*[pynini.invert(ordinal(c, g)) for c in CASES for g in GNUM])).optimize()


@functools.cache
def spoken_fraction() -> pynini.Fst:
    """три целых и пять десятых (any case, "и" may be left out) → 3,5; три запятая четырнадцать → 3,14."""
    sigma = pynini.closure(pynini.union(*"абвгдеёжзийклмнопрстуфхцчшщъыьэюя ,0123456789")).optimize()
    no_and = pynini.cdrewrite(pynini.cross(" и ", " "), "", "", sigma)
    exact = pynini.union(*[pynini.invert(fraction(c)) for c in CASES])
    loose = pynini.union(*[pynini.invert(fraction(c) @ no_and) for c in CASES])
    integer = spoken_cardinal() @ pynini.closure(DIGIT, 1)
    comma = integer + pynini.cross(" запятая ", ",") + integer
    # три тысячных → 0,003: a fraction said without its whole part
    bare = []
    for i, c in enumerate(CASES):
        whole = adjective("целый", "gen", "pl") if c in ("nom", "acc") else adjective("целый", c, "pl")
        bare.append((pynutil.insert(f"{ZERO[i]} {whole} и ") + sigma) @ pynini.invert(fraction(c)))
    return pynini.union(exact, loose, comma, *bare).optimize()

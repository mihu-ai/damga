from __future__ import annotations

import functools
import operator

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import BEFORE_NOUN, FEMININE
from ...numbers import DIGIT_WORD
from .cardinal import text

_UPPER = pynini.union(*"ABCDEFGHIJKLMNOPQRSTUVWXYZ")
# Countries that issue IBANs: "UE27 2020 2021 2022" is no IBAN.
_IBAN_COUNTRIES = """AD AE AL AT AZ BA BE BG BH BI BR BY CH CR CY CZ DE DJ DK DO EE EG ES FI FK FO FR GB GE GI GL GR GT HR HU
IE IL IQ IS IT JO KW KZ LB LC LI LT LU LV LY MC MD ME MK MN MR MT MU NI NL NO OM PK PL PS PT QA RO RS RU SA SC SD SE
SI SK SM SO ST SV TL TN TR UA VA VG XK YE""".split()
_MARK = pynutil.delete(pynini.union(FEMININE, BEFORE_NOUN)).ques     # the pre-hook marks a group before a noun


def _spell(chars: pynini.Fst, n_min: int, n_max: int) -> pynini.Fst:
    """``n_min`` to ``n_max`` of ``chars`` read one by one, a space between them."""
    return (chars + pynini.closure(pynutil.insert(" ") + chars, n_min - 1, n_max - 1)).optimize()


def _iban() -> pynini.Fst:
    """``ES91 2100 0418 4502 0005 1332`` / ``ES9121000418450200051332`` (15 to 34 characters, from a
    country that issues IBANs): letters spelled, digits read one by one, a comma between the groups of four."""
    char = pynini.union(_UPPER, DIGIT_WORD)
    country = pynini.union(*[pynini.cross(c, f"{c[0]} {c[1]}") for c in _IBAN_COUNTRIES])
    head = country + pynutil.insert(" ") + _spell(DIGIT_WORD, 2, 2)
    group = _spell(char, 4, 4)
    spaced, unspaced = [], []
    for full in range(2, 8):
        for last in range(1, 5):
            if 15 <= 4 + 4 * full + last <= 34:
                rest = [group] * full + [_spell(char, last, last)]
                spaced.append(functools.reduce(operator.add, [pynini.cross(" ", ", ") + _MARK + g for g in rest], head))
                unspaced.append(functools.reduce(operator.add, [pynutil.insert(", ") + g for g in rest], head))
    return pynini.union(*spaced, *unspaced).optimize()


def _keyword() -> pynini.Fst:
    """``Número de cuenta:``, ``nº de cuenta``, ``cuenta``, ``cuenta corriente n.º``, ``CCC:`` — kept as written."""
    number = pynini.union("Número", "número", "Nº", "nº", "N.º", "n.º", "Núm.", "núm.")
    account = pynini.union("Cuenta", "cuenta") + pynini.union("", " bancaria", " corriente")
    word = pynini.union(number + " de " + account, account, "CCC")
    colon = pynini.closure(":", 0, 1)
    after = pynini.closure(" " + pynini.union("Nº", "nº", "N.º", "n.º", "núm.") + colon, 0, 1)
    return (word + colon + after + " ").optimize()


def _account() -> pynini.Fst:
    """A domestic account number, digit by digit with a comma between the written groups: the CCC (4-4-2-10,
    spaced or not) or other groups of ten digits or more in all.  A number grouped in thousands is no account."""
    digits = lambda n_min, n_max: _spell(DIGIT_WORD, n_min, n_max)  # noqa: E731
    sep = pynini.union(pynini.cross(" ", ", "), pynini.cross("-", ", ")) + _MARK
    ccc_plain = digits(4, 4) + pynutil.insert(", ") + digits(4, 4) + pynutil.insert(", ") + digits(2, 2) \
        + pynutil.insert(", ") + digits(10, 10)
    plain = pynini.difference(pynini.project(digits(10, 34), "input"), DIGIT ** 20) @ digits(10, 34)
    grouped = digits(1, 20) + pynini.closure(sep + digits(1, 20), 1)
    long_enough = pynini.closure(pynini.closure(pynini.union(" ", "-"), 0, 1) + DIGIT, 10, 34)
    thousands = pynini.closure(DIGIT, 1, 3) + pynini.closure(pynini.union(" ", "-") + DIGIT ** 3, 1)
    grouped_ok = pynini.difference(long_enough, thousands)
    # the pre-hook marks may sit before any group: accept them in the input when checking the shape
    marked_ok = pynini.project(grouped, "input") @ pynini.cdrewrite(
        pynutil.delete(pynini.union(FEMININE, BEFORE_NOUN)), "", "", pynini.closure(
            pynini.union(DIGIT, " ", "-", FEMININE, BEFORE_NOUN))) @ grouped_ok
    grouped = pynini.project(marked_ok, "input") @ grouped
    return (_MARK + pynini.union(ccc_plain, plain, grouped)).optimize()


class BankReader(Rule):
    """Bank account numbers, read character by character with a pause (``, ``) between the written groups: an IBAN
    anywhere (``ES91 2100 …`` → ``E S nueve uno, dos uno cero cero, …``), a domestic number only after its keyword."""

    name = "bank"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(pynini.union(_iban(), _keyword() + _account()))).optimize()

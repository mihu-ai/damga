from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import CASE_MARKS, GENDER_MARKS
from .cardinal import _DIGIT_WORDS
from .common import text

UPPER = pynini.union(*"ABCDEFGHIJKLMNOPQRSTUVWXYZ").optimize()
CHAR = pynini.union(UPPER, DIGIT).optimize()
DIGIT_WORD = pynini.union(*[pynini.cross(d, w) for d, w in _DIGIT_WORDS.items()]).optimize()
SPELL = pynini.union(UPPER, DIGIT_WORD).optimize()
GROUP_SEP = pynini.cross(" ", ", ")
# the pre-hook may put a case or gender mark before a group of digits; a code is read the same whatever it says
MARKS = pynini.closure(pynutil.delete(pynini.union(*CASE_MARKS.values(), *GENDER_MARKS.values())), 0, 2)

# Keywords a bank code follows; the number after them is read digit by digit.  The words for an account (счёт)
# also stand before sums (счёт 10 000 рублей), so after them the number must be a long one.
CODES = ["р/с", "р/сч", "к/с", "к/сч", "БИК", "ИНН", "КПП", "ОГРН", "ОГРНИП", "ОКПО"]
ACCOUNTS = ["счёт", "счет", "расчётный счёт", "расчетный счет", "корр. счёт", "корр. счет", "корреспондентский счёт",
            "корреспондентский счет"]
CODE_MIN, ACCOUNT_MIN = 5, 10


def spelled(n_min: int, n_max: int | None = None) -> pynini.Fst:
    """``RU02`` → ``R U ноль два``: capitals one by one, digits as digit words, a space between."""
    more = pynutil.insert(" ") + SPELL
    if n_max is None:
        rest = pynini.closure(more, n_min - 1)
    elif n_max == 1:
        rest = pynini.accep("")                     # closure(…, 0, 0) would be unbounded
    else:
        rest = pynini.closure(more, n_min - 1, n_max - 1)
    return (SPELL + rest).optimize()


def at_least(n: int) -> pynini.Fst:
    """Input acceptor: ``n`` or more digits, spaces between them allowed."""
    sp = pynini.closure(" ")
    return (pynini.closure(sp + DIGIT, n, n) + pynini.closure(pynini.union(DIGIT, " "))).optimize()


def capitalized(word: str) -> pynini.Fst:
    return pynini.union(word, word[0].upper() + word[1:])


class BankReader(Rule):
    """Bank numbers read character by character, ``, `` between the written groups: an IBAN, spaced in fours or not
    (``RU02 0445 …`` → R U ноль два, ноль четыре четыре пять, …), or a number after a keyword (``БИК 044525225``).
    Without a keyword a number is read as a number."""

    name = "bank"
    kind = "read"

    def build(self, variants: bool = False):
        head = UPPER + pynutil.insert(" ") + UPPER + pynutil.insert(" ") + DIGIT_WORD + pynutil.insert(" ") + DIGIT_WORD
        four = spelled(4, 4)
        ibans = []
        for full in range(1, 8):
            for last in range(0, 4):
                if not 15 <= 4 + 4 * full + last <= 34:
                    continue
                spaced = head + pynini.closure(GROUP_SEP + MARKS + four, full, full)
                unspaced = head + pynini.closure(pynutil.insert(", ") + four, full, full)
                if last:
                    spaced = spaced + GROUP_SEP + MARKS + spelled(last, last)
                    unspaced = unspaced + pynutil.insert(", ") + spelled(last, last)
                ibans += [spaced, unspaced]
        iban = pynini.union(*ibans)

        group = pynini.closure(DIGIT, 1)
        number = (group + pynini.closure(" " + group)) @ (spelled(1) + pynini.closure(GROUP_SEP + spelled(1)))
        # БИК: 044525225, р/с № 40702…, ИНН No 7707083893: the colon stays, № is said
        numero = pynini.closure(" " + pynini.cross(pynini.union("№", "No", "No."), "номер"), 0, 1)
        tail = pynini.closure(":", 0, 1) + numero + pynini.union(" ", pynutil.insert(" ")) + MARKS
        codes = pynini.union(*[capitalized(k) for k in CODES])
        accounts = pynini.union(*[capitalized(k) for k in ACCOUNTS])
        keyed = pynini.union(codes + tail + (at_least(CODE_MIN) @ number),
                             accounts + tail + (at_least(ACCOUNT_MIN) @ number))
        return self.wrap(text(pynini.union(iban, keyed))).optimize()


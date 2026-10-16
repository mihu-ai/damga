from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import DIGIT_WORD
from .cardinal import text

UPPER = pynini.union(*"ABCDEFGHIJKLMNOPQRSTUVWXYZ").optimize()
CHAR = pynini.union(UPPER, DIGIT).optimize()
SPELL = pynini.union(UPPER, DIGIT @ DIGIT_WORD).optimize()
GROUP_SEP = pynini.cross(" ", ", ")

# Keywords a domestic account number follows; the bare word *compte* is common, so it needs a marker or a long number.
KEYWORDS = ["RIB", "clé RIB", "numéro de compte", "n° de compte", "code banque", "code guichet"]
MARKERS = [":", " :", " n°", " n° :"]


def spelled(min_len: int, max_len: int | None = None) -> pynini.Fst:
    """``FR76`` → ``F R sept six``: capitals one by one, digits as digit words, a space between."""
    more = pynutil.insert(" ") + SPELL
    rest = pynini.closure(more, min_len - 1) if max_len is None else pynini.closure(more, min_len - 1, max_len - 1)
    return (SPELL + rest).optimize()


def at_least(n: int) -> pynini.Fst:
    """Input acceptor: ``n`` or more characters besides spaces."""
    sp = pynini.closure(" ")
    return (pynini.closure(sp + CHAR, n, n) + pynini.closure(pynini.union(CHAR, " "))).optimize()


def capitalized(word: str) -> pynini.Fst:
    return pynini.union(word, word[0].upper() + word[1:])


class BankReader(Rule):
    """Bank numbers read character by character, ``, `` between the written groups: an IBAN (``FR76 3000 …`` →
    ``F R sept six, trois zéro zéro zéro, …``), or a domestic number after a keyword such as ``RIB :``; without a
    keyword a number is read as a number."""

    name = "bank"
    kind = "read"

    def build(self, variants: bool = False):
        head = UPPER + pynutil.insert(" ") + UPPER + pynutil.insert(" ") + (DIGIT @ DIGIT_WORD) + pynutil.insert(" ") + (
            DIGIT @ DIGIT_WORD)
        four = spelled(4, 4)
        ibans = []
        for full in range(1, 8):
            for last in range(0, 5):
                if not 15 <= 4 + 4 * full + last <= 34:
                    continue
                spaced = head + pynini.closure(GROUP_SEP + four, full, full)
                unspaced = head + pynini.closure(pynutil.insert(", ") + four, full, full)
                if last:
                    spaced += GROUP_SEP + spelled(last, last)
                    unspaced += pynutil.insert(", ") + spelled(last, last)
                ibans += [spaced, unspaced]
        # The BBAN carries digits: a long capitalised word with a number in it is not an IBAN.
        with_digit = UPPER + UPPER + DIGIT + DIGIT + pynini.closure(pynini.union(CHAR, " ")) + DIGIT + pynini.closure(
            pynini.union(CHAR, " "))
        iban = with_digit @ pynini.union(*ibans)

        group = pynini.closure(CHAR) + DIGIT + pynini.closure(CHAR)
        number_in = DIGIT + pynini.closure(CHAR) + pynini.closure(" " + group)
        number = number_in @ (spelled(1) + pynini.closure(GROUP_SEP + spelled(1)))
        keyword = pynini.union(*[capitalized(k) for k in KEYWORDS])
        marker = pynini.union(*MARKERS)
        compte = capitalized("compte")
        domestic = pynini.union(
            keyword + pynini.closure(marker, 0, 1) + " " + (at_least(2) @ number),
            compte + marker + " " + (at_least(2) @ number),
            compte + " " + (at_least(8) @ number),
        )
        return self.wrap(text(pynini.union(iban, domestic))).optimize()

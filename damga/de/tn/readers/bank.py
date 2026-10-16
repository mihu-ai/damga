from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import DIGIT_WORD
from .cardinal import text

UPPER = pynini.union(*"ABCDEFGHIJKLMNOPQRSTUVWXYZ").optimize()
PAUSE = ", "                       # between the written groups


def _count(symbol: pynini.Fst, low: int, high: int, other: pynini.Fst) -> pynini.Fst:
    """Strings with ``low`` to ``high`` ``symbol``s among any number of ``other``s."""
    rest = pynini.closure(other)
    return (rest + pynini.closure(symbol + rest, low, high)).optimize()


def _spelled(chars: pynini.Fst) -> pynini.Fst:
    """``B2`` → ``B zwei``: one word for each character, a letter as itself, a digit as its digit word."""
    char = pynini.union(UPPER, DIGIT_WORD)
    return chars @ (char + pynini.closure(pynutil.insert(" ") + char))


def iban() -> pynini.Fst:
    """``DE89 3704 0044 …`` → ``D E acht neun, drei sieben null vier, …``.  At least six digits after the check
    digits are required, so a line of capitals stays words."""
    alnum = pynini.union(UPPER, DIGIT)
    head = _spelled(UPPER + UPPER + DIGIT + DIGIT)
    four = _spelled(pynini.closure(alnum, 4, 4))
    short = _spelled(pynini.closure(alnum, 1, 3))
    gap = pynini.cross(" ", PAUSE)
    spaced = head + pynini.closure(gap + four, 2, 7) + pynini.closure(gap + short, 0, 1)
    unspaced = head + pynini.closure(pynutil.insert(PAUSE) + four, 2, 7) + pynini.closure(pynutil.insert(PAUSE) + short, 0, 1)
    # 15 to 34 characters, at least six of them digits after the check digits
    chars = _count(alnum, 15, 34, pynini.accep(" "))
    digits = UPPER + UPPER + DIGIT + DIGIT + _count(DIGIT, 6, 30, pynini.union(UPPER, " "))
    shape = pynini.intersect(chars, digits).optimize()
    return (shape @ pynini.union(spaced, unspaced)).optimize()


def domestic() -> pynini.Fst:
    """``BLZ 370 400 44`` → ``BLZ drei sieben null, …``: digit by digit, only after a keyword.  After a bare
    ``Konto`` only 6 to 10 unbroken digits count ("auf dem Konto 500 Euro" is an amount)."""
    digits = DIGIT_WORD + pynini.closure(pynutil.insert(" ") + DIGIT_WORD)
    groups = pynini.closure(DIGIT, 1) + pynini.closure(" " + pynini.closure(DIGIT, 1))
    read = digits + pynini.closure(pynini.cross(" ", PAUSE) + digits)

    def grouped(low: int, high: int) -> pynini.Fst:
        return pynini.intersect(groups, _count(DIGIT, low, high, pynini.accep(" "))).optimize() @ read

    nr = pynini.cross("Nr.", "Nummer")
    colon = pynini.closure(":", 0, 1)
    between = pynini.union(colon + " ", " " + nr + colon + " ")
    account_word = pynini.union("Kontonummer", pynini.cross(pynini.union("Konto-Nr.", "Kto.-Nr."), "Kontonummer"))
    account = pynini.union(account_word + between + grouped(3, 10),
                           pynini.accep("Konto") + " " + nr + colon + " " + grouped(3, 10),
                           pynini.accep("Konto") + colon + " " + (pynini.closure(DIGIT, 6, 10) @ digits))
    blz = pynini.union("BLZ", "Bankleitzahl") + between + grouped(8, 8)
    return pynini.union(account, blz).optimize()


class BankReader(Rule):
    """International bank account numbers (IBAN) and domestic bank numbers after their keyword (BLZ, Kontonummer),
    read character by character with a pause between the written groups."""

    name = "bank"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(pynini.union(iban(), domestic()))).optimize()

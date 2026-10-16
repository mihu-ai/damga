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
    """``B2`` → ``B two``: one word for each character, a letter as itself, a digit as its digit word."""
    char = pynini.union(UPPER, DIGIT_WORD)
    return chars @ (char + pynini.closure(pynutil.insert(" ") + char))


def iban() -> pynini.Fst:
    """``GB33 BUKB 2020 …`` → ``G B three three, B U K B, two zero two zero, …``.  At least six digits after the
    check digits are required, so a line of capitals stays words."""
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


def _keyword(*phrases: str) -> pynini.Fst:
    """``account number`` also as ``Account number``, ``Account Number`` and ``ACCOUNT NUMBER``."""
    forms = set()
    for p in phrases:
        forms |= {p, p[0].upper() + p[1:], " ".join(w[0].upper() + w[1:] for w in p.split()), p.upper()}
    return pynini.union(*[pynini.escape(f) for f in sorted(forms)]).optimize()


def domestic() -> pynini.Fst:
    """``Sort code 12-34-56`` → ``Sort code one two, three four, five six``: digit by digit, only after a keyword."""
    digits = DIGIT_WORD + pynini.closure(pynutil.insert(" ") + DIGIT_WORD)
    sep = pynini.union(" ", "-")
    grouped = pynini.intersect(pynini.closure(DIGIT, 1) + pynini.closure(sep + pynini.closure(DIGIT, 1)),
                               _count(DIGIT, 6, 17, sep)).optimize()
    account_number = grouped @ (digits + pynini.closure(pynini.cross(sep, PAUSE) + digits))
    sort_code = (pynini.closure(DIGIT, 2, 2) + pynini.closure("-" + pynini.closure(DIGIT, 2, 2), 2, 2)) @ (
        digits + pynini.closure(pynini.cross("-", PAUSE) + digits))
    routing_number = pynini.closure(DIGIT, 9, 9) @ digits

    number_sign = pynini.union(pynini.cross("#", "number"), "No.", "no.")
    # "account number: 1234", "acct #1234", "acct no. 1234"
    between = pynini.union(
        pynini.closure(":", 0, 1) + " ",
        " " + number_sign + pynini.closure(":", 0, 1) + " ",
        " " + pynini.cross("#", "number "),
    )
    account = _keyword("account number", "account no.", "acct") + between + account_number
    sort = _keyword("sort code") + between + sort_code
    routing = _keyword("routing number") + between + routing_number
    aba = pynini.accep("ABA") + between + routing_number
    return pynini.union(account, sort, routing, aba).optimize()


class BankReader(Rule):
    """International bank account numbers (IBAN) and domestic bank numbers after their keyword, read character by
    character with a pause between the written groups."""

    name = "bank"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(pynini.union(iban(), domestic()))).optimize()

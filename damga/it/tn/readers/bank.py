from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import DIGIT_WORD
from ..normalizer import IBAN_COUNTRIES
from .cardinal import text

UPPER = pynini.union(*"ABCDEFGHIJKLMNOPQRSTUVWXYZ").optimize()
# a letter is spelled as itself (X), a digit is its word (zero, uno, due …)
CHAR_SAID = pynini.union(UPPER, DIGIT_WORD).optimize()
ALNUM = pynini.union(UPPER, DIGIT).optimize()


def said(n: int) -> pynini.Fst:
    """``n`` letters or digits, said one by one with a space between."""
    return (CHAR_SAID + pynini.closure(pynutil.insert(" ") + CHAR_SAID, n - 1, n - 1)).optimize()


def grouped(sizes: list[int], separator: str) -> pynini.Fst:
    """Groups of the given sizes written with ``separator`` between them, said with ``, `` between them."""
    out = said(sizes[0])
    for size in sizes[1:]:
        out = out + pynini.cross(separator, ", ") + said(size)
    return out.optimize()


class IbanReader(Rule):
    """``IT60 X054 2811 …`` → ``I T sei zero, X zero cinque quattro, due otto uno uno, …``: every character said apart,
    in groups of four even when written unspaced.  15 to 34 characters."""

    name = "iban"
    kind = "read"

    def build(self, variants: bool = False):
        # the head is the country code and the check digits; any other pair of capitals is no IBAN (UE28 …)
        head = (pynini.union(*IBAN_COUNTRIES) + DIGIT + DIGIT) @ (said(2) + pynutil.insert(" ") + said(2))
        branches = []
        for full in range(2, 8):
            for last in range(1, 5):
                if not 15 <= 4 + 4 * full + last <= 34:
                    continue
                sizes = [4] * full + [last]
                for separator in (" ", ""):
                    branches.append(head + pynini.cross(separator, ", ") + grouped(sizes, separator))
        return self.wrap(text(pynini.union(*branches))).optimize()


def _keyword(*words: str) -> pynini.Fst:
    return pynini.union(*[pynini.union(w, w[0].upper() + w[1:]) for w in words])


class BankAccountReader(Rule):
    """Italian bank coordinates after their name (``ABI``, ``CAB``, ``CIN``, ``conto``, ``c/c`` …), every character
    said apart: ``ABI 05428`` → ``ABI zero cinque quattro due otto``.  Without the name the number is a number."""

    name = "bank_account"
    kind = "read"

    def build(self, variants: bool = False):
        # ABI: 05428, conto n. 123… (n. is "numero" after the pre-hook), c/c n°123…
        sep = (pynini.closure(":", 0, 1) + " "
               + pynini.closure(pynini.union("numero ", "Numero ", "nr. ", "n° ", "N° ", "n°", "N°"), 0, 1))
        abi_cab = pynini.union("ABI", "CAB") + sep + (pynini.closure(DIGIT, 5, 5) @ said(5))
        cin = pynini.accep("CIN") + sep + UPPER
        # an account number holds a digit; letters in it are spelled
        letters_only = pynini.closure(UPPER, 1)
        loose = pynini.difference(pynini.closure(ALNUM, 6, 12), letters_only) @ pynini.union(
            *[said(n) for n in range(6, 13)])
        strict = pynini.difference(pynini.closure(ALNUM, 12, 12), letters_only) @ said(12)
        spaced = grouped([4, 4, 4], " ")
        loose, strict = pynini.union(loose, spaced), pynini.union(strict, spaced)
        account = pynini.union(
            _keyword("conto corrente", "numero di conto", "c/c", "C/C") + sep + loose,
            # plain "conto" is said digit by digit only for a full twelve-character account number
            _keyword("conto") + sep + strict,
        )
        return self.wrap(text(pynini.union(abi_cab, cin, account))).optimize()

from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL, DIGITS_SPOKEN
from .cardinal import text

# what is written before a phone number; any number shape after it is a phone number
KEYWORDS = ("tel.:", "tel.", "tel:", "tel", "telefono:", "telefono", "cellulare:", "cellulare", "cell.:", "cell.",
            "cell", "fax:", "fax", "chiama lo", "chiama il", "chiamare lo", "chiamare il", "numero verde",
            "numero verde:")


def _digits(least: int, most: int | None = None) -> pynini.Fst:
    """``least`` to ``most`` digits with separators around and between them: a digit count over a written form."""
    gap = pynini.closure(pynini.union(" ", "-", "/", ".", "+"))
    return (gap + pynini.closure(DIGIT + gap, least, most if most is not None else least)).optimize()


class TelephoneReader(Rule):
    """Italian phone numbers, said digit by digit with ``, `` between the written groups: ``06 1234 5678`` → ``zero
    sei, uno due tre quattro, cinque sei sette otto``.  On their own a landline (``0…``, at least eight digits) and a
    ten-digit mobile (``3…``) are told by their shape, an international number by its ``+`` / ``00``; after
    ``Tel.``, ``Fax``, ``numero verde`` … any number of six digits or more is one."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        said = pynini.closure(DIGIT, 1) @ DIGITS_SPOKEN

        def number(seps: list[str]) -> pynini.Fst:
            sep = pynini.cross(pynini.union(*seps), ", ")
            return said + pynini.closure(sep + said)

        loose_seps, strict_seps = [" ", "-", "/", "."], [" ", "-"]
        # +39 333 …, +39-06-…, 0039 06 …, +393331234567: the country code, then the national number
        code = pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 2)
        after_code = pynini.cross(pynini.union(" ", "-"), ", ")
        country = pynini.union(
            pynini.cross("+", "più ") + (code @ CARDINAL) + after_code,
            pynini.cross("00", "zero zero ") + (code @ CARDINAL) + after_code,
            pynini.cross("+39", "più trentanove, ") + pynini.union(pynini.cross(pynini.union(" ", "-"), ""), ""),
        )

        def shaped(seps: list[str], shape: pynini.Fst) -> pynini.Fst:
            return (shape @ number(seps)).optimize()

        def groups(first: pynini.Fst, rest: pynini.Fst) -> pynini.Fst:
            return first + pynini.closure(pynini.union(*strict_seps).ques + rest)

        # a landline: 0 and its area code (never 00), at least eight digits; a mobile: 3 and nine more digits
        area = pynini.accep("0") + pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 2)
        landline = pynini.intersect(groups(area, pynini.closure(DIGIT, 1)), _digits(8, 11))
        mobile = pynini.intersect(groups(pynini.accep("3") + DIGIT + DIGIT, pynini.closure(DIGIT, 1)), _digits(10))
        national = shaped(strict_seps, pynini.union(landline, mobile))
        # (06) 1234 5678, +39 (06) 1234 5678: the area code in brackets, said as any other group
        bracketed = (pynutil.delete("(") + area + pynutil.delete(")") + pynini.closure(
            pynini.union(*strict_seps, DIGIT))) @ landline @ number(strict_seps)
        bracketed = bracketed.optimize()
        national = pynini.union(national, bracketed)
        bare_groups = pynini.closure(DIGIT, 1) + pynini.closure(pynini.union(*strict_seps) + pynini.closure(DIGIT, 1))
        abroad = shaped(strict_seps, pynini.intersect(bare_groups, _digits(6, 13)))
        alone = pynini.union(national, country + abroad, country + bracketed)

        loose = pynini.closure(DIGIT, 1) + pynini.closure(pynini.union(*loose_seps) + pynini.closure(DIGIT, 1))
        any_number = shaped(loose_seps, pynini.intersect(loose, _digits(6, 13)))
        keyword = pynini.union(*[pynini.union(k, k[0].upper() + k[1:]) for k in KEYWORDS]) + " "
        named = keyword + pynini.union(any_number, country + any_number)
        return self.wrap(text(pynini.union(alone, named))).optimize()

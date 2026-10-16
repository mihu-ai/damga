from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import DIGITS
from ...numbers import COUNTRY_CODES
from .cardinal import spoken_cardinal, text

D = DIGIT
TWO_TO_NINE = pynini.difference(DIGIT, pynini.union("0", "1")).optimize()
ANY = pynini.closure(pynini.union(DIGIT, " ", "-")).optimize()
# Ten bare North American digits are a number only after one of these words.
KEYWORDS = ("call", "call me at", "call me on", "phone", "number", "number is", "dial", "text", "text me at",
            "reach me at")
TOLL_FREE = ("800", "888", "877", "866", "855", "844", "833")


def _shape(*sizes: int, sep: str = " ") -> pynini.Fst:
    """Digits → groups of ``sizes`` joined by ``sep``: ``_shape(3, 4, 4)`` writes ``020 7946 0958``."""
    out = pynini.closure(D, sizes[0], sizes[0])
    for size in sizes[1:]:
        out = out + pynutil.insert(sep) + pynini.closure(D, size, size)
    return out.optimize()


def spoken_digits() -> pynini.Fst:
    """``two oh double five triple nine`` → ``2055999``."""
    words = [(w, d) for w, d in DIGITS] + [("zero", "0"), ("oh", "0"), ("o", "0"), ("nought", "0")]
    one = pynini.union(*[pynini.cross(w, d) for w, d in words])
    many = pynini.union(*[pynini.cross(f"{times} {w}", d * n) for times, n in (("double", 2), ("triple", 3))
                          for w, d in words])
    unit = pynini.union(one, many)
    return (unit + pynini.closure(pynutil.delete(" ") + unit)).optimize()


def digit_run(min_units: int = 8) -> pynini.Fst:
    """A long run of digit words, kept as said.  Weighted so a phone number is never cut out of the middle of a
    longer run."""
    words = [w for w, _ in DIGITS] + ["zero", "oh", "o", "nought"]
    unit = pynini.union(*words, *[f"{t} {w}" for t in ("double", "triple") for w in words])
    return (unit + pynini.closure(" " + unit, min_units - 1)).optimize()


def uk_shape() -> pynini.Fst:
    """An 11-digit UK number with its trunk 0, grouped as printed: ``020 7946 0958``, ``07911 123456``."""
    london_like = "02" + D                                         # 020, 023, 024, 028, 029
    mobile = pynini.accep("07")
    four = pynini.union("011" + D, "01" + D + "1", pynini.union("03", "08", "09") + D + D).optimize()
    eleven = pynini.closure(D, 11, 11)
    rest = pynini.difference(eleven, pynini.union(london_like, mobile, four) + pynini.closure(D)).optimize()
    return pynini.union(
        (london_like + pynini.closure(D, 8, 8)) @ _shape(3, 4, 4),
        (mobile + pynini.closure(D, 9, 9)) @ _shape(5, 6),
        (four + pynini.closure(D, 7, 7)) @ _shape(4, 3, 4),
        rest @ _shape(5, 6),
    ).optimize()


class TelephoneReader(Rule):
    """Spoken phone numbers, SSNs and IP addresses: ``plus four four two zero seven …`` → ``+44 20 7946 0958``.

    Bare North American digits need a keyword (*call*, *number*); a UK number is anchored by its trunk zero, an
    international one by *plus*."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        digits = spoken_digits()
        sp = pynini.accep(" ")

        def length(low: int, high: int) -> pynini.Fst:
            return (digits @ pynini.closure(D, low, high)).optimize()

        # North American area and exchange start with 2 to 9
        area = pynini.union(length(3, 3) @ (TWO_TO_NINE + D + D), pynini.cross("eight hundred", "800"))
        seven = digits @ (TWO_TO_NINE + pynini.closure(D, 6, 6))
        nanp = (area + pynutil.delete(" ") + seven) @ _shape(3, 3, 4, sep="-")
        toll_free = (area @ pynini.union(*TOLL_FREE) + pynutil.delete(" ") + seven) @ _shape(3, 3, 4, sep="-")

        uk = uk_shape()
        uk_domestic = length(11, 11) @ ("0" + pynini.closure(D)) @ uk
        # the national part after +44 is the domestic number without its trunk 0
        uk_national = (length(10, 10) @ (pynini.difference(D, "0") + pynini.closure(D))
                       @ (pynutil.insert("0") + pynini.closure(D)) @ uk @ (pynutil.delete("0") + ANY))
        france = length(9, 9) @ (pynini.difference(D, "0") + pynini.closure(D)) @ _shape(1, 2, 2, 2, 2)

        cardinal = spoken_cardinal()

        def code(*codes: str) -> pynini.Fst:
            allowed = pynini.union(*codes)
            return pynini.union(digits @ allowed, cardinal @ allowed).optimize()

        others = tuple(c for c in COUNTRY_CODES if c not in ("1", "44", "33"))
        # "double oh four four" (0044) is written as +
        plus = pynini.union(pynini.cross("plus ", "+"),
                            pynini.cross(pynini.union("double oh", "double zero", "oh oh", "zero zero") + sp, "+"))
        international = pynini.union(
            plus + code("1") + sp + nanp,
            plus + code("44") + sp + pynini.union(uk_national, pynutil.add_weight(length(7, 9), 0.1)),
            plus + code("33") + sp + pynini.union(france, pynutil.add_weight(length(7, 12), 0.1)),
            plus + code(*others) + sp + length(7, 12),
        )
        keyword = pynini.union(*KEYWORDS) + sp
        ssn = (pynini.union("ssn", "social security number") + pynini.closure(" is", 0, 1) + sp
               + (length(9, 9) @ _shape(3, 2, 4, sep="-")))
        # IP address: four numbers up to 255, each said digit by digit or as a number
        hundreds = (digits @ pynini.union(*"12")) + pynutil.delete(" ") + (cardinal @ (pynini.union(*"123456789") + D))
        byte = pynini.union(*[str(n) for n in range(256)])
        group = pynini.union(length(1, 3), cardinal, hundreds) @ byte
        ip = group + pynini.closure(pynini.cross(" dot ", ".") + group, 3, 3)
        graph = pynini.union(
            ssn,
            ip,
            international,
            uk_domestic,
            pynutil.add_weight(length(10, 10) @ ("0" + pynini.closure(D)) @ _shape(5, 5), 0.1),
            pynini.cross("one ", "1-") + toll_free,
            keyword + pynini.closure(pynini.cross("one ", "1-"), 0, 1) + nanp,
            pynutil.add_weight(digit_run(), 3.0),
        )
        return self.wrap(text(graph)).optimize()

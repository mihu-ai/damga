from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import DIGIT_WORD
from .cardinal import spoken_cardinal, text

# area codes of two digits: Milano, Roma (no longer area code starts with 02 or 06)
TWO_DIGIT_AREAS = ("02", "06")


class TelephoneReader(Rule):
    """Italian phone numbers said digit by digit, in pairs or in hundreds: ``zero sei uno due tre quattro cinque sei
    sette otto`` → ``06 12345678``, ``più trentanove …`` → ``+39 …``.

    A landline is told by its leading ``zero`` and eight to eleven digits, a mobile by its leading ``tre`` and ten
    digits; anything else needs ``più`` / ``zero zero`` or ``numero verde`` before it.  Groups may be apart by commas."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        digit = pynini.invert(DIGIT_WORD)
        number = spoken_cardinal()
        group = pynini.union(
            digit,
            number @ (NONZERO_DIGIT + DIGIT),
            number @ (NONZERO_DIGIT + DIGIT + DIGIT),
        ).optimize()
        glue = pynutil.delete(pynini.union(" ", ", "))
        said = (group + pynini.closure(glue + group)).optimize()

        def spaced(*sizes: int) -> pynini.Fst:
            out = pynini.closure(DIGIT, sizes[0], sizes[0])
            for size in sizes[1:]:
                out = out + pynutil.insert(" ") + pynini.closure(DIGIT, size, size)
            return out

        # 0 and a non-zero digit, eight to eleven digits; never the count zero uno due tre …
        counting = pynini.union(*["0123456789"[:n] for n in range(8, 11)])
        landline_digits = pynini.difference("0" + NONZERO_DIGIT + pynini.closure(DIGIT, 6, 9), counting)
        two = pynini.union(*TWO_DIGIT_AREAS)
        landline_fmt = pynini.union(
            two + pynutil.insert(" ") + pynini.closure(DIGIT, 1),
            pynini.difference("0" + NONZERO_DIGIT, two) + pynini.closure(DIGIT, 1),
        )
        landline = (said @ landline_digits @ landline_fmt).optimize()
        mobile_fmt = ("3" + DIGIT + DIGIT) @ spaced(3) + pynutil.insert(" ") + spaced(3, 4)
        mobile = (said @ mobile_fmt).optimize()
        # without an anchor a mobile must start with the digit word tre: "trenta quaranta cinquanta …" is a list
        bare_mobile = ((pynini.accep("tre") + pynini.union(" ", ", ") + pynini.project(said, "input"))
                       @ mobile).optimize()

        to_space = pynini.cross(pynini.union(" ", ", "), " ")
        italy = pynini.union(
            pynini.cross(pynini.union("più trentanove", "più tre nove", "zero zero trentanove", "zero zero tre nove"),
                         "+39"),
        ) + to_space + pynini.union(landline, mobile)
        # any other country code said as one number: più quarantaquattro venti …, più uno …
        code = number @ (NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2))
        other = pynini.cross("più ", "+") + code + to_space + (said @ pynini.closure(DIGIT, 7, 12))
        other = pynini.difference(pynini.project(other, "input"), "più tre nove " + pynini.project(said, "input")) @ other
        toll_free = pynini.accep("numero verde ") + (said @ (("80" + DIGIT) @ spaced(3) + pynutil.insert(" ")
                                                             + spaced(3, 3)))
        graph = pynini.union(
            landline,
            bare_mobile,
            italy,
            pynutil.add_weight(other, 0.1),
            toll_free,
        )
        return self.wrap(text(graph)).optimize()

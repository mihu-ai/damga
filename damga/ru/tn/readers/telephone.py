from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import CASE_MARKS, GENDER_MARKS, ZERO
from ...numbers import NONZERO_DIGIT, cardinal
from .bank import MARKS, capitalized
from .common import text

# Words a telephone number follows; after them a local number without a code is a telephone number too.
KEYWORDS = ["тел.", "тел", "телефон", "телефону", "телефона", "т.", "моб.", "моб", "мобильный", "факс", "тел./факс",
            "звоните", "звоните по номеру", "звонить по номеру", "по номеру", "номер телефона"]
LOCAL_MIN = 5      # a local number has at least this many digits (2-34-56), fewer is a range or a score
# what stands between the digits of a number: separators, parentheses, the pre-hook's marks
NOT_DIGIT = pynini.union(*" +-()", *CASE_MARKS.values(), *GENDER_MARKS.values()).optimize()


def digits(n_min: int, n_max: int) -> pynini.Fst:
    return pynini.closure(DIGIT, n_min, n_max)


def with_digits(n_min: int, n_max: int | None = None) -> pynini.Fst:
    """Input filter: ``n_min`` to ``n_max`` digits (no limit: ``None``), anything else around them."""
    other = pynini.closure(NOT_DIGIT)
    more = pynini.closure(DIGIT + other, n_min) if n_max is None else pynini.closure(DIGIT + other, n_min, n_max)
    return (other + more).optimize()


def group_reading() -> pynini.Fst:
    """One written group as a number in the nominative: ``123`` → сто двадцать три; a leading zero is said
    (``05`` → ноль пять, ``050`` → ноль пятьдесят, ``00`` → ноль ноль); four digits are two pairs."""
    zero = pynini.cross("0", ZERO[0])
    rest = (NONZERO_DIGIT + pynini.closure(DIGIT)) @ cardinal("nom", "m")
    zeros = zero + pynini.closure(pynutil.insert(" ") + zero)
    one = pynini.union(rest, zeros, zeros + pynutil.insert(" ") + rest)
    two = pynini.closure(DIGIT, 2, 2) @ one
    # four digits are said as two pairs: 3843 → тридцать восемь сорок три
    pairs = two + pynutil.insert(" ") + two
    short = pynini.union(pynini.closure(DIGIT, 1, 3), pynini.closure(DIGIT, 5)) @ one
    return pynini.union(short, pairs).optimize()


class TelephoneReader(Rule):
    """A Russian telephone number read in its written groups, each a number in the nominative, ``, `` between
    them: ``8 800 555-35-35`` → восемь, восемьсот, пятьсот пятьдесят пять, тридцать пять, тридцать пять.  After a
    keyword (``тел.``, ``телефон`` …) a local number counts too.

    Without a keyword only a number with a ``+7`` or ``8`` code and ten digits after it counts, so ranges
    (``3-5``), scores (``2-1``) and plain numbers stay with their own readings."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        g = group_reading()
        comma = pynutil.insert(", ")
        sep = pynini.union(pynutil.delete("-"), pynutil.delete(" "))

        def grp(n_min: int, n_max: int) -> pynini.Fst:
            return MARKS + (digits(n_min, n_max) @ g)

        prefix = pynini.union(pynini.cross("+7", "плюс семь"), pynini.cross("8", "восемь"))
        # the code, in parentheses or not: (495), ( 495 ), 495
        paren = (pynutil.delete("(") + pynini.closure(pynutil.delete(" "), 0, 1) + grp(3, 5)
                 + pynini.closure(pynutil.delete(" "), 0, 1) + pynutil.delete(")"))
        code = pynini.union(
            pynini.closure(pynutil.delete(" "), 0, 1) + comma + paren + pynini.closure(pynutil.delete(" "), 0, 1),
            sep + comma + grp(3, 5) + sep)
        def run(n: int) -> pynini.Fst:
            return digits(n, n) @ g

        # the subscriber number: two to four groups of one to four digits, or the digits run together (1234567 is
        # said 123-45-67, 123456 is said 12-34-56)
        local = pynini.union(grp(1, 4) + pynini.closure(sep + comma + grp(1, 4), 1, 3),
                             MARKS + run(3) + comma + run(2) + comma + run(2),
                             MARKS + run(2) + comma + run(2) + comma + run(2))
        spaced = MARKS + prefix + code + comma + local
        spaced = (with_digits(11, 11) @ spaced).optimize()
        # 00 and the country code, dialled instead of "+": 007 495 123-45-67 → ноль ноль семь, …
        country = pynini.accep("00") + NONZERO_DIGIT + digits(0, 2)
        abroad = MARKS + (country @ g) + pynini.union(code, sep + comma + grp(2, 5) + sep) + comma + local
        abroad = (with_digits(11, 15) @ abroad).optimize()
        spaced = pynini.union(spaced, abroad)

        run_together = (MARKS + pynini.union(pynini.cross("+7", "плюс семь"), pynini.cross("8", "восемь"),
                                             pynini.cross("7", "семь"))
                        + comma + run(3) + comma + run(3) + comma + run(2) + comma + run(2))
        full = pynini.union(spaced, run_together)

        # after a keyword: the full number, or a local one of three or four groups (123-45-67, 2-34-56)
        short = grp(1, 3) + pynini.closure(sep + comma + grp(2, 3), 2, 3)
        short = (with_digits(LOCAL_MIN) @ short).optimize()
        keywords = pynini.union(*[capitalized(k) for k in KEYWORDS])
        tail = pynini.closure(":", 0, 1) + " "
        keyed = keywords + tail + pynini.union(full, short)
        return self.wrap(text(pynini.union(full, keyed))).optimize()

from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule, drop_space
from ...numbers import DIGIT_WORD
from .cardinal import spoken_cardinal, text

DIGIT_SAID = pynini.union(pynini.invert(DIGIT_WORD), pynini.cross("une", "1")).optimize()   # zéro … neuf → 0 … 9
GAP = drop_space


def pairs_from_right(n: int) -> pynini.Fst:
    """``n`` digits → pairs, a single digit first when ``n`` is odd: ``123456789`` → ``1 23 45 67 89``."""
    pair = DIGIT + DIGIT
    head = DIGIT if n % 2 else pair
    return (head + pynini.closure(pynutil.insert(" ") + pair, (n - 1) // 2, (n - 1) // 2)).optimize()


class TelephoneReader(Rule):
    """Spoken phone numbers, in pairs or digit by digit: *zéro six douze trente-quatre cinquante-six
    soixante-dix-huit* → ``06 12 34 56 78``, *plus trente-trois un …* → ``+33 1 23 45 67 89``; other countries take
    *plus*, a code and seven digits or more, paired from the right.

    The anchors (a leading *zéro* and exactly ten digits, or *plus* and a code) keep ordinary numbers out."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        number = spoken_cardinal()
        two = (number @ (NONZERO_DIGIT + DIGIT)).optimize()            # dix … quatre-vingt-dix-neuf
        three = (number @ (NONZERO_DIGIT + DIGIT + DIGIT)).optimize()   # cent … neuf cent quatre-vingt-dix-neuf
        # Each group costs a little so the split with fewer groups wins (*vingt trois* is 23, not 2 | 3).
        group = pynutil.add_weight(pynini.union(DIGIT_SAID, two), 0.1)
        groups = (group + pynini.closure(GAP + group)).optimize()
        first = (DIGIT_SAID @ NONZERO_DIGIT).optimize()
        # 0 + digit, then four pairs: ``06 12 34 56 78``.
        rest = (groups @ pynini.closure(DIGIT, 8, 8) @ pairs_from_right(8)).optimize()
        domestic = pynini.cross("zéro", "0") + GAP + first + pynutil.insert(" ") + GAP + rest

        thirty_three = pynini.union(number @ "33", pynini.cross("trois trois", "33"))
        national = pynutil.add_weight(pynutil.delete("zéro "), 0.1).ques + (groups @ (NONZERO_DIGIT + pynini.closure(
            DIGIT, 8, 8)) @ pairs_from_right(9))
        to_france = pynini.union(pynini.cross("plus ", "+"), pynini.cross("zéro zéro ", "00")) + thirty_three \
            + pynutil.insert(" ") + GAP + national

        code = pynutil.add_weight(pynini.union(first, two, three), 0.1)
        long_groups = (pynini.union(group, pynutil.add_weight(three, 0.3))
                       + pynini.closure(GAP + pynini.union(group, pynutil.add_weight(three, 0.3)))).optimize()
        abroad = pynini.cross("plus ", "+") + code + pynutil.insert(" ") + GAP + (long_groups @ pynini.union(
            *[pynini.closure(DIGIT, n, n) @ pairs_from_right(n) for n in range(7, 16)]))

        graph = pynini.union(domestic, to_france, pynutil.add_weight(abroad, 0.2))
        return self.wrap(text(graph)).optimize()

from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, SIGMA, TR_LOWER, Rule, drop_space
from .cardinal import _BIG, TAIL_WORDS, CardinalReader, _forms


def digit_groups(cardinal: CardinalReader, max_group: int = 3, group_weight: float = 0.1, tolerant: bool = True) -> pynini.Fst:
    """Spoken digit groups of a phone number / IBAN.

    ``tolerant`` accepts written digits, punctuation and fillers between groups.  ``tolerant=False`` (only spoken
    words and single spaces) is used without an anchor so a comma-separated list of numbers is never glued into
    a phone number.
    """
    glue = drop_space if not tolerant else _glue()
    s_r, b_r, o_r = _group_parts(cardinal, ROUND, max_group, group_weight, tolerant)
    s_l, b_l, o_l = _group_parts(cardinal, 0.0, max_group, group_weight, tolerant)
    # A single-digit group directly followed by a bare "yüz" group would split "beş yüz beş" into 5 | 105 and invent
    # a digit that was never said, so that adjacency is not part of the language: S never precedes B.
    t_g = pynini.union(o_r, b_r)
    s_g, o_g = s_r + glue, o_r + glue
    body = pynini.closure(pynini.union(t_g + glue, pynini.closure(s_g, 1) + o_g))
    ending = pynini.union(
        body + pynini.union(s_l, o_l, b_l),
        body + pynini.closure(s_g, 1) + pynini.union(s_l, o_l),
    )
    return ending.optimize()


ROUND = 3.0


def _inner(tolerant: bool) -> pynini.Fst:
    """Separator inside one group (``yirmi, üç``): a space, or with ``tolerant`` also recognizer punctuation."""
    if not tolerant:
        return drop_space
    return pynini.union(drop_space, pynutil.add_weight(pynutil.delete(pynini.union(", ", ". ", "; ")), 0.05))


def _glue() -> pynini.Fst:
    """Separator between groups as recognizers emit it: punctuation, hyphens, fillers."""
    punct = pynutil.delete(pynini.closure(pynini.union(",", ".", "-", ";", ":"), 0, 2))
    filler = pynutil.add_weight(pynutil.delete(pynini.union(" eee", " ııı", " hmm", " şey", " ee", " ıı")) + punct, 0.2)
    return pynini.union(drop_space, punct + drop_space, pynutil.delete("-"), pynutil.delete("."), punct + drop_space + punct,
                        punct + filler + drop_space + punct)


def _group_parts(cardinal: CardinalReader, round_penalty: float, max_group: int, group_weight: float, tolerant: bool,
                 allow_round: bool = True) -> tuple[pynini.Fst, pynini.Fst, pynini.Fst]:
    """The spoken digit groups of ``_group`` split into (single digit, bare ``yüz`` group, everything else)."""
    inner = _inner(tolerant)
    nz = pynini.difference(DIGIT, "0")
    two_full = cardinal.ties + inner + cardinal.digit
    two_round = pynutil.add_weight(cardinal.ties + pynutil.insert("0"), round_penalty)
    if not allow_round:
        two_round = pynini.Fst()  # empty: no round two-digit groups
    two_any = pynini.union(two_full, two_round, pynutil.insert("0") + cardinal.digit)
    hundreds_tail = inner + two_any
    if allow_round:
        hundreds_tail = pynini.union(hundreds_tail, pynutil.add_weight(pynutil.insert("00"), round_penalty))
    three = cardinal.digit + inner + pynutil.delete("yüz") + hundreds_tail
    bare = pynini.Fst()
    if allow_round:
        bare = pynini.cross("yüz", "1") + pynini.union(inner + two_any, pynutil.add_weight(pynutil.insert("00"), round_penalty + 2.0))
    # "sıfır yüz yirmi" is 0 | 1 20, never a hundred, so only a non-zero digit word counts as a single-digit group.
    single = cardinal.digit
    other = pynini.union(cardinal.zero, two_full, two_round)
    if max_group >= 3:
        other = pynini.union(other, three)
    if max_group >= 4:
        other = pynini.union(other, cardinal.graph_no_zero @ (nz + DIGIT + DIGIT + DIGIT))
    if tolerant:
        other = pynini.union(other, pynini.closure(DIGIT, 1, 6))
    w = group_weight
    return pynutil.add_weight(single, w), pynutil.add_weight(bare, w), pynutil.add_weight(other, w)


def _group(cardinal: CardinalReader, round_penalty: float, max_group: int, group_weight: float, tolerant: bool,
           allow_round: bool = True) -> pynini.Fst:
    """One spoken digit group (``beş``, ``kırk üç``, ``beş yüz elli``) → its digits; round groups pay ``round_penalty``.

    With ``allow_round=False`` a group must spell every digit (``beş yüz elli`` = 550 and ``altmış`` = 60 are rejected).
    """
    return pynini.union(*_group_parts(cardinal, round_penalty, max_group, group_weight, tolerant, allow_round))


def shaped_groups(cardinal: CardinalReader, shape: tuple[int, ...], round_penalty: float = 0.5, group_weight: float = 0.1) -> pynini.Fst:
    """Exactly the groups in ``shape`` (digit counts), e.g. ``(3, 3, 2, 2)``, with punctuation between groups.

    At most one group may be round (``beş yüz elli`` = 550), so a list of round prices stays a list.
    """
    def exact(size: int) -> pynini.Fst:
        return _group(cardinal, 0.0, 3, group_weight, tolerant=True, allow_round=False) @ pynini.closure(DIGIT, size, size)

    def rounded(size: int) -> pynini.Fst:
        return _group(cardinal, round_penalty, 3, group_weight, tolerant=True) @ pynini.closure(DIGIT, size, size)

    def chain(round_at: int | None) -> pynini.Fst:
        out = None
        for i, size in enumerate(shape):
            g = rounded(size) if i == round_at else exact(size)
            out = g if out is None else out + _glue() + g
        assert out is not None
        return out

    return pynini.union(chain(None), *[chain(i) for i in range(len(shape))]).optimize()

class TelephoneReader(Rule):
    name = "telephone"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        groups = digit_groups(cardinal)
        d = DIGIT
        fmt11 = pynini.accep("0") + d + d + d + pynutil.insert(" ") + d + d + d + pynutil.insert(" ") + d + d + pynutil.insert(" ") + d + d
        fmt10 = d + d + d + pynutil.insert(" ") + d + d + d + pynutil.insert(" ") + d + d + pynutil.insert(" ") + d + d
        domestic = groups @ fmt11
        intl = pynini.union(pynini.cross("artı doksan", "+90 "), pynini.cross("sıfır sıfır doksan", "+90 ")) + drop_space + (groups @ fmt10)

        # No anchor (no ``sıfır``, no ``+90``): clean spoken digits, or the 3-3-2-2 mobile layout; both start with 5.
        mobile = pynini.accep("5") + pynini.closure(d, 9, 9)
        ten_mobile = pynini.union(
            digit_groups(cardinal, tolerant=False) @ mobile,
            # dearer than the anchored forms, so ``sıfır beş yüz …`` is still read as one 11-digit number
            pynutil.add_weight(shaped_groups(cardinal, (3, 3, 2, 2)) @ mobile, 0.5),
        )
        # Must stay above 1.0, or ``0`` + unanchored mobile ties with the anchored reading and doubles the 0.
        mobile_no_zero = pynutil.add_weight((pynutil.insert("0") + ten_mobile) @ fmt11, 1.4)
        # ``doksan beş yüz otuz iki …`` without ``artı``: 90 before a full mobile number is the country code.
        intl_no_plus = pynutil.add_weight(pynini.cross("doksan", "+90 ") + drop_space + (ten_mobile @ fmt10), 0.3)
        number = pynini.union(domestic, intl, mobile_no_zero, intl_no_plus)
        # A case ending on the last group word: ``… on iki otuz dörtten`` -> ``0532 645 12 34'ten``.
        tail = pynini.union(*[pynini.cross(surface, f"{w}'{sfx}") for w in TAIL_WORDS
                              for surface, sfx in _forms(w, () if w in _BIG else None)])
        split = SIGMA + pynini.accep(" ") + tail
        suffixed = pynini.compose(split, number + pynini.accep("'") + pynini.closure(TR_LOWER, 1))
        number = pynini.union(number, suffixed)
        return self.wrap(pynutil.insert('number="') + number + pynutil.insert('"')).optimize()

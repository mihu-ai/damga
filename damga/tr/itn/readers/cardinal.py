from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, SIGMA, TR_LOWER, Rule, drop_space, string_map, strip_leading_zeros
from ...lexicon import DIGITS, SCALES, TIES, ZERO
from ...morph import case_suffixes, more_suffixes

# Words a spoken number can end with.  Some suffixed forms are ordinary words alone (``ona``, ``birden``), so a
# single-word number only takes a suffix when the word is not in NO_BARE_SUFFIX.
TAIL_WORDS = [ZERO] + [w for w, _ in DIGITS] + [w for w, _ in TIES] + SCALES
NO_BARE_SUFFIX = frozenset({"bir", "on", ZERO} | set(SCALES))
# After ``bin``/``milyon``… only case endings: ``seksen binlerden`` is written ``80 binlerden``, not ``80.000'lerden``.
_BIG = frozenset(SCALES) - {"yüz"}
# ``onun`` (his), ``onlar`` (they): pronouns, even after another number word.
_PRONOUN_FORMS = {"on": ("genitive", "plural")}
# Decade words take the plural and ``-li``/``-lik`` alone: ``yetmişler`` → 70'ler, ``doksanlı yıllar`` → 90'lı.
_DECADE_KINDS = ("plural", "li", "lik", "genitive")
# The genitive alone where it is no other word (``sekizin katları``, ``dördün``; not ``altının`` of the gold).
_GENITIVE_ALONE = frozenset({"iki", "üç", "dört", "beş", "yedi", "sekiz", "dokuz"})


def _forms(word: str, kinds: tuple[str, ...] | None) -> list[tuple[str, str]]:
    """Case endings of ``word`` plus the ``more_suffixes`` kinds listed (None: all)."""
    forms = list(case_suffixes(word))
    for kind, pairs in more_suffixes(word).items():
        if (kinds is None or kind in kinds) and kind not in _PRONOUN_FORMS.get(word, ()):
            forms += pairs
    return list(dict.fromkeys(forms))


class CardinalReader(Rule):
    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):

        digit = string_map(DIGITS)
        ties = string_map(TIES)
        zero = pynini.cross(ZERO, "0")
        self.digit = digit
        self.zero = zero
        self.ties = ties

        TIE = 0.01
        two_digit = pynini.union(
            ties + pynini.union(drop_space + digit, pynutil.add_weight(pynutil.insert("0"), TIE)),
            pynutil.insert("0") + digit,
        )

        hundreds = pynini.union(
            string_map(DIGITS[1:]) + pynutil.delete(" yüz"),
            pynini.cross("yüz", "1"),
            pynutil.add_weight(pynini.cross("bir yüz", "1"), 1.0),
        )
        three_digit = pynini.union(
            hundreds + pynini.union(drop_space + two_digit, pynutil.add_weight(pynutil.insert("00"), TIE)),
            pynutil.insert("0") + two_digit,
        )

        thousands = pynini.union(
            pynini.union(three_digit + pynutil.delete(" bin"), pynutil.add_weight(pynutil.insert("00") + digit + pynutil.delete(" bin"), 0.0)),
            pynini.cross("bin", "001"),
            pynutil.add_weight(pynini.cross("bir bin", "001"), 1.0),
        )

        six_digit = pynini.union(
            thousands + pynini.union(drop_space + three_digit, pynutil.insert("000")),
            pynutil.insert("000") + three_digit,
        )

        def scale(lower: pynini.Fst, word: str, width: int) -> pynini.Fst:
            pad = "0" * width
            unit = pynini.union(
                three_digit + pynutil.delete(f" {word}"),
                pynutil.add_weight(pynini.cross(word, "001"), 0.5),
            )
            return pynini.union(
                unit + pynini.union(drop_space + lower, pynutil.insert(pad)),
                pynutil.insert("000") + lower,
            )

        nine_digit = scale(six_digit, "milyon", 6)
        twelve_digit = scale(nine_digit, "milyar", 9)
        fifteen_digit = scale(twelve_digit, "trilyon", 12)

        graph = (fifteen_digit @ strip_leading_zeros()).optimize()
        graph = pynini.union(graph, zero).optimize()

        self.two_digit = two_digit.optimize()
        self.three_digit = three_digit.optimize()
        self.graph_no_zero = (fifteen_digit @ strip_leading_zeros()).optimize()
        self.graph = graph

        NZ = pynini.difference(DIGIT, "0")
        written = pynini.union(NZ + pynini.closure(DIGIT), pynini.accep("0"),
                               NZ + pynini.closure(DIGIT, 0, 2) + pynini.closure(pynutil.delete(".") + DIGIT + DIGIT + DIGIT, 1))
        mixed = pynini.closure(DIGIT) + pynutil.delete("0") + drop_space + digit
        self.written = written.optimize()
        self.graph_mixed = pynini.union(graph, pynutil.add_weight(written, 0.1), pynutil.add_weight(mixed, 0.2)).optimize()

        spoken_no_lone_bir = pynini.difference(pynini.project(graph, "input"), pynini.accep("bir")).optimize()
        self.graph_tag = (spoken_no_lone_bir @ graph).optimize()

        self.graph_suffixed = self.with_suffix(graph)

        optional_minus = pynini.closure(pynutil.insert('negative="') + pynini.cross("eksi", "-") + pynutil.insert('" ') + drop_space, 0, 1)
        final = optional_minus + pynutil.insert('integer="') + pynini.union(self.graph_tag, self.graph_suffixed) + pynutil.insert('"')
        return self.wrap(final)

    @staticmethod
    def with_suffix(graph: pynini.Fst, anywhere: bool = False) -> pynini.Fst:
        """``graph`` with a suffix on its last word: ``yirmi altıda`` → ``26" suffix="da``; the caller closes the quote.

        The suffix is split off on the input side behind an apostrophe, which ``graph``'s input never contains.
        After another number word every inflection counts; a single word takes only the case endings (decade words
        also the plural and ``-li``).  ``anywhere`` (after ``yüzde``) accepts every inflection on every word.
        """
        def cross(pairs_by_word):
            return pynini.union(*[pynini.cross(surface, f"{w}'{s}") for w, pairs in pairs_by_word for surface, s in pairs])

        tail = cross([(w, _forms(w, () if w in _BIG else None)) for w in TAIL_WORDS])
        if anywhere:
            bare = cross([(w, _forms(w, None)) for w in TAIL_WORDS])
        else:
            ties = {t for t, _ in TIES} - {"on"}
            bare = cross([(w, _forms(w, _DECADE_KINDS if w in ties else ("genitive",) if w in _GENITIVE_ALONE else ()))
                          for w in TAIL_WORDS if w not in NO_BARE_SUFFIX])
        split = pynini.union(SIGMA + pynini.accep(" ") + tail, bare)
        read = graph + pynini.cross("'", '" suffix="') + pynini.closure(TR_LOWER, 1)
        return pynini.compose(split, read).optimize()

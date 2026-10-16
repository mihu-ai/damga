from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, SIGMA, Rule
from ...lexicon import BIG_SCALES
from ...numbers import CARDINAL, CARDINAL_ATTRIBUTIVE, YEAR_SPOKEN, group_thousands

_LOWER = pynini.cdrewrite(pynini.union(*[pynini.cross(c, c.lower()) for c in "MB"]), "", "", SIGMA)


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def canonical() -> pynini.Fst:
    """Alternative spellings mapped to the one the grammars read: "zwo" → "zwei", "tausendund…" → "tausend…"."""
    lower = pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüß")
    zwo = pynini.cdrewrite(pynini.cross("zwo", "zwei"), pynini.union("[BOS]", " ", "tausend", "hundert"),
                           pynini.union("[EOS]", " ", "tausend", "hundert", "und"), SIGMA)
    und = pynini.cdrewrite(pynutil.delete("und"), "tausend", lower, SIGMA)
    return (zwo @ und).optimize()


def spoken_cardinal() -> pynini.Fst:
    """Spoken (lower case) → digits; "eins" and "ein" both end a number (hunderteins, hundertein Euro)."""
    return (canonical() @ pynini.invert(pynini.union(CARDINAL, CARDINAL_ATTRIBUTIVE) @ _LOWER)).optimize()


def written_digits(group: bool = True) -> pynini.Fst:
    """``25000`` → ``25.000``; four digits stay as they are (``1300``, ``2012``)."""
    return group_thousands(5) if group else pynini.closure(DIGIT, 1).optimize()


# A number after these words is written in digits even below thirteen (Absatz 3); "Nummer" is ambiguous, left out.
REFERENCE_WORDS = ("artikel", "absatz", "absätze", "ziffer", "änderungsantrag", "änderungsanträge", "kapitel",
                   "anhang", "erwägung", "erwägungsgrund", "kategorie", "tagesordnungspunkt", "randnummer")


class CardinalReader(Rule):
    """``fünfundzwanzigtausend`` → ``25.000``.  A lone number up to twelve stays a word (``zwei Berichte``)."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False, group: bool = True):
        number = spoken_cardinal()
        self.number = number
        words = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüß "))
        ends_in_scale = words + pynini.union(*[" " + w.lower() for s in BIG_SCALES for w in s])
        plain = pynini.difference(pynini.project(number, "input"), ends_in_scale) @ number
        self.digits = (plain @ written_digits(group)).optimize()
        small = pynini.union(*[str(d) for d in range(13)])
        self.big = (plain @ pynini.difference(pynini.closure(DIGIT, 1), small) @ written_digits(group)).optimize()
        self.year = (canonical() @ pynini.invert(YEAR_SPOKEN)).optimize()   # zwanzig dreizehn, zwanzigzwanzig → 2013, 2020
        scale = pynini.union(*[pynini.cross(" " + w.lower(), " " + w) for s in BIG_SCALES for w in s])
        with_scale = (number @ pynini.closure(DIGIT, 1, 3)) + scale            # zehn millionen → 10 Millionen
        with_scale = pynini.union(with_scale, *[pynini.cross("eine " + sg.lower(), "1 " + sg) for sg, _ in BIG_SCALES])
        self.with_scale = with_scale.optimize()
        sign = pynini.closure(pynini.cross("minus ", "-"), 0, 1)
        # siebenundvierzigjähriger → 47-jähriger (up to twelve the word stays: dreijährig)
        suffix = pynini.union("jährig", "fach", "prozentig", "tägig", "stündig", "wöchig", "monatig", "seitig",
                              "köpfig", "minütig") + pynini.closure(pynini.union("e", "en", "er", "es", "em"), 0, 1)
        compound = self.big + pynutil.insert("-") + suffix
        reference = pynini.union(*REFERENCE_WORDS) + pynini.accep(" ") + self.digits
        graph = pynini.union(pynutil.add_weight(reference, -0.2), sign + self.big, compound, pynini.cross("minus ", "-") + self.digits,
                             pynutil.add_weight(self.year, -0.1), self.with_scale)
        return self.wrap(text(graph)).optimize()

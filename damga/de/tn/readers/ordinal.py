from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import ORDINAL_STEM
from .cardinal import text
from .date import STRONG_EN, WEAK

# "N." before one of these nouns (or a compound ending in one) is an ordinal even without an article.
ORDINAL_NOUNS = ("jahrhundert", "jahrestag", "geburtstag", "todestag", "richtlinie", "programm", "paket", "bericht",
                 "konferenz", "parteitag", "jubiläum", "weltkrieg", "runde", "sitzung", "tagung", "periode", "gipfel",
                 "kongress", "erweiterung", "mitglied", "staat", "jahr", "mal", "platz", "stelle", "woche", "quartal",
                 "änderung", "protokoll", "verordnung")


# After these "N." is an ordinal only before a noun ("von 50 bis 100." ends a sentence); after the other STRONG_EN
# words also without one ("zum 1000.").
_PREPOSITIONS = ("vor", "seit", "bis")
ARTICLES_EN = tuple(w for w in STRONG_EN if w not in _PREPOSITIONS)


def ordinal_noun() -> pynini.Fst:
    lower = pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüß")
    upper = pynini.union(*"ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ")
    ending = pynini.closure(pynini.union("s", "es", "e", "en", "n"), 0, 1)
    whole = pynini.union(*[w[0].upper() + w[1:] for w in ORDINAL_NOUNS])
    compound = upper + pynini.closure(lower, 1) + pynini.union(*ORDINAL_NOUNS)
    return (pynini.union(whole, compound) + ending).optimize()


class OrdinalReader(Rule):
    """``der 3. Platz`` → ``der dritte Platz``, ``im 20. Jahrhundert`` → ``im zwanzigsten Jahrhundert``.

    "3." before a lower-case word cannot end a sentence, so it is an ordinal with the strong ending -er.  Without an
    article, an ``ORDINAL_NOUNS`` noun or a lower-case word after it, "3." stays a number (``Das kostet 3.``)."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        number = pynini.union(*[str(n) for n in range(1, 1001)]) @ ORDINAL_STEM
        sp = pynini.accep(" ")

        def one(ending: str) -> pynini.Fst:
            return number + pynutil.delete(".") + pynutil.insert(ending)

        def ordinal(ending: str) -> pynini.Fst:
            # der 3. und 4. Platz → der dritte und vierte Platz: the article's ending holds for both
            return one(ending) + pynini.closure(pynini.union(" und ", " oder ", " bis ") + one(ending), 0, 1)

        noun = pynini.closure(sp + ordinal_noun(), 0, 1)     # taken along, so the article's ending wins
        # the word in lower case is taken along to make sure of it; a reading with an article goes first
        lower = pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüß")
        lower_word = lower + pynini.closure(pynini.union(lower, *"ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ"))
        graph = pynini.union(pynini.union(*WEAK) + sp + ordinal("e") + noun,
                             pynini.union(*ARTICLES_EN) + sp + ordinal("en") + noun,
                             pynini.union(*_PREPOSITIONS) + sp + ordinal("en") + sp + ordinal_noun(),
                             ordinal("en") + sp + ordinal_noun(),
                             pynutil.add_weight(one("er") + sp + lower_word, 0.1))
        return self.wrap(text(graph)).optimize()

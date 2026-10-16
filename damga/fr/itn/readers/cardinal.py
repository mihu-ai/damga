from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import CARDINAL, CARDINAL_FEM, TENS, WORDS, flexible, group_thousands
from ...tn.readers.cardinal import hundreds_year


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def _belgian() -> pynini.Fst:
    """Canonical 70–99 → the Belgian and Swiss words (septante, huitante, octante, nonante), whole words only and
    each number on its own, as both systems may be mixed."""
    pairs = []
    units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    for n in range(70, 100):
        canon = pynini.shortestpath(pynini.accep(str(n)) @ TENS).string()
        for tens in {7: ["septante"], 8: ["huitante", "octante"], 9: ["nonante"]}[n // 10]:
            u = n % 10
            said = tens if u == 0 else (f"{tens} et un" if u == 1 else f"{tens}-{units[u]}")
            pairs.append((canon, said))
    pairs += [("quatre-vingt", "huitante"), ("quatre-vingt", "octante")]   # quatre-vingt mille
    rule = pynini.union(*[pynini.cross(a, b) for a, b in pairs])
    out = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyzàâäæçéèêëîïôœùûüÿ -"))
    rewrite = pynini.cdrewrite(rule, pynini.union(" ", "[BOS]"), pynini.union(" ", "[EOS]"), out, mode="opt")
    return rewrite.optimize()


def spoken_cardinal() -> pynini.Fst:
    """Spoken → digits: masculine and feminine, the Belgian/Swiss tens, 1100–1999 counted in hundreds, with a
    space, a hyphen or nothing between the words."""
    canon = pynini.union(CARDINAL, CARDINAL_FEM, CARDINAL @ _belgian(), hundreds_year())
    return pynini.invert(canon @ flexible()).optimize()


def written_digits(group: bool = True) -> pynini.Fst:
    return group_thousands(5) if group else pynini.closure(DIGIT, 1).optimize()


# A number that names something is written in digits even at ten and below: "article cinq" → "article 5".
REFERENCE_WORDS = ("article", "articles", "paragraphe", "amendement", "amendements", "considérant", "annexe",
                   "chapitre", "page", "numéro", "point", "titre", "règle", "niveau", "objectif", "priorité", "étape",
                   "catégorie", "option", "pilier", "protocole", "alinéa", "section", "partie", "phase", "lot")


class CardinalReader(Rule):
    """``vingt et un`` → ``21``, ``quinze mille`` → ``15 000``, ``deux mille seize`` → ``2016``, ``deux millions`` →
    ``2 millions``.  Zero to ten stay words (``deux rapports``), as French is written."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False, group: bool = True):
        number = spoken_cardinal()
        self.number = number
        # deux millions, deux-millions, deuxmillions → 2 millions
        scale_words = pynini.union(" ", pynini.cross("-", " "), pynutil.insert(" ")) + pynini.union(*QUANTITY_WORDS)
        ends_in_scale = WORDS + pynini.union(*QUANTITY_WORDS)
        written = number @ written_digits(group)
        self.digits = (pynini.difference(pynini.project(written, "input"), ends_in_scale) @ written).optimize()
        small = pynini.union(*[str(d) for d in range(11)])
        self.big = (self.digits @ pynini.difference(pynini.closure(pynini.union(DIGIT, " "), 1), small)).optimize()
        with_scale = (number @ pynini.closure(DIGIT, 1, 3)) + scale_words
        reference = pynini.union(*REFERENCE_WORDS) + pynini.accep(" ") + self.digits
        sign = pynini.closure(pynini.cross("moins ", "-"), 0, 1)
        graph = pynini.union(
            pynutil.add_weight(reference, -0.2),
            sign + self.big,
            pynini.cross("moins ", "-") + self.digits,
            with_scale,
        )
        return self.wrap(text(graph)).optimize()

from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, SIGMA, Rule
from ....en.itn.readers.cardinal import text
from ...lexicon import QUANTITY_WORDS
from ...numbers import CARDINAL_MARKED, group_thousands

__all__ = ["CardinalReader", "REFERENCE_WORDS", "spoken_cardinal", "text"]

# A number that names something is written in digits even below ten: "paragrafo otto" → "paragrafo 8".
REFERENCE_WORDS = ("paragrafo", "paragrafi", "articolo", "articoli", "emendamento", "emendamenti", "considerando",
                   "allegato", "capitolo", "sezione", "pagina", "comma", "numero", "fase", "livello", "pilastro",
                   "obiettivo", "titolo", "parte", "tabella", "figura", "regola", "protocollo", "punto", "voce",
                   "rubrica")


def spoken_cardinal() -> pynini.Fst:
    """Spoken → digits: glued as Italian writes numbers (duemilasedici) and also spaced or with "e" after the
    thousands (duemila sedici, duemila e sedici); tre without the accent in a compound (ventitre) too."""
    spoken = pynini.union(
        pynini.cdrewrite(pynini.cross("|", pynini.union("", " ", " e ")), "", "", SIGMA),
    ).optimize()
    accent = pynini.cdrewrite(pynini.cross("tré", pynini.union("tré", "tre")), "", "", SIGMA).optimize()
    # cento before otto/ottanta is written both ways: centoottanta and centottanta, centotto and centootto
    elision = pynini.cdrewrite(pynini.union(pynini.cross("centoott", pynini.union("centoott", "centott")),
                                            pynini.cross("centott", pynini.union("centott", "centoott"))),
                               "", "", SIGMA).optimize()
    # ventuno / ventiuno, trentotto / trentaotto: the tens may keep their vowel
    tens = ("venti", "trenta", "quaranta", "cinquanta", "sessanta", "settanta", "ottanta", "novanta")
    full = pynini.cdrewrite(pynini.union(*[pynini.cross(t[:-1] + u, pynini.union(t[:-1] + u, t + u))
                                           for t in tens for u in ("uno", "otto")]), "", "", SIGMA).optimize()
    return pynini.invert(CARDINAL_MARKED @ spoken @ accent @ elision @ full).optimize()


class CardinalReader(Rule):
    """``venticinquemila`` → ``25.000``, ``tre milioni`` → ``3 milioni``.  A lone number below ten stays a word
    (``due anni``), the way Italian is written."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False):
        number = spoken_cardinal()
        self.number = number
        self.digits = (number @ group_thousands()).optimize()
        small = pynini.union(*[str(d) for d in range(10)])
        words = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyzàèéìòù "))
        ends_in_scale = words + pynini.union(*[" " + w for w in QUANTITY_WORDS])
        big = number @ pynini.difference(pynini.closure(DIGIT, 1), small) @ group_thousands()
        self.big = (pynini.difference(pynini.project(big, "input"), ends_in_scale) @ big).optimize()
        scale = pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS])
        with_scale = pynini.union(number @ pynini.closure(DIGIT, 1, 3), pynini.cross("un", "1")) + scale
        reference = pynini.union(*REFERENCE_WORDS) + pynini.accep(" ") + (pynini.difference(
            pynini.project(self.digits, "input"), ends_in_scale) @ self.digits)
        five_stars = pynini.cross("cinque stelle", "5 Stelle")
        graph = pynini.union(
            pynutil.add_weight(reference, -0.2),
            pynutil.add_weight(five_stars, -0.2),
            self.big,
            pynini.cross("meno ", "-") + self.digits,
            with_scale,
        )
        return self.wrap(text(graph)).optimize()

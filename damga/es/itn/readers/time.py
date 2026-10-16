from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import text

PERIODS = [" de la mañana", " de la tarde", " de la noche", " de la madrugada", " del mediodía"]


class TimeReader(Rule):
    """``a las once cuarenta y cinco horas`` → ``a las 11.45 horas``, ``las dos menos veinte`` → ``la 1.40``.
    After a bare article (``las``) only with minutes or the part of the day, so ``las dos casas`` stays."""

    name = "time"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        hour = number @ pynini.union(*[str(h) for h in range(0, 25)])
        two = pynini.union(*[f"{m:02d}" for m in range(1, 60)])
        minutes = pynini.union(
            pynini.cross(" y media", ".30"), pynini.cross(" y cuarto", ".15"),
            pynutil.insert(".") + pynini.cross(" cero ", "0") + (number @ pynini.union(*"123456789")),
            pynutil.insert(".") + pynutil.delete(" ") + (number @ (pynini.union(*"12345") + DIGIT)),
            # la una y diez, la una con cinco
            pynutil.insert(".") + pynutil.delete(pynini.union(" y ", " con "))
            + (number @ pynini.union(*[str(m) for m in range(1, 60)]) @ pynini.union(pynutil.insert("0") + DIGIT, two)),
        )
        prep = pynini.union("a ", "de ", "hasta ", "desde ", "sobre ")
        article = pynini.union("las ", "la ")
        lead = prep + article
        horas = pynini.accep(" horas")
        # a eme / pe eme → a. m. / p. m.; the part of the day stays words
        period = pynini.union(*PERIODS, pynini.cross(pynini.union(" a eme", " a m"), " a. m."),
                              pynini.cross(pynini.union(" pe eme", " p m"), " p. m."))
        # "las dos menos veinte" → "la 1.40", "las tres menos cuarto" → "las 2.45"
        to = []
        for h in range(2, 25):
            said = number @ pynini.accep(str(h))
            art = pynini.cross("las ", "la ") if h == 2 else pynini.accep("las ")
            for m in range(1, 31):
                spoken = pynini.cross(" menos cuarto", "") if m == 15 else (
                    pynutil.delete(" menos ") + pynutil.delete(number @ pynini.accep(str(m))))
                to.append(prep.ques + art + pynutil.delete(said) + spoken + pynutil.insert(f"{h - 1}.{60 - m:02d}"))
        graph = pynini.union(
            pynini.union(lead, article) + hour + minutes + pynini.closure(horas, 0, 1) + period.ques,
            lead + hour + pynutil.insert(".00") + horas,
            lead + hour + period.ques,
            article + hour + period,
            hour + minutes + period,
            pynini.union(*to) + period.ques,
        )
        return self.wrap(text(graph)).optimize()

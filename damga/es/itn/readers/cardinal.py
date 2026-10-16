from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_APOC, CARDINAL_FEM, group_thousands


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def spoken_cardinal() -> pynini.Fst:
    """Spoken → digits, every form: uno/un/una, veintiuno/veintiún/veintiuna, doscientos/doscientas."""
    return pynini.invert(pynini.union(CARDINAL, CARDINAL_APOC, CARDINAL_FEM)).optimize()


def written_digits(group: bool = True) -> pynini.Fst:
    """``25000`` → ``25.000``; up to four digits (``2008``, ``1500``) without a separator."""
    return group_thousands(".", 5) if group else pynini.closure(DIGIT, 1).optimize()


# A number that names something is written in digits even when small: "el artículo cinco" → "el artículo 5".
REFERENCE_WORDS = ("artículo", "artículos", "apartado", "apartados", "párrafo", "párrafos", "enmienda", "enmiendas",
                   "considerando", "anexo", "capítulo", "sección", "título", "número", "página", "punto", "fase",
                   "nivel", "objetivo", "eje", "prioridad", "línea", "opción", "pilar", "protocolo", "fila", "grupo")
SCALES = (" millón", " millones", " billón", " billones")


class CardinalReader(Rule):
    """``veinticinco mil`` → ``25.000``, ``dos mil ocho`` → ``2008``, ``ochenta millones`` → ``80 millones``.  A lone
    number up to ten stays a word (``tres informes``), as Spanish is written; ``artículo cinco`` → ``artículo 5``."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False, group: bool = True):
        number = spoken_cardinal()
        self.number = number
        words = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyzáéíóúüñ "))
        ends_in_scale = words + pynini.union(*SCALES)
        no_scale = pynini.difference(pynini.project(number, "input"), ends_in_scale) @ number
        self.digits = (no_scale @ written_digits(group)).optimize()
        small = pynini.union(*[str(d) for d in range(11)])
        self.big = (no_scale @ pynini.difference(pynini.closure(DIGIT, 1), small) @ written_digits(group)).optimize()
        # ochenta millones → 80 millones, cinco mil millones → 5000 millones; "un millón" stays as it is
        multiplier = pynini.difference(pynini.project(number, "input"), pynini.union("un", "uno")) @ number
        with_scale = (multiplier @ pynini.closure(DIGIT, 1, 6)) + pynini.union(*[pynini.accep(s) for s in SCALES])
        reference = pynini.union(*REFERENCE_WORDS) + pynini.accep(" ") + self.digits
        sign = pynini.closure(pynini.cross("menos ", "-"), 0, 1)
        graph = pynini.union(
            pynutil.add_weight(reference, -0.2),
            sign + self.big,
            pynini.cross("menos ", "-") + self.digits,
            with_scale,
        )
        return self.wrap(text(graph)).optimize()

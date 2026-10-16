from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NON_QUOTE, Rule
from ...morph import SUFFIX_KIND, reinflect
from .cardinal import optional_sign, optional_suffix
from .decimal import number_body
from .number import CARDINAL, TWO_DIGIT

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "currency.tsv"


def _spoken_units() -> list[str]:
    """Every word the money reader can put in ``currency`` / ``minor_unit``, plus ``lira`` (the major unit before
    kuruş)."""
    words = {"lira"}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            words.update(x.strip() for x in line.split("\t")[1:3] if x.strip())
    return sorted(words)


def with_suffix(word: str) -> pynini.Fst:
    """Output ``word`` and consume the token's optional suffix, inflected on the spoken word: ``TL'ye`` is written
    for *te-le*, so ``Türk lirası`` + ``ye`` → ``Türk lirasına``; ``kuruş`` + ``den`` → ``kuruştan``.  An unknown suffix
    is glued on as written (weighted, so the inflected forms win)."""
    known = [pynini.cross(f' suffix="{sfx}"', form) for sfx in SUFFIX_KIND if (form := reinflect(word, sfx))]
    raw = pynutil.insert(word) + optional_suffix()
    return pynini.union(pynutil.insert(word), *[pynutil.insert("") + k for k in known], pynutil.add_weight(raw, 1.0))


class MoneyWriter(Rule):
    name = "money"
    kind = "write"

    def build(self, variants: bool = False):
        q = pynini.closure(NON_QUOTE, 1)
        units = _spoken_units()
        currency = pynutil.delete(' currency="') + pynutil.insert(" ") + pynini.union(
            *[pynutil.delete(w + '"') + with_suffix(w) for w in units])
        plain = number_body() + currency

        integer = pynutil.delete('integer="') + (pynini.closure(DIGIT, 1) @ CARDINAL) + pynutil.delete('"')
        minor = pynutil.delete(' minor="') + (DIGIT + DIGIT @ TWO_DIGIT) + pynutil.delete('"')
        minor_unit = pynutil.delete(' minor_unit="') + q + pynutil.delete('"')
        major = pynutil.delete(' currency="') + pynini.union(pynini.cross("Türk lirası", "lira"), pynini.difference(q, "Türk lirası")) + pynutil.delete('"')

        with_minor = integer + pynutil.insert(" ") + _reorder(minor, minor_unit, major)
        return self.unwrap(optional_sign() + pynini.union(plain, with_minor))

def _reorder(minor: pynini.Fst, minor_unit: pynini.Fst, major: pynini.Fst) -> pynini.Fst:
    branches = []
    for n in range(100):
        if n == 0:
            continue
        two = f"{n:02d}"
        spoken = pynini.shortestpath(pynini.accep(two) @ TWO_DIGIT).string()
        m = pynutil.delete(f' minor="{two}"')
        branches.append(m + minor_unit_buffer(minor_unit, spoken, major))
    return pynini.union(*branches).optimize()

def minor_unit_buffer(minor_unit: pynini.Fst, spoken_minor: str, major: pynini.Fst) -> pynini.Fst:

    out = []
    for mu in ("kuruş", "sent", "peni"):
        out.append(pynutil.delete(f' minor_unit="{mu}"') + major + pynutil.insert(f" {spoken_minor} ") + with_suffix(mu))
    return pynini.union(*out)

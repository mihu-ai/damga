from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import CARDINAL, ORDINAL, strip_thousands
from .cardinal import text

_SPECIAL = {"1/2": "one half", "1/4": "one quarter", "3/4": "three quarters", "24/7": "twenty four seven", "7/24": "seven twenty four",
            "50/50": "fifty fifty"}


def mixed_number() -> pynini.Fst:
    """``2 1/2`` → ``two and a half``, ``3 3/4`` → ``three and three quarters``, ``1 1/3`` → ``one and a third``."""
    whole = strip_thousands() @ CARDINAL
    one = {"2": "a half", "4": "a quarter"}
    parts = []
    for d in range(2, 21):
        ordinal = pynini.shortestpath(pynini.accep(str(d)) @ ORDINAL).string()
        name, names = {2: ("half", "halves"), 4: ("quarter", "quarters")}.get(d, (ordinal, ordinal + "s"))
        parts.append(pynini.cross(f"1/{d}", one.get(str(d), "a " + name)))
        parts.append((pynini.union(*[str(n) for n in range(2, 100)]) @ CARDINAL) + pynini.cross(f"/{d}", " " + names))
    return (whole + pynini.cross(" ", " and ") + pynini.union(*parts)).optimize()


class FractionReader(Rule):
    """``3/4`` → ``three quarters``, ``2 1/2`` → ``two and a half``.  Denominators 2 to 20 only (not ``9/11``,
    ``24/7``)."""

    name = "fraction"
    kind = "read"

    def build(self, variants: bool = False):
        special = pynini.union(*[pynini.cross(k, v) for k, v in _SPECIAL.items()],
                               *[pynini.cross(k, v) for k, v in {"½": "one half", "¼": "one quarter",
                                                                 "¾": "three quarters", "⅓": "one third",
                                                                 "⅔": "two thirds"}.items()])
        numerator = pynini.union(*[str(n) for n in range(1, 100)])
        many = pynini.difference(numerator, "1") @ CARDINAL
        branches = [many + pynini.cross("/2", " halves"),
                    (pynini.difference(numerator, pynini.union("1", "3")) @ CARDINAL) + pynini.cross("/4", " quarters")]
        for d in range(3, 21):
            if d == 4:
                continue
            ordinal = pynini.shortestpath(pynini.accep(str(d)) @ ORDINAL).string()
            branches += [pynini.cross(f"1/{d}", f"one {ordinal}"), many + pynini.cross(f"/{d}", f" {ordinal}s")]
        generic = pynini.union(*branches)
        generic = pynini.difference(pynini.project(generic, "input"), pynini.project(special, "input")) @ generic
        graph = pynini.union(special, generic, pynutil.add_weight(mixed_number(), -0.1))
        return self.wrap(text(graph)).optimize()

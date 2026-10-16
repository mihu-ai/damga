from __future__ import annotations

import pynini

from ....core.rules import Rule
from ...lexicon import ORDINAL_TENS, ORDINALS
from .cardinal import text

_UNITS = [w for w, _ in ORDINALS[:9]]                     # primero … noveno
_HUNDREDS = ["centésimo", "ducentésimo", "tricentésimo", "cuadringentésimo", "quingentésimo", "sexcentésimo",
             "septingentésimo", "octingentésimo", "noningentésimo"]
_PLAIN = str.maketrans("áéíóú", "aeiou")


def _masculine(n: int) -> list[str]:
    """The ways ``n`` (1..999) is said as a masculine ordinal: 11 *undécimo* / *decimoprimero* / *décimo primero*,
    21 *vigésimo primero* / *vigesimoprimero*, 134 *centésimo trigésimo cuarto*."""
    if n <= 20:
        said = [dict((int(d), w) for w, d in ORDINALS)[n]]
        if 11 <= n <= 19:
            unit = _UNITS[n - 11]
            said += [f"décimo {unit}", "decimo" + unit.translate(_PLAIN) if n != 18 else "decimoctavo"]
        return list(dict.fromkeys(said))
    if n < 100:
        tens = dict((int(d), w) for w, d in ORDINAL_TENS)[n // 10]
        if n % 10 == 0:
            return [tens]
        unit = _UNITS[n % 10 - 1]
        glued = tens.translate(_PLAIN) + (unit[1:] if unit.startswith("o") else unit)   # vigesimoctavo
        return [f"{tens} {unit}", glued]
    head = _HUNDREDS[n // 100 - 1]
    return [head] if n % 100 == 0 else [f"{head} {rest}" for rest in _masculine(n % 100)]


def _feminine(said: str) -> list[str]:
    """``vigésimo primero`` → ``vigésima primera``, and the mixed ``vigésimo primera``."""
    words = said.split()
    every = " ".join(w[:-1] + "a" for w in words)
    last = " ".join(words[:-1] + [words[-1][:-1] + "a"])
    return list(dict.fromkeys([every, last]))


class OrdinalReader(Rule):
    """``decimotercera`` → ``13.ª``, ``vigésimo primero`` / ``vigesimoprimero`` → ``21.º``; primero to décimo stay
    words."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        pairs = []
        for n in range(11, 1000):
            for said in _masculine(n):
                pairs.append((said, f"{n}.º"))
                pairs += [(fem, f"{n}.ª") for fem in _feminine(said)]
                for full, short in (("primero", "primer"), ("tercero", "tercer")):
                    if said.endswith(full):
                        pairs.append((said[: -len(full)] + short, f"{n}.er"))
        graph = pynini.string_map(pairs)
        return self.wrap(text(graph)).optimize()

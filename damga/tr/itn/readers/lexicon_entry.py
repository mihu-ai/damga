from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.data import load_tsv
from ....core.rules import Rule
from ....core.unicode import caps_variants, tr_lower

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "lexicon_entries.tsv"
BRANDS = pathlib.Path(__file__).resolve().parent.parent / "data" / "brands.tsv"
BRANDS_EXTRA = pathlib.Path(__file__).resolve().parent.parent / "data" / "brands_extra.tsv"

# Locative fraction numerators ("üçte bir" = 1/3) stay words instead of "3'te bir".  They must cost slightly more
# than a time reading so "saat üçte bir toplantı" keeps the time.
FRACTION_NUMERATORS = {"ikide": "2'de", "üçte": "3'te", "dörtte": "4'te", "beşte": "5'te", "altıda": "6'da",
                       "yedide": "7'de", "sekizde": "8'de", "dokuzda": "9'da", "onda": "10'da"}
FRACTION_TAILS = ["bir", "biri", "birini", "biridir"]


class LexiconEntryReader(Rule):
    name = "lexicon_entry"
    kind = "read"

    def build(self, variants: bool = False, custom: dict[str, str] | None = None, builtin: bool = True):
        pairs = (load_tsv(DATA) + load_tsv(BRANDS)) if builtin else []
        if builtin:
            seen = {a for a, _ in pairs}
            pairs += [(a, b) for a, b in load_tsv(BRANDS_EXTRA) if a not in seen]

        pairs += [(v, b) for a, b in list(pairs) for v in caps_variants(a)]
        branches = []
        if pairs:
            branches.append(pynini.union(*[pynini.cross(a, pynini.escape(b)) for a, b in pairs]))
        if custom:
            branches.append(pynutil.add_weight(
                pynini.union(*[pynini.cross(tr_lower(a.strip()), pynini.escape(b)) for a, b in custom.items()]), -0.1))
        if not branches:
            self._fst = None
            return
        if builtin:
            fractions = [f"{n} {t}" for n in FRACTION_NUMERATORS for t in FRACTION_TAILS]
            fractions += [v for f in list(fractions) for v in caps_variants(f)]
            branches.append(pynutil.add_weight(pynini.union(*[pynini.accep(f) for f in fractions]), 0.5))
            at_hour = [(f"saat {n} {t}", f"saat {d} {t}") for n, d in FRACTION_NUMERATORS.items() for t in FRACTION_TAILS]
            branches.append(pynutil.add_weight(pynini.union(*[pynini.cross(a, b) for a, b in at_hour]), 0.2))
        graph = pynini.union(*branches)

        SUFFIXES = ["i", "ı", "u", "ü", "yi", "yı", "yu", "yü", "e", "a", "ye", "ya", "de", "da", "te", "ta", "den", "dan", "ten", "tan",
                    "in", "ın", "un", "ün", "nin", "nın", "nun", "nün", "le", "la", "yle", "yla", "im", "ım", "um", "üm", "iniz", "ınız",
                    "unuz", "ünüz", "imiz", "ımız", "umuz", "ümüz", "ler", "lar", "leri", "ları", "lerde", "larda", "lere", "lara",
                    "lerden", "lardan", "si", "sı", "su", "sü", "ye", "ya", "deki", "daki", "teki", "taki", "miz", "mız", "niz", "nız",
                    "uyla", "üyle", "ıyla", "iyle", "yla", "yle", "la", "le", "ta", "te", "tan", "ten", "u", "ü", "ı", "i"]
        long_entries = [(a, b) for a, b in pairs if len(a.replace(" ", "")) >= 4]
        if long_entries:
            inflected = (pynini.union(*[pynini.cross(a, pynini.escape(b)) for a, b in long_entries]) + pynutil.delete(pynini.closure("'", 0, 1))
                         + pynutil.insert("'") + pynini.union(*sorted(set(SUFFIXES))))
            graph = pynini.union(graph, pynutil.add_weight(inflected, 0.2))
        return self.wrap(pynutil.insert('word="') + graph + pynutil.insert('"'))

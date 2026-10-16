from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule, drop_space, string_map
from .cardinal import CardinalReader

HOURS = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on", "on bir", "on iki",
         "on üç", "on dört", "on beş", "on altı", "on yedi", "on sekiz", "on dokuz", "yirmi", "yirmi bir",
         "yirmi iki", "yirmi üç", "yirmi dört"]

# The accusative (``dokuzu çeyrek geçe``) and dative (``ona çeyrek kala``) of every hour word, on its last word:
# ``on yediyi çeyrek geçe`` is 17:15, ``yirmi bire beş var`` 20:55.
_ACC_WORD = {"bir": "biri", "iki": "ikiyi", "üç": "üçü", "dört": "dördü", "beş": "beşi", "altı": "altıyı",
             "yedi": "yediyi", "sekiz": "sekizi", "dokuz": "dokuzu", "on": "onu", "yirmi": "yirmiyi"}
_DAT_WORD = {"bir": "bire", "iki": "ikiye", "üç": "üçe", "dört": "dörde", "beş": "beşe", "altı": "altıya",
             "yedi": "yediye", "sekiz": "sekize", "dokuz": "dokuza", "on": "ona", "yirmi": "yirmiye"}


def _inflect(word: str, table: dict[str, str]) -> str:
    head, _, last = word.rpartition(" ")
    return (head + " " if head else "") + table[last]


ACC = {w: _inflect(w, _ACC_WORD) for w in HOURS[1:]}
DAT = {w: _inflect(w, _DAT_WORD) for w in HOURS[1:]}

def _two(n: int) -> str:
    return f"{n:02d}"

class TimeReader(Rule):
    name = "time"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        hour = string_map([(w, _two(i)) for i, w in enumerate(HOURS)])
        minute = cardinal.two_digit @ pynini.union(*[_two(i) for i in range(1, 60)])
        # ``saat on beş`` is 15, not 10:05: after the tens words ``on``/``yirmi`` a single digit continues the
        # hour, so those hours only take two-digit minutes (``saat on beş kırk`` is still 15:40, and
        # ``saat dokuz beş`` 09:05).
        tens = string_map([("on", "10"), ("yirmi", "20")])
        hour_other = string_map([(w, _two(i)) for i, w in enumerate(HOURS) if w not in ("on", "yirmi")])
        minute_two = cardinal.two_digit @ pynini.union(*[_two(i) for i in range(10, 60)])
        m_two = pynutil.insert(' minutes="') + minute_two + pynutil.insert('"')
        h_tens = pynutil.insert('hours="') + tens + pynutil.insert('"')
        h = pynutil.insert('hours="') + hour_other + pynutil.insert('"')
        # Recognizers spell the full hour as ``sıfır sıfır`` and a leading-zero minute as ``sıfır beş``.
        zero_minute = pynini.union(pynini.cross("sıfır sıfır", "00"),
                                   pynutil.insert("0") + pynutil.delete("sıfır ") + cardinal.digit)
        m = pynutil.insert(' minutes="') + pynini.union(minute, zero_minute) + pynutil.insert('"')
        m_zero_tens = pynutil.insert(' minutes="') + zero_minute + pynutil.insert('"')
        keyword = pynutil.insert('word="') + pynini.accep("saat") + pynutil.insert('" ') + drop_space

        SUFFIXES = ["da", "de", "ta", "te", "dan", "den", "tan", "ten", "a", "e", "ya", "ye", "dır", "dir", "dur", "dür",
                    "tır", "tir", "tur", "tür", "ki", "daki", "deki", "taki", "teki", "ydı", "ydi", "tı", "ti"]
        suffix = pynini.closure(pynutil.insert(' suffix="') + pynini.union(*SUFFIXES) + pynutil.insert('"'), 0, 1)
        plain = pynini.union(
            h + drop_space + m + suffix,
            h_tens + drop_space + m_two + suffix,
            h_tens + drop_space + m_zero_tens + suffix,
            pynutil.insert('hours="') + hour + pynutil.insert('"') + pynutil.delete(" buçuk") + pynutil.insert(' minutes="30"') + suffix,
        )

        gece_min = pynini.union(pynini.cross("çeyrek", "15"), minute)
        gece = pynini.union(*[pynini.cross(ACC[w], _two(i)) for i, w in enumerate(HOURS) if w in ACC])
        gece_graph = pynutil.insert('hours="') + gece + pynutil.insert('" minutes="') + drop_space + gece_min + pynutil.insert('"') + pynutil.delete(" geçe")

        kala_branches = []
        var_map = pynini.union(*[pynini.cross(_two(k), _two(60 - k)) for k in range(5, 60, 5)])
        for i, w in enumerate(HOURS):
            if w not in DAT:
                continue
            prev = _two((i - 1) % 24)
            mins = pynini.union(pynini.cross("çeyrek", "45"), *[pynini.cross(HOURS[k], _two(60 - k)) for k in range(1, 60) if k < len(HOURS)])

            k_map = pynini.union(*[pynini.cross(_two(k), _two(60 - k)) for k in range(1, 60)])
            mins = pynini.union(pynini.cross("çeyrek", "45"), cardinal.two_digit @ k_map)
            # ``beşe on var`` is the same as ``beşe on kala``; ``var`` is only accepted after round minutes.
            var_mins = pynini.union(pynini.cross("çeyrek", "45"), cardinal.two_digit @ var_map)
            kala_branches.append(pynutil.insert('hours="' + prev + '" minutes="') + pynutil.delete(DAT[w]) + drop_space + mins + pynutil.insert('"') + pynutil.delete(" kala"))
            kala_branches.append(pynutil.insert('hours="' + prev + '" minutes="') + pynutil.delete(DAT[w]) + drop_space + var_mins + pynutil.insert('"') + pynutil.delete(" var"))
        kala_graph = pynini.union(*kala_branches)

        wh = pynini.union(*[pynini.cross(str(i), f"{i:02d}") for i in range(25)] + [pynini.accep(f"{i:02d}") for i in range(10)])
        wm = pynini.union(*[pynini.accep(f"{i:02d}") for i in range(60)])
        written = pynini.union(
            pynutil.insert('hours="') + wh + pynutil.insert('"') + pynutil.delete(pynini.union(".", ":")) + pynutil.insert(' minutes="') + wm + pynutil.insert('"') + suffix,
            pynutil.insert('hours="') + wh + pynutil.insert('"') + pynutil.delete(" buçuk") + pynutil.insert(' minutes="30"') + suffix,
        )
        graph = pynini.union(keyword + self.wrap(pynini.union(plain, written)), self.wrap(pynini.union(gece_graph, kala_graph)))
        return graph.optimize()

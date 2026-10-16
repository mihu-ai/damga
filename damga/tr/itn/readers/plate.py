from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule, drop_space, string_map
from .cardinal import CardinalReader

LETTER_NAMES = [("a", "A"), ("be", "B"), ("ce", "C"), ("de", "D"), ("e", "E"), ("fe", "F"), ("ge", "G"), ("he", "H"),
                ("ı", "I"), ("i", "I"), ("je", "J"), ("ke", "K"), ("ka", "K"), ("le", "L"), ("me", "M"), ("ne", "N"), ("o", "O"),
                ("pe", "P"), ("re", "R"), ("se", "S"), ("te", "T"), ("u", "U"), ("ve", "V"), ("ye", "Y"), ("ze", "Z")]
BARE = [(c, c.upper()) for c in "abcdefghjklmnoprstuvyz"]
PHONETIC = [("adana", "A"), ("bolu", "B"), ("ceyhan", "C"), ("denizli", "D"), ("edirne", "E"), ("fatsa", "F"),
            ("giresun", "G"), ("hatay", "H"), ("isparta", "I"), ("izmir", "I"), ("jandarma", "J"), ("kars", "K"),
            ("lüleburgaz", "L"), ("muş", "M"), ("niğde", "N"), ("ordu", "O"), ("polatlı", "P"), ("rize", "R"),
            ("sinop", "S"), ("tokat", "T"), ("uşak", "U"), ("van", "V"), ("yozgat", "Y"), ("zonguldak", "Z")]
# Two-letter unit abbreviations that follow a written number: "70 kg 180 cm" is not plate 70 KG 180.
UNIT_ABBREVIATIONS = {"km", "kg", "cm", "mm", "ml", "lt", "gr", "dk", "sn", "mb", "gb", "kb", "tb", "hz", "kw", "mg", "dm", "hp", "mt"}
AMBIGUOUS = {"ve", "de", "da", "e", "o", "i", "ı", "ne", "te", "se", "ye", "me", "ce"}

class PlateReader(Rule):
    name = "plate"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        province = pynini.union(cardinal.two_digit, DIGIT + DIGIT) @ pynini.union(*[f"{i:02d}" for i in range(1, 82)])
        AMB1 = {"ve", "de", "da", "e", "o", "a", "i", "ı", "ne", "te", "se", "ye", "me", "ce", "u"}
        single_all = LETTER_NAMES + BARE + PHONETIC + [("ı", "I"), ("i", "I")]
        anyl = string_map(single_all)
        safe1 = string_map([(a, b) for a, b in single_all if a not in AMB1])

        STOP2 = {"ve", "de", "da", "bu", "şu", "ne", "ki", "mi", "mı", "mu", "mü", "ya", "et", "ev", "at", "el", "en", "az", "ad", "ak", "al", "an", "ay", "er", "es", "un", "uy", "yz"} | {a for a, _ in LETTER_NAMES} | UNIT_ABBREVIATIONS
        glued = pynini.union(*[pynini.cross(w, w.upper().replace("I", "I")) for w in
                              [a + b for a in "abcdefghjklmnprstuvyz" for b in "abcdefghjklmnprstuvyz"] if w not in STOP2])
        UP = "ABCDEFGHIJKLMNPRSTUVYZ"
        caps = pynini.union(*[pynini.accep(c) for c in UP])
        caps_glued = pynini.union(caps + caps, caps + caps + caps)
        anyl = pynini.union(anyl, caps); safe1 = pynini.union(safe1, caps); glued = pynini.union(pynutil.add_weight(glued, 0.1), caps_glued)
        number = cardinal.graph_mixed @ (pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 3))
        sep = pynutil.delete(pynini.closure(",", 0, 1)) + drop_space

        # One letter is followed by 3-4 digits (34 A 1234); "70 m 1" or "10 m 4" are a length and a number, not plates.
        number_single = cardinal.graph_mixed @ (pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 2, 3))

        def body(letters: pynini.Fst, num: pynini.Fst = number) -> pynini.Fst:
            return (pynutil.insert('city="') + province + pynutil.insert('" letters="') + sep + letters
                    + pynutil.insert('" number="') + sep + num + pynutil.insert('"'))

        letters_multi = pynini.union(anyl + sep + anyl + pynini.closure(sep + anyl, 0, 1),
                                     glued + pynini.closure(sep + anyl, 0, 1), anyl + sep + glued)
        letters_single = pynutil.add_weight(safe1, 0.3)
        keyword = pynini.accep("plaka") + pynini.closure(pynini.union(*"mnsıi"), 0, 4)
        graph = pynini.union(
            self.wrap(pynini.union(body(letters_multi), body(letters_single, number_single))),
            pynutil.insert('word="') + keyword + pynutil.insert('" ') + drop_space + self.wrap(body(pynini.union(letters_multi, anyl))),
        )
        return graph.optimize()

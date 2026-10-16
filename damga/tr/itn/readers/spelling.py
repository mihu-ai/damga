from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import TR_LOWER, TR_UPPER, Rule

LETTER_NAMES = [("a", "a"), ("be", "b"), ("b", "b"), ("ce", "c"), ("c", "c"), ("çe", "ç"), ("ç", "ç"), ("de", "d"), ("d", "d"),
                ("e", "e"), ("fe", "f"), ("f", "f"), ("ge", "g"), ("g", "g"), ("he", "h"), ("h", "h"),
                ("ı", "ı"), ("i", "i"), ("je", "j"), ("j", "j"), ("ke", "k"), ("k", "k"), ("le", "l"), ("l", "l"), ("me", "m"), ("m", "m"),
                ("ne", "n"), ("n", "n"), ("o", "o"), ("ö", "ö"), ("pe", "p"), ("p", "p"), ("re", "r"), ("r", "r"), ("se", "s"), ("s", "s"),
                ("şe", "ş"), ("ş", "ş"), ("te", "t"), ("t", "t"), ("u", "u"), ("ü", "ü"), ("ve", "v"), ("v", "v"), ("ye", "y"), ("y", "y"),
                ("ze", "z"), ("z", "z"), ("ağ", "a"), ("ağa", "a")]
LETTER_NAMES += [(u, lo) for u, lo in zip("ABCÇDEFGĞHIJKLMNOÖPRSŞTUÜVYZ", "abcçdefgğhıjklmnoöprsştuüvyz")]

SPECIAL_NAMES = [("yumuşak ge", "ğ"), ("ğe", "ğ"), ("ku", "q"), ("dabılyu", "w"), ("iks", "x")]
UPPER = {"i": "İ", "ı": "I"}
CITIES = ("adana", "adıyaman", "afyon", "ağrı", "amasya", "ankara", "antalya", "artvin", "aydın", "balıkesir", "bilecik", "bingöl",
          "bitlis", "bolu", "burdur", "bursa", "çanakkale", "çankırı", "çorum", "denizli", "diyarbakır", "edirne", "elazığ", "erzincan",
          "erzurum", "eskişehir", "gaziantep", "giresun", "gümüşhane", "hakkari", "hatay", "isparta", "mersin", "istanbul", "izmir",
          "kars", "kastamonu", "kayseri", "kırklareli", "kırşehir", "kocaeli", "konya", "kütahya", "malatya", "manisa", "kahramanmaraş",
          "mardin", "muğla", "muş", "nevşehir", "niğde", "ordu", "rize", "sakarya", "samsun", "siirt", "sinop", "sivas", "tekirdağ",
          "tokat", "trabzon", "tunceli", "şanlıurfa", "uşak", "van", "yozgat", "zonguldak", "aksaray", "bayburt", "karaman", "kırıkkale",
          "batman", "şırnak", "bartın", "ardahan", "iğdır", "yalova", "karabük", "kilis", "osmaniye", "düzce", "ceyhan", "cizre",
          "fatsa", "fethiye", "lüleburgaz", "lefkoşa", "ödemiş", "polatlı", "pamukkale", "ünye", "jandarma", "urfa", "maraş")
ALPHABET = "abcçdefgğhıijklmnoöprsştuüvyz"
STOP_MNEMONICS = pynini.union("ve", "ile", "de", "da", "bu", "şu", "o", "ki", "mi", "mı", "mu", "mü", "ne", "bir", "ya", "ama", "çok",
                              "en", "her", "hem", "için", "gibi", "kadar", "ben", "sen", "biz", "siz", "ama", "veya", "yani")
INITIAL = {c: c for c in ALPHABET} | {"â": "a", "î": "i", "û": "u"}

class SpellingReader(Rule):
    name = "spelling"
    kind = "read"

    def build(self, variants: bool = False):
        tok = pynini.closure(TR_LOWER, 1)
        vowel = pynini.union(*"aeıioöuü")
        poss = pynini.union("ın", "in", "un", "ün", "nın", "nin", "nun", "nün")
        apos = pynutil.delete(pynini.closure("'", 0, 1))
        opt_space = pynutil.delete(pynini.closure(" ", 0, 1))

        poss_mark = pynutil.delete(pynini.closure(pynini.union(pynini.accep("'"), pynini.accep(" ")) + poss, 0, 1))

        si_base = pynini.union("si", "sı", "su", "sü", "harfi", "harfı")
        si_tail = pynini.closure(vowel, 0, 1) + si_base + pynini.closure(pynini.union("si", "sı"), 0, 1)
        si_tail_se = pynini.union(si_tail, "se")
        low = pynini.union(TR_LOWER, *"âîû")
        s_clipped = pynini.closure(vowel, 0, 1) + pynini.union("s", "S")
        letter_name = pynini.union(*[pynini.accep(a) for a, _ in LETTER_NAMES])

        loose = pynini.union(pynini.closure(low, 0, 3) + apos + opt_space + si_tail,
                             pynini.closure(low, 1, 3) + pynini.accep("'") + vowel,
                             pynini.accep("ağzı"))
        named_si = letter_name + apos + opt_space + si_tail
        named_si_n = letter_name + apos + opt_space + si_tail + pynini.accep("n")
        named_bare = letter_name

        caps = (pynini.closure(TR_UPPER, 1, 4) + pynini.closure(pynini.union(TR_LOWER, "'"), 0, 3)
                + pynini.closure(pynini.accep(" ") + pynini.union("S", "s", "es", "ES", "si", "sı"), 0, 1))

        caps_short = (pynini.closure(TR_UPPER, 1, 2) + pynini.closure(pynini.union(TR_LOWER, "'"), 0, 3)
                      + pynini.closure(pynini.accep(" ") + pynini.union("S", "s", "es", "ES", "si", "sı"), 0, 1))
        tail_glued = pynini.union(loose, named_si, pynutil.add_weight(caps_short, 0.1))
        tail_spaced = pynini.union(tail_glued, named_si_n, pynutil.add_weight(s_clipped, 0.2))

        tail_no_poss = pynini.union(named_si, named_si_n, pynutil.add_weight(caps_short, 0.1), pynutil.add_weight(s_clipped, 0.2),
                                    si_tail, pynini.accep("ağzı"),
                                    pynini.closure(low, 1, 3) + pynini.accep("'") + vowel)

        bare_ok = pynini.difference(named_bare, pynini.union("ve", "ne", "o", "de", "da", "se", "ki", "mi"))
        tail_after_poss = pynini.union(tail_spaced, pynutil.add_weight(bare_ok, 0.05), pynutil.add_weight(caps, 0.1),
                                       pynutil.add_weight(vowel + pynini.accep("se"), 0.3))

        city = pynini.union(*[pynini.accep(c) for c in CITIES])

        split_rest = pynutil.add_weight(pynini.closure(low, 0, 1) + pynini.accep(" ") + tok, 0.3)

        def unit(upper: bool):
            def up(c):
                return UPPER.get(c, c.upper()) if upper else c

            def mnemonic(c):
                whole = pynini.difference(pynini.accep(c) + pynini.closure(low), STOP_MNEMONICS)
                return pynini.union(pynini.compose(whole, pynini.cross(c, up(INITIAL[c])) + pynutil.delete(pynini.closure(low))),
                                    pynini.cross(c, up(INITIAL[c])) + pynutil.delete(split_rest))
            poss_sep = pynutil.delete(pynini.union(pynini.accep("'"), pynini.accep(" ")) + poss) + apos
            gap1 = pynutil.delete(pynini.closure(pynini.union(" ", ","), 1, 2))
            by_mnemonic = pynini.union(*[
                mnemonic(c) + pynini.union(

                    poss_sep + pynini.union(gap1 + pynutil.delete(tail_after_poss), pynutil.delete(tail_glued),
                                            pynutil.delete(pynini.union(*[pynini.accep(ch) for ch in ALPHABET]))),
                    apos + gap1 + pynutil.delete(tail_no_poss),
                    pynutil.delete(pynini.union(poss, pynini.accep("'") + pynini.union(poss, "n"))) + pynutil.delete(tail_glued))

                for c in INITIAL])

            names = pynini.union(*[pynini.cross(a, up(b)) for a, b in LETTER_NAMES])
            cons_names = pynini.union(*[pynini.cross(a, up(b)) for a, b in LETTER_NAMES if len(a) == 2 and a[0] not in "aeıioöuü"])
            by_name = pynutil.add_weight(pynini.union(
                names + pynutil.delete(pynini.union("'", " ")) + opt_space + pynutil.delete(si_tail_se),
                cons_names + pynutil.delete(si_tail)), 0.1)

            spec = pynini.union(*[pynini.cross(a, up(b)) for a, b in SPECIAL_NAMES])
            by_special = pynutil.add_weight(
                pynutil.delete(pynini.closure(tok + poss_mark + apos + pynini.accep(" "), 0, 1)) + spec + apos + opt_space
                + pynutil.delete(pynini.closure(si_tail, 0, 1)), -0.2)

            by_city = pynutil.add_weight(pynini.union(*[
                pynini.cross(c, up(c)) + pynutil.delete(pynini.closure(low, 1)) + poss_mark for c in ALPHABET]), 0.6)
            return pynini.union(by_mnemonic, by_name, by_special), by_city

        sep = pynutil.delete(pynini.closure(pynini.union(" ", ",", ".", ":", ";"), 1, 3))
        first_u, _ = unit(True)
        later_u, bare_u = unit(False)
        bare_city = pynini.project(city + pynini.closure(pynini.union("'", " "), 0, 1) + pynini.closure(poss, 0, 1), "input")
        bare_u = pynini.compose(bare_city, bare_u)

        graph = first_u + pynini.closure(sep + later_u, 1) + pynini.closure(sep + bare_u, 0, 1)
        return self.wrap(pynutil.insert('text="') + pynini.union(graph, self._yani_code(), self._letter_names())
                         + pynutil.insert('"')).optimize()

    @staticmethod
    def _letter_names():
        """Letter-by-letter spelling with the letter names: "ye ı le me a ze" -> YILMAZ, "de a yumuşak ge" -> DAĞ,
        "ka me te dört yedi bir" -> KMT471.  At least three letters, two of them consonant names that are no ordinary
        word (be, ce, çe, fe, ge, je, ke, le, me, pe, re, se, şe, te, ze), so "a de ne" or "ye me ve içme" or the laugh "he he he" never fires; "yumuşak ge" alone is enough, and one clear name in four or more letters."""
        clear = {"be": "B", "ce": "C", "çe": "Ç", "fe": "F", "ge": "G", "je": "J", "ke": "K", "ka": "K", "le": "L",
                 "me": "M", "pe": "P", "re": "R", "er": "R", "se": "S", "şe": "Ş", "te": "T", "ze": "Z",
                 "dabılyu": "W", "iks": "X", "ku": "Q"}
        weak = {"a": "A", "e": "E", "ı": "I", "i": "İ", "o": "O", "ö": "Ö", "u": "U", "ü": "Ü", "de": "D", "ne": "N", "ve": "V", "ye": "Y", "he": "H"}
        def m(d):
            return pynini.union(*[pynini.cross(pynini.union(k, k.capitalize()), v) for k, v in d.items()])
        strong, soft = m(clear), m(weak)
        gap = pynutil.delete(pynini.closure(pynini.union(" ", ",", "-"), 1, 2))
        any_letter = pynini.union(strong, soft)
        # strong ... strong with at least three letters overall
        seq = (pynini.closure(soft + gap, 0, 3) + strong + pynini.closure(gap + any_letter, 0) + gap + strong
               + pynini.closure(gap + soft, 0, 3))
        # one clear consonant name is enough once the word has at least four letters: "de e re ye a" -> DERYA
        four = pynini.closure(pynini.union(*"ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZWXQ"), 4)
        one_strong = pynini.closure(soft + gap, 0, 4) + strong + pynini.closure(gap + soft, 0, 4)
        seq = pynini.union(seq, pynini.compose(one_strong, four))
        soft_g = pynini.cross(pynini.union("yumuşak ge", "Yumuşak ge"), "Ğ")
        seq = pynini.union(seq, pynini.closure(any_letter + gap, 1) + soft_g + pynini.closure(gap + any_letter, 0))
        three = pynini.closure(pynini.union(*"ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZWXQ"), 3)
        seq = pynini.compose(seq, three)
        digit = pynini.union(*[pynini.cross(w, d) for w, d in [("sıfır", "0"), ("bir", "1"), ("iki", "2"), ("üç", "3"), ("dört", "4"),
                                                                ("beş", "5"), ("altı", "6"), ("yedi", "7"), ("sekiz", "8"), ("dokuz", "9")]])
        return pynutil.add_weight(seq + pynini.closure(gap + digit, 0), 0.3)

    @staticmethod
    def _yani_code():
        """Code read letter by letter with an example word: "K yani Kayseri, M yani Muş, T yani Tokat, dört yedi bir" -> KMT471.
        Each unit is a letter (bare, or its name: ke, me, te, ye ...) + "yani" + a word starting with that letter, so a plain
        "a yani anladın mı" never fires; at least two units are required. Spoken digits right after the code are appended."""
        word_char = pynini.union(TR_LOWER, TR_UPPER, *"âîû")
        gap = pynutil.delete(pynini.closure(pynini.union(" ", ",", ".", ":", ";"), 1, 3))
        names = {}
        for spoken, letter in LETTER_NAMES:
            if spoken.islower():
                names.setdefault(letter, set()).update({spoken, spoken.capitalize(), spoken.upper()})
                if len(spoken) == 2 and spoken[1] == "e":  # recognizer splits the name: "m e" for me
                    names[letter].add(spoken[0] + " e")
        units = []
        for c in ALPHABET:
            heard = pynini.union(*[pynini.accep(s) for s in sorted(names.get(c, {c}) | {c, UPPER.get(c, c.upper())})])
            starts = pynini.union(c, UPPER.get(c, c.upper()))
            example = starts + pynini.closure(word_char, 1) + pynini.closure(pynini.accep("'") + pynini.closure(word_char, 1), 0, 1)
            units.append(pynini.cross(heard, UPPER.get(c, c.upper())) + gap + pynutil.delete("yani") + gap + pynutil.delete(example))
        unit = pynini.union(*units)
        digit = pynini.union(*[pynini.cross(w, d) for w, d in [("sıfır", "0"), ("bir", "1"), ("iki", "2"), ("üç", "3"), ("dört", "4"),
                                                                ("beş", "5"), ("altı", "6"), ("yedi", "7"), ("sekiz", "8"), ("dokuz", "9")]]
                              + [pynini.accep(d) for d in "0123456789"])
        return unit + pynini.closure(gap + unit, 1) + pynini.closure(gap + digit, 0)

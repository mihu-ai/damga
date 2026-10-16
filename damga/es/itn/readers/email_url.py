from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ....en.tn.readers.email_url import TLDS
from ...numbers import DIGIT_WORD
from .cardinal import text


class EmailUrlReader(Rule):
    """``ana punto garcia arroba gmail punto com`` → ``ana.garcia@gmail.com``, spelled out too (``g mail`` →
    ``gmail``); the address must end in a known top-level domain."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzñ")
        word = pynini.difference(pynini.closure(letter, 2), pynini.project(DIGIT_WORD, "output"))   # "tres" is 3
        # spelled letters and digits run together: "a s d f uno dos tres" → "asdf123"
        single = pynini.union(letter, pynini.invert(DIGIT_WORD))
        run = single + pynini.closure(pynutil.delete(" ") + single)
        part = pynini.union(word, run)
        # after "arroba" a spelled start may run into a word: "g mail" → "gmail", "e bay" → "ebay"
        host_part = pynini.union(part, run + pynutil.delete(" ") + word)
        join = pynini.union(pynini.cross(" punto ", "."), pynini.cross(" guion bajo ", "_"), pynini.cross(" guion ", "-"))
        name = part + pynini.closure(join + part, 0, 6)
        tld = part @ pynini.union(*TLDS, "gob")
        host = host_part + pynini.closure(pynini.cross(" punto ", ".") + host_part, 0, 3) + pynini.cross(" punto ", ".") + tld
        email = name + pynini.cross(" arroba ", "@") + host
        www = pynini.cross(pynini.union("uve doble uve doble uve doble punto ", "doble ve doble ve doble ve punto ",
                                        "doble uve doble uve doble uve punto ", "w w w punto "), "www.")
        scheme = pynini.union(pynini.cross("hache te te pe ese dos puntos barra barra ", "https://"),
                              pynini.cross("hache te te pe dos puntos barra barra ", "http://"))
        path = pynini.closure(pynini.cross(" barra ", "/") + part, 0, 4)
        url = pynini.closure(scheme, 0, 1) + www + host + path
        return self.wrap(text(pynini.union(email, url))).optimize()

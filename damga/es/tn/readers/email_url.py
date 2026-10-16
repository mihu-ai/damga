from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ....en.tn.readers.email_url import TLDS
from ...numbers import DIGIT_WORD
from .cardinal import text


class EmailUrlReader(Rule):
    """``ana.garcia@gmail.com`` → ``ana punto garcia arroba gmail punto com``, ``www.europa.eu`` → ``uve doble uve
    doble uve doble punto europa punto eu``, ``@usuario`` → ``arroba usuario``."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        word = pynini.closure(letter, 1)
        digit = pynutil.insert(" ") + DIGIT_WORD + pynutil.insert(" ")
        sep = pynini.union(pynini.cross(".", " punto "), pynini.cross("-", " guion "), pynini.cross("_", " guion bajo "))
        part = pynini.closure(pynini.union(word, digit), 1)
        tld = pynini.union(*TLDS)
        domain = part + pynini.closure(pynini.cross(".", " punto ") + part) + pynini.cross(".", " punto ") + tld
        # after "@" or a scheme any top-level domain will do (abc@gmail.abc, http://www.diario.com.sm)
        any_domain = part + pynini.closure(pynini.cross(".", " punto ") + part, 1)
        email = part + pynini.closure(sep + part) + pynini.cross("@", " arroba ") + any_domain
        handle = pynini.cross("@", "arroba ") + part + pynini.closure(sep + part)        # @usuario
        www = pynini.cross("www.", "uve doble uve doble uve doble punto ")
        scheme = pynini.union(pynini.cross("https://", "hache te te pe ese dos puntos barra barra "),
                              pynini.cross("http://", "hache te te pe dos puntos barra barra "))
        path = pynini.closure(pynini.cross("/", " barra ") + pynini.closure(pynini.union(word, digit, sep), 1), 0, 6)
        url = pynini.union(scheme + www + any_domain, pynutil.add_weight(scheme + any_domain, 0.01), www + domain) + path + pynini.closure(
            pynutil.delete("/"), 0, 1)
        return self.wrap(text(pynini.union(email, url, handle, pynutil.add_weight(domain + path, 0.5)))).optimize()

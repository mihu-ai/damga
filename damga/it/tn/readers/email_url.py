from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ....en.tn.readers.email_url import TLDS as COMMON_TLDS
from ...numbers import DIGIT_WORD
from .cardinal import text

# beyond the common ones: neighbouring and other European countries
TLDS = sorted(set(COMMON_TLDS) | {"sm", "va", "mx", "br", "ar", "cl", "jp", "cn", "in", "lu", "si", "hr", "ro", "hu",
                                  "sk", "bg", "biz", "app", "dev", "tv", "pro", "museum"})


class EmailUrlReader(Rule):
    """``mario.rossi@gmail.com`` → ``mario punto rossi chiocciola gmail punto com``, ``www.europa.eu`` → ``vu vu vu
    punto europa punto eu``.  A top-level domain in capitals is said as in small letters (``.IT`` → ``punto it``)."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        word = pynini.closure(letter, 1)
        digit = pynutil.insert(" ") + DIGIT_WORD + pynutil.insert(" ")
        sep = pynini.union(pynini.cross(".", " punto "), pynini.cross("-", " trattino "),
                           pynini.cross("_", " trattino basso "))
        part = pynini.closure(pynini.union(word, digit), 1)
        local = part + pynini.closure(sep + part)
        tld = pynini.union(*TLDS, *[pynini.cross(t.upper(), t) for t in TLDS])
        domain = part + pynini.closure(pynini.cross(".", " punto ") + part) + pynini.cross(".", " punto ") + tld
        email = local + pynini.cross("@", " chiocciola ") + domain
        handle = pynini.cross("@", "chiocciola ") + local
        www = pynini.cross("www.", "vu vu vu punto ")
        scheme = pynini.union(pynini.cross("https://", "acca ti ti pi esse due punti barra barra "),
                              pynini.cross("http://", "acca ti ti pi due punti barra barra "))
        # a path piece ends in a letter or digit: a full stop after it ends the sentence
        path = pynini.closure(pynini.cross("/", " barra ") + local, 0, 6)
        # after the scheme, www is said vu vu vu, not read as the first part of the domain
        after_scheme = pynini.union(www, pynutil.add_weight(pynini.accep(""), 0.1))
        url = pynini.union(scheme + after_scheme, www) + domain + path + pynini.closure(pynutil.delete("/"), 0, 1)
        return self.wrap(text(pynini.union(email, url, handle, pynutil.add_weight(domain + path, 0.5)))).optimize()

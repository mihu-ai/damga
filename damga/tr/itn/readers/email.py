from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.data import load_tsv
from ....core.rules import CHAR, DIGIT, TR_LOWER, TR_TO_ASCII, Rule, drop_space
from .cardinal import CardinalReader

UPPER_TO_LOWER = pynini.union(*[pynini.cross(u, lo) for u, lo in zip("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZQWX", "abcçdefgğhıijklmnoöprsştuüvyzqwx")])

DOMAINS = pathlib.Path(__file__).resolve().parent.parent / "data" / "domains.tsv"
PROVIDERS = pathlib.Path(__file__).resolve().parent.parent / "data" / "email_providers.tsv"

ET_WORDS = ["mehmet", "ahmet", "demet", "internet", "paket", "sepet", "market", "ücret", "şirket", "hizmet", "kısmet", "davet",
            "cennet", "millet", "devlet", "nimet", "ismet", "saadet", "adet", "evet", "zahmet", "rahmet", "ticaret", "kuvvet",
            "sohbet", "hikmet", "kıymet", "minnet", "cumhuriyet", "hürriyet", "emniyet", "niyet", "sanat", "et"]

STOP = ["adresim", "adres", "adresi", "adresiniz", "adrese", "adresine", "mail", "mailim", "mailimi", "maili", "eposta",
        "posta", "postam", "postanız", "için", "şu", "bu", "ve", "ile", "yazın", "gönderin", "edin", "not", "olsun",
        "olarak", "kayıtlı", "iletin", "bilgileri", "faturayı", "teklifi", "kayıt", "numaram", "telefon", "hepsi", "doğru", "mı", "mi", "mu", "mü",
        "eurosta", "epostanız", "epostam", "postanız", "postam", "meylimi", "meylim", "meyl", "meil", "mel", "adresin", "adresine", "adresimi",
        "alo", "merhaba", "evet", "hayır", "tamam", "peki", "lütfen", "şimdi", "ben", "benim", "adım", "ismim", "yani", "işte", "efendim", "pardon",
        "bilgilere", "bilgiler", "teklif", "fatura", "adrese", "adresi", "kayıta", "meylemi", "meyilimi", "meyle", "meylime"]
TLDS = ["com", "net", "org", "ai", "io", "tr", "edu", "gov", "info", "co", "biz", "me", "dev", "app", "eu", "de", "uk", "bel", "av", "k12", "gen"]

class EmailReader(Rule):
    name = "email"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        lower_word = pynini.closure(pynini.union(TR_LOWER, DIGIT), 1)
        any_word = pynini.closure(pynini.union(TR_LOWER, UPPER_TO_LOWER, DIGIT), 1)
        word_acc = pynini.difference(lower_word, pynini.union(*STOP)).optimize()
        word = (any_word @ word_acc).optimize()
        number = cardinal.graph_no_zero
        comma = pynutil.delete(pynini.closure(pynini.union(",", "."), 0, 1))
        glued = pynutil.add_weight(pynini.accep(""), 0.3)
        def sep_of(spoken, out):
            return pynini.union(
                pynutil.delete(" ") + pynini.cross(spoken, out) + comma + pynutil.delete(" "),
                glued + comma + pynini.union(pynutil.delete(" "), pynini.accep("")) + pynini.cross(spoken, out) + comma + pynini.union(pynutil.delete(" "), pynini.accep("")),
            )
        sep = pynini.union(sep_of("nokta", "."), sep_of("alt çizgi", "_"), sep_of("altçizgi", "_"), sep_of("altı çizgi", "_"), sep_of("alt tire", "_"), sep_of("altı tire", "_"),
                           sep_of("al çizgi", "_"), sep_of("tire", "-"), pynutil.add_weight(sep_of("tir", "-"), 0.25),
                           pynutil.add_weight(sep_of("tira", "-"), 0.15), sep_of("artı", "+"))

        digits = DIGIT + pynini.closure(pynutil.delete(pynini.closure(pynini.union(".", "-"), 0, 1)) + DIGIT)
        ocomma = pynutil.delete(pynini.closure(",", 0, 1))

        spoken_digit = pynini.union(cardinal.digit, cardinal.zero)
        spoken_digits = spoken_digit + pynini.closure(ocomma + drop_space + spoken_digit)
        from .plate import PHONETIC
        fon = pynini.union(*[pynini.cross(a, b.lower()) for a, b in PHONETIC])
        odot = pynutil.delete(pynini.closure(pynini.union(",", "."), 0, 1))
        phonetic = fon + pynini.closure(odot + drop_space + fon, 1)
        mixed = pynini.closure(DIGIT) + pynutil.delete("0") + drop_space + pynini.union(cardinal.digit)
        num_tail = pynini.union(number, digits, spoken_digits, pynutil.add_weight(mixed, 0.2))
        pg = pynini.union(pynutil.add_weight(pynini.union(word, phonetic), 0.01) + pynini.closure(ocomma + drop_space + num_tail), num_tail)
        # a role word may be set off by a recognizer comma ("iletişim, Özdemir"); an ordinary word may not
        role = pynini.union("iletişim", "destek", "bilgi", "satış", "info", "muhasebe", "müşteri", "sipariş")
        local = pynini.union(pg, pynutil.add_weight(word + drop_space + pg, 0.6),
                             pynutil.add_weight(role + ocomma + drop_space + pg, 0.6)) + pynini.closure(sep + pg)
        TLD_ALIAS = {"kom": "com", "cam": "com", "kam": "com", "kum": "com", "con": "com", "john": "com", "kon": "com", "ton": "com", "tre": "tr", "tier": "tr", "trar": "tr", "tere": "tr",
                     "ko": "com", "cım": "com", "kım": "com", "kem": "com", "te re": "tr", "ti ar": "tr", "trem": "tr", "teer": "tr", "tiar": "tr", "t-r": "tr", "t r": "tr", "te-re": "tr", "i": "ai", "ay": "ai", "aı": "ai", "a i": "ai"}
        tld_plain = pynini.union(pynini.union(*TLDS), *[pynini.cross(a, b) for a, b in TLD_ALIAS.items()])
        # recognizers capitalize the last word of a sentence-like span ("nokta TR", "nokta Com")
        tld = pynini.union(tld_plain, pynutil.add_weight(
            pynini.closure(pynini.union(TR_LOWER, UPPER_TO_LOWER, " ", "-"), 1) @ tld_plain, 0.1))
        aliases = pynini.union(*[pynini.cross(a, b) for a, b in load_tsv(DOMAINS)])
        one = (any_word @ pynini.difference(word_acc, pynini.union(*TLD_ALIAS, "nokta", "et", "dot", "dat", "tir"))).optimize()

        label = pynini.union(one + pynini.closure(pynutil.add_weight(pynutil.delete(pynini.closure(pynini.union(",", " "), 1, 2)), 0.6) + one, 0, 2), pynutil.add_weight(aliases, -0.05))

        opt = pynutil.delete(pynini.closure(pynini.union(",", " ", "."), 0, 2))

        dot = pynini.union(pynini.cross(" nokta ", "."), pynutil.add_weight(opt + pynini.cross(pynini.union("dot", "dat", "dad", "dott"), ".") + opt, 0.2), pynutil.add_weight(opt + pynini.cross("nokta", ".") + opt, 0.3),
                           pynutil.add_weight(pynini.accep("."), 0.3))

        t_word = pynini.accep("t") + pynini.closure(TR_LOWER, 1, 3)
        cc = pynini.union(tld, pynutil.add_weight(pynini.cross(t_word, "tr"), 0.3))

        label1 = pynini.union(one, pynutil.add_weight(aliases, -0.05))
        dot_spoken = pynini.union(pynini.cross(" nokta ", "."), pynutil.add_weight(opt + pynini.cross(pynini.union("dot", "dat", "dad", "dott"), ".") + opt, 0.2),
                                  pynutil.add_weight(opt + pynini.cross("nokta", ".") + opt, 0.3))
        segment = pynini.union(label1 + dot, label + dot_spoken)
        tld_real = pynini.union(*TLDS)
        # a recognizer glues the last spoken label to the TLD but keeps a space inside a two-word name
        # ("örnek mağaza.com" → ornekmagaza.com); such a label costs a little more than a single word
        label_two = one + pynutil.add_weight(pynutil.delete(pynini.closure(pynini.union(",", " "), 1, 2)), 0.4) + one
        last = pynini.union(label + dot_spoken + tld, label1 + pynutil.add_weight(pynini.accep("."), 0.3) + tld_real,
                            label_two + pynutil.add_weight(pynini.accep("."), 0.3) + tld_real)
        domain = pynini.closure(segment) + last + pynini.closure(dot + cc, 0, 1)

        opt_p = pynutil.delete(pynini.closure(pynini.union(",", ".", " "), 0, 3))
        req_p = pynutil.delete(pynini.closure(pynini.union(",", ".", " "), 1, 3))
        at = pynini.union(pynini.cross(" et ", "@"), pynini.cross(" at ", "@"), pynini.cross(" ad ", "@"),
                          pynutil.add_weight(req_p + pynini.cross("et", "@") + opt_p, 0.3),
                          pynutil.add_weight(req_p + pynini.cross("evet", "@") + req_p, 0.9),
                          pynutil.add_weight(pynini.cross(" e ", "@"), 0.5), pynutil.add_weight(pynini.cross("'e ", "@"), 0.5),
                          pynutil.add_weight(opt_p + pynini.cross(pynini.union("ed", "ett"), "@") + opt_p, 0.4))

        glued_et = pynutil.add_weight(pynini.cross("et", "@") + pynutil.delete(pynini.closure(pynini.union(" ", ",", "."), 1, 3)), 0.5)
        local_glued = pynini.difference(pynini.closure(pynini.union(TR_LOWER, DIGIT), 3), pynini.union(*[w[:-2] for w in ET_WORDS if len(w) > 2]))

        known = pynini.union(*sorted({b for _, b in load_tsv(DOMAINS)} | {"gmail", "hotmail", "outlook", "yahoo", "icloud", "protonmail", "proton", "yandex", "msn", "live", "aol", "zoho", "gmx",
            "mynet", "superonline", "ttmail", "amazon", "google", "microsoft", "apple", "meta", "facebook", "aws", "azure",
            "turkcell", "vodafone", "turktelekom", "etstur", "ets", "mihu", "trendyol", "hepsiburada", "getir", "yemeksepeti",
            "garanti", "garantibbva", "akbank", "isbank", "ziraatbank", "yapikredi", "halkbank", "qnb", "denizbank", "thy",
            "turkishairlines", "flypgs", "migros", "acibadem", "memorial", "medicalpark", "koc", "sabanci", "arcelik", "vestel",
            "hilton", "marriott", "rixos", "booking", "airbnb"}))
        providers = [a for a, _ in load_tsv(PROVIDERS) if len(a) >= 4]
        if providers:
            known = pynini.union(known, pynini.union(*providers))
        known_domain = pynini.union(known, aliases) + dot + tld + pynini.closure(dot + tld, 0, 1)
        no_et = pynutil.add_weight(local + pynini.cross(" ", "@") + known_domain, 0.8)

        glued_head = pynini.union(local_glued, word + pynini.closure(ocomma + drop_space + pynini.union(number, digits), 1))
        glued_head = pynini.union(glued_head, pynutil.add_weight(word + drop_space + glued_head, 0.6),
                                  pynutil.add_weight(role + ocomma + drop_space + glued_head, 0.6))

        glued_e = pynutil.add_weight(pynini.cross("e", "@") + pynutil.delete(" "), 0.9)
        email = pynini.union(local + at + domain, (pynini.closure(pg + sep) + glued_head) + glued_et + domain, no_et,
                             (pynini.closure(pg + sep) + glued_head) + glued_e + known_domain)

        spoken_inside = pynini.closure(CHAR) + pynini.union("nokta", "dot", "dat", "www") + pynini.closure(CHAR)
        web = pynini.union(pynini.cross("www nokta ", "www.") + domain, pynutil.add_weight(pynini.compose(spoken_inside, domain), 0.8))
        # ``https iki nokta bölü bölü mihu nokta ai`` → https://mihu.ai (optionally followed by ``bölü yol`` path parts)
        scheme = pynini.union(pynini.accep("https"), pynini.accep("http")) + pynini.cross(
            pynini.union(" iki nokta bölü bölü ", " iki nokta slash slash ", " iki nokta eğik çizgi eğik çizgi "), "://")
        path = pynini.closure(pynini.cross(pynini.union(" bölü ", " slash "), "/") + one, 0, 4)
        url = scheme + pynini.union(pynini.cross("www nokta ", "www.") + domain, domain) + path
        graph = pynini.union(email, web, url) @ TR_TO_ASCII
        return self.wrap(pynutil.insert('address="') + graph + pynutil.insert('"')).optimize()

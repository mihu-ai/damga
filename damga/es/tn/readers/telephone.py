from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import BEFORE_NOUN, FEMININE
from ...numbers import DIGITS_SPOKEN, TWO
from .cardinal import text

_MARKS = pynini.union(FEMININE, BEFORE_NOUN)
_MARK = pynutil.delete(_MARKS).ques               # the pre-hook marks a group before a noun
_FIRST = pynini.union(*"6789")                    # Spanish numbers start with 6, 7, 8 or 9
_PAUSE = ", "
_CHARS = pynini.union(DIGIT, " ", "-", ".", "+", "(", ")")
_SIGMA = pynini.closure(_CHARS).optimize()


def _keyword() -> pynini.Fst:
    """``Tel.``, ``Tel.:``, ``Teléfono``, ``Tlf.``, ``Móvil``, ``Fax``, ``llame al``, ``llámenos al`` — kept as
    written."""
    word = pynini.union(
        "Tel.", "tel.", "Tel", "tel", "TEL.", "Tlf.", "tlf.", "Tlf", "tlf", "Tlfno.", "tlfno.", "Tfno.", "tfno.",
        "Telf.", "telf.", "Teléfono", "teléfono", "TELÉFONO", "Teléfonos", "teléfonos", "Móvil", "móvil", "MÓVIL",
        "Fax", "fax", "FAX")
    call = pynini.union("Llame", "llame", "Llámenos", "llámenos", "Llámanos", "llámanos", "Llama", "llama", "Llámame",
                        "llámame", "Llamar", "llamar", "Marque", "marque", "Marca", "marca") + " al"
    return (pynini.union(word + pynini.closure(":", 0, 1), call) + " ").optimize()


def _group() -> pynini.Fst:
    """One written group: two digits as a number (``34`` → *treinta y cuatro*, ``05`` → *cero cinco*), any other
    length digit by digit (``912`` → *nueve uno dos*)."""
    pair = pynini.union((pynini.difference(DIGIT, "0") + DIGIT) @ TWO, ("0" + DIGIT) @ DIGITS_SPOKEN)
    other = pynini.union(DIGIT, pynini.closure(DIGIT, 3, 4)) @ DIGITS_SPOKEN
    return _MARK + pynini.union(pair, other)


def _unspaced() -> pynini.Fst:
    """An unspaced number: nine digits split 3-3-3 (``912345678`` → *nueve uno dos, tres cuatro cinco, seis siete
    ocho*), any other length digit by digit."""
    three = DIGIT ** 3 @ DIGITS_SPOKEN
    spanish = three + pynutil.insert(_PAUSE) + three + pynutil.insert(_PAUSE) + three
    other = pynini.difference(pynini.closure(DIGIT, 6, 15), DIGIT ** 9) @ DIGITS_SPOKEN
    return _MARK + pynini.union(spanish, other)


def _prefix() -> pynini.Fst:
    """``+34`` → *más treinta y cuatro*, ``0034`` → *cero cero treinta y cuatro*: the country code as a number."""
    code = (pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 2)) @ pynini.union(
        TWO, (DIGIT ** 3) @ DIGITS_SPOKEN)
    return pynini.union(pynini.cross("+", "más "), pynini.cross("00", "cero cero ")) + code


def _shapes() -> tuple[pynini.Fst, pynini.Fst]:
    """The written shapes (without the pre-hook marks) of a number standing on its own (the 9-digit Spanish ones,
    or an international one) and of a number after a keyword (six digits or more).  Groups are separated by spaces,
    or by dashes (``+34-912-345-678``); a first group in parentheses is an area code (``+34 (91) 234 56 78``)."""
    sp = " "
    spaced = pynini.union(
        _FIRST + DIGIT ** 2 + sp + DIGIT ** 3 + sp + DIGIT ** 3,
        _FIRST + DIGIT ** 2 + sp + DIGIT ** 2 + sp + DIGIT ** 2 + sp + DIGIT ** 2,
        _FIRST + DIGIT + sp + DIGIT ** 3 + sp + DIGIT ** 2 + sp + DIGIT ** 2).optimize()
    dashed = pynini.project(pynini.cdrewrite(pynini.cross("-", " "), "", "", _SIGMA) @ spaced, "input")
    dashed = pynini.intersect(dashed, pynini.closure(pynini.union(DIGIT, "-"))).optimize()
    spanish = pynini.union(spaced, dashed, _parenthesized(spaced), _FIRST + DIGIT ** 8)
    glued = pynini.union("+34", "0034") + _FIRST + DIGIT ** 8           # +34612345678
    prefix = pynini.union("+", "00") + pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 2)
    sep = pynini.union(" ", "-", ".")
    group = pynini.union(DIGIT, pynini.closure(DIGIT, 2, 4))
    grouped = group + pynini.closure(sep + group, 1)
    six = pynini.closure(pynini.closure(pynini.union(sep, "(", ")"), 0, 2) + DIGIT, 6)   # six digits or more in all
    grouped = pynini.union(grouped, _parenthesized(grouped))
    any_number = pynini.union(pynini.intersect(grouped, six).optimize(), pynini.closure(DIGIT, 6, 15))
    spaced_intl = pynini.intersect(group + pynini.closure(" " + group, 1), six).optimize()
    after_prefix = pynini.union(sp, "-")
    # three dash-separated groups or more, nine digits in all, are a telephone wherever they stand (123-123-5678,
    # (123) 123-5678); a date has eight (17-02-2008, 2024-03-15)
    dgroup = pynini.closure(DIGIT, 2, 4)
    nine = pynini.closure(pynini.closure(pynini.union("-", " ", "(", ")"), 0, 2) + DIGIT, 9)
    dashed_any = pynini.intersect(pynini.union(dgroup + pynini.closure("-" + dgroup, 2),
                                               "(" + DIGIT ** 3 + ") " + DIGIT ** 3 + "-" + DIGIT ** 4), nine).optimize()
    alone = pynini.union((pynini.union("+34", "0034") + after_prefix).ques + spanish, glued,
                         prefix + sp + pynini.difference(spaced_intl, spanish))
    # a dashed number takes the pre-hook marks before a word ("123-123-5678 ext. 12")
    sigma = pynini.closure(pynini.union(_CHARS, _MARKS)).optimize()
    unmark = pynini.cdrewrite(pynutil.delete(_MARKS), "", "", sigma)
    alone = pynini.union(alone, pynini.project(unmark @ ((prefix + after_prefix).ques + dashed_any), "input"))
    keyword = pynini.union((prefix + after_prefix).ques + any_number, glued)
    return alone.optimize(), keyword.optimize()


def _parenthesized(shape: pynini.Fst) -> pynini.Fst:
    """``shape`` with its first group (two or three digits, then a space) in parentheses: ``(91) 234 56 78``."""
    paren = pynini.cross("(", "") + pynini.closure(DIGIT, 2, 3) + pynini.cross(")", "") + " " + _SIGMA
    return pynini.project(paren @ shape, "input").optimize()


class TelephoneReader(Rule):
    """Telephone numbers, a pause (``, ``) between the written groups: ``+34 612 34 56 78`` → ``más treinta y
    cuatro, seis uno dos, treinta y cuatro, …``.  Spanish and international numbers are read anywhere, other shapes
    only after a keyword (``Tel.:``); a number before a noun (``912 345 678 euros``) is a number."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        sep = pynini.union(pynini.cross(" ", _PAUSE), pynini.cross("-", _PAUSE), pynini.cross(".", _PAUSE))
        first = pynini.union(_group(), pynutil.delete("(") + _group() + pynutil.delete(")"))
        body = pynini.union(first + pynini.closure(sep + _group(), 1), _unspaced())
        glued = pynini.union("+34", "0034") @ _prefix() + pynutil.insert(_PAUSE) + (_FIRST + DIGIT ** 8) @ _unspaced()
        prefix = _prefix() + pynini.union(pynini.cross(" ", _PAUSE), pynini.cross("-", _PAUSE))
        reading = pynini.union(pynini.closure(prefix, 0, 1) + body, glued).optimize()
        alone, keyword = _shapes()
        sigma = pynini.closure(pynini.union(_CHARS, _MARKS)).optimize()
        unmark = pynini.cdrewrite(pynutil.delete(_MARKS), "", "", sigma)
        marked_keyword = pynini.project(unmark @ keyword, "input")
        # an IP address: four groups of up to three digits, read digit by digit (a thousands number has groups of
        # three after the first: 1.000.000.000)
        octet = pynini.closure(DIGIT, 1, 3)
        dot = pynini.accep(".")
        ip = pynini.difference(octet + (dot + octet) ** 3, octet + (dot + DIGIT ** 3) ** 3)
        ip = ip @ (DIGITS_SPOKEN + (pynini.cross(".", " punto ") + DIGITS_SPOKEN) ** 3)
        graph = pynini.union(alone @ reading, _keyword() + (marked_keyword @ reading), ip)
        return self.wrap(text(graph)).optimize()

from __future__ import annotations

import pynini
from pynini.lib import pynutil, utf8

CHAR = utf8.VALID_UTF8_CHAR
SIGMA = pynini.closure(CHAR).optimize()
DIGIT = pynini.union(*"0123456789").optimize()
NONZERO_DIGIT = pynini.union(*"123456789").optimize()
TR_LOWER = pynini.union(*"abcçdefgğhıijklmnoöprsştuüvyzqwx").optimize()
TR_UPPER = pynini.union(*"ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZQWX").optimize()
TR_ALPHA = pynini.union(TR_LOWER, TR_UPPER).optimize()
TR_ALNUM = pynini.union(TR_ALPHA, DIGIT).optimize()
SPACE = pynini.accep(" ")
WHITE_SPACE = pynini.union(" ", "\t", "\n", "\r", " ").optimize()
NON_SPACE = pynini.difference(CHAR, WHITE_SPACE).optimize()
NON_QUOTE = pynini.difference(CHAR, '"').optimize()

ESCAPED_CHAR = pynini.union(pynini.difference(NON_SPACE, pynini.union('"', "\\")), pynini.cross('"', '\\"'), pynini.cross("\\", "\\\\")).optimize()
UNESCAPED_CHAR = pynini.union(pynini.difference(CHAR, pynini.union('"', "\\")), pynini.cross('\\"', '"'), pynini.cross("\\\\", "\\")).optimize()
PUNCT = pynini.union(*[pynini.escape(c) for c in '.,;:!?()[]"\'-…']).optimize()

drop_space = pynutil.delete(" ")
squeeze_space = pynini.cross(pynini.closure(WHITE_SPACE, 1), " ")
drop_optional_space = pynutil.delete(pynini.closure(" ", 0, 1))
add_space = pynutil.insert(" ")

TR_TO_ASCII = pynini.cdrewrite(
    pynini.union(*[pynini.cross(a, b) for a, b in zip("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")]),
    "", "", SIGMA).optimize()

def string_map(pairs, weight: float | None = None) -> pynini.Fst:
    fst = pynini.union(*[pynini.cross(a, b) for a, b in pairs])
    if weight is not None:
        fst = pynutil.add_weight(fst, weight)
    return fst.optimize()

def word_list(words) -> pynini.Fst:
    return pynini.union(*words).optimize()

def strip_leading_zeros() -> pynini.Fst:
    return pynini.union(
        pynutil.delete(pynini.closure("0")) + NONZERO_DIGIT + pynini.closure(DIGIT),
        pynini.cross(pynini.closure("0", 1), "0"),
    ).optimize()

def group_thousands(min_digits: int = 4) -> pynini.Fst:
    """``25600`` → ``25.600``; numbers shorter than ``min_digits`` stay as they are (``min_digits=5``: ``1950``)."""
    triple = pynutil.insert(".") + DIGIT + DIGIT + DIGIT
    head = pynini.union(DIGIT, DIGIT + DIGIT, DIGIT + DIGIT + DIGIT)
    grouped = head + pynini.closure(triple)
    if min_digits <= 4:
        return grouped.optimize()
    return pynini.union(pynini.closure(DIGIT, 1, min_digits - 1),
                        pynini.closure(DIGIT, min_digits) @ grouped).optimize()

class Rule:
    """One grammar.  A subclass names its class (``name``), says whether it reads or writes (``kind``) and returns
    its transducer from ``build``; the constructor arguments go to ``build``.  ``build`` may return None when there
    is nothing to match (an empty word list), and ``built`` tells."""

    name: str = ""
    kind: str = ""

    def __init__(self, *args, **kwargs):
        self._fst: pynini.Fst | None = self.build(*args, **kwargs)

    def build(self, *args, **kwargs) -> pynini.Fst | None:
        raise NotImplementedError

    @property
    def fst(self) -> pynini.Fst:
        if self._fst is None:
            raise RuntimeError(f"{self.name}/{self.kind}: grammar not built")
        return self._fst

    @property
    def built(self) -> bool:
        return self._fst is not None

    def wrap(self, fst: pynini.Fst) -> pynini.Fst:
        return (pynutil.insert(f"{self.name}(") + fst + pynutil.insert(")")).optimize()

    def unwrap(self, fst: pynini.Fst) -> pynini.Fst:
        return (pynutil.delete(f"{self.name}(") + fst + pynutil.delete(")")).optimize()

    def far_name(self) -> str:
        return f"{self.kind}_{self.name}"

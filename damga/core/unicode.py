from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

_WS = re.compile(r"[ \t\r\n   ]+")
_APOS = {"’": "'", "‘": "'", "ʼ": "'", "`": "'", "´": "'"}

def tr_lower(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()

def tr_upper(text: str) -> str:
    return text.replace("i", "İ").replace("ı", "I").upper()

def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)

_CAPS = re.compile(r"^([^\wÇĞİÖŞÜ]*)([A-ZÇĞİÖŞÜ]{1,3})([^\wçğıöşü]*)$")
_CAPS_LOWER = {"ET", "TL", "AT", "VE", "DE", "DA", "NO", "AI", "AY", "OK", "TC", "E", "O", "A", "I", "İ", "KI", "MI", "MU", "MÜ", "BU", "ŞU", "NE", "DIR", "DİR"}

@dataclass(frozen=True)
class Casing:
    """How a language lower-cases its input before the grammars and which short all-capital tokens (acronyms such
    as ``TL``, ``AB``) it keeps.  ``TURKISH`` is the default; a language passes its own to the engine."""
    lower: Callable[[str], str] = tr_lower
    upper: Callable[[str], str] = tr_upper
    caps: re.Pattern[str] = _CAPS
    caps_lower: frozenset[str] = field(default_factory=lambda: frozenset(_CAPS_LOWER))


TURKISH = Casing()


def caps_variants(spoken: str) -> list[str]:
    import itertools
    opts = []
    for tok in spoken.split(" "):
        up = tr_upper(tok)
        opts.append([tok, up] if re.fullmatch(r"[a-zçğıöşü]{1,3}", tok) and up not in _CAPS_LOWER else [tok])
    if sum(len(o) > 1 for o in opts) > 4:
        return [" ".join(o[-1] for o in opts)]
    return [" ".join(c) for c in itertools.product(*opts) if " ".join(c) != spoken]

def preprocess(text: str, lowercase: bool = True, keep_caps: bool = True, casing: Casing = TURKISH) -> str:
    t = nfc(text)
    for a, b in _APOS.items():
        t = t.replace(a, b)
    t = _WS.sub(" ", t).strip()
    if not lowercase:
        return t
    lower = casing.lower
    if not keep_caps:
        return lower(t)

    long_words = [w for w in t.split(" ") if sum(ch.isalpha() for ch in w) >= 4]
    if long_words and all(w == casing.upper(w) for w in long_words):
        return lower(t)
    out = []
    for tok in t.split(" "):
        m = casing.caps.match(tok)
        if m and m.group(2) not in casing.caps_lower:
            out.append(m.group(1) + m.group(2) + lower(m.group(3)))
        else:
            out.append(lower(tok))
    return " ".join(out)

_CASE_WINDOW = 400


def restore_case(original: str, lowered: str, output: str, casing: Casing = TURKISH) -> str:
    """Put the original casing back on the words the grammar left as they were.  A word the grammar only
    recased (``istanbul'da`` → ``İstanbul'da``) keeps the grammar's casing unless the original was ALL CAPS."""
    import difflib
    if original == lowered:
        return output
    orig, low, out = original.split(" "), lowered.split(" "), output.split(" ")
    if len(orig) != len(low):
        return output
    res = list(out)
    out_low = [casing.lower(t) for t in out]
    i = j = 0
    while i < len(low) and j < len(out):
        last = i + _CASE_WINDOW >= len(low) or j + _CASE_WINDOW >= len(out)
        a, b = (low[i:], out_low[j:]) if last else (low[i:i + _CASE_WINDOW], out_low[j:j + _CASE_WINDOW])
        limit = len(a) if last else len(a) - _CASE_WINDOW // 4
        end = later = None
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
            if tag == "replace" and i1 < limit:
                # a rewritten word (vatsap → WhatsApp) keeps the capital it had
                o, w = orig[i + i1], out[j + j1]
                plain = w.rstrip(".,;:!?") and all(c.isalpha() or c == "'" for c in w.rstrip(".,;:!?"))
                # (a word with a capital inside, ``iPhone'umun``, keeps its own casing)
                if plain and o[:1] == casing.upper(o[:1]) and o[:1].isalpha() and o != casing.upper(o) \
                        and w == casing.lower(w):
                    res[j + j1] = casing.upper(w[:1]) + w[1:]      # not an e-mail or a number: fatma.kaya@… stays
                continue
            if tag != "equal":
                continue
            if i1 >= limit:
                later = later or (i1, j1)
                continue
            i2, j2 = min(i2, limit), j1 + min(i2, limit) - i1
            for k in range(i2 - i1):
                o, w = orig[i + i1 + k], out[j + j1 + k]
                if w == low[i + i1 + k] or (o == casing.upper(o) and o != casing.lower(o)):
                    res[j + j1 + k] = o
            end = (i2, j2)
        if last:
            break
        di, dj = end or later or (len(a), len(b))
        i, j = i + di, j + dj
    return " ".join(res)

def reattach_quotes(source: str, output: str) -> str:
    if source.count('"') != output.count('"'):
        return output
    src_pos = [i for i, ch in enumerate(source) if ch == '"']
    parts = output.split('"')
    res = parts[0]
    for k, nxt in enumerate(parts[1:]):
        i = src_pos[k]
        if i > 0 and source[i - 1] != " ":
            res = res.rstrip(" ")
        res += '"'
        if i + 1 < len(source) and source[i + 1] != " ":
            nxt = nxt.lstrip(" ")
        res += nxt
    return res

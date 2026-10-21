"""Spoken shell syntax for dictating terminal commands (pure Python, no pynini).

Symbols are said as words and the result is typed as a command line: ``ls tire lah`` -> ``ls -lah``,
``cd slash tmp`` -> ``cd /tmp``, ``git çift tire version`` -> ``git --version``, ``cat dosya nokta txt`` ->
``cat dosya.txt``, ``ps aux boru grep python`` -> ``ps aux | grep python``.  Run it after ITN, on text meant for a
shell: it lower-cases (ASCII ``i`` for ``I``/``İ``), drops the recognizer's punctuation and joins symbols to their
neighbours, so it must never run on ordinary prose ("eksi", "nokta", "bölü" are Turkish words there).
"""
from __future__ import annotations

import re

# Every symbol and the ways it is said (Turkish, English, and how the recognizer spells the English).
SHELL_SYMBOLS = [
    ("--", ["çift tire", "iki tire", "2 tire", "tire tire", "çift eksi", "iki eksi", "2 eksi", "eksi eksi",
            "çift minus", "minus minus", "maynus maynus", "double dash", "dabıl daş", "çift çizgi", "çift kısa çizgi"]),
    ("-", ["tire", "eksi", "minus", "maynus", "mainus", "dash", "daş", "hyphen", "kısa çizgi", "çizgi", "kesme çizgisi",
           "çıkarma işareti"]),
    ("/", ["slash", "slaş", "eğik çizgi", "bölü", "taksim", "bölme işareti", "forward slash"]),
    ("\\", ["ters eğik çizgi", "ters slash", "ters slaş", "backslash", "bekslaş", "bek slaş", "ters bölü"]),
    (":", ["iki nokta üst üste", "2 nokta üst üste", "iki nokta", "2 nokta", "colon", "kolon"]),
    (";", ["noktalı virgül", "semicolon", "semikolon"]),
    (".", ["nokta", "dot", "dat"]),
    (",", ["virgül", "comma"]),
    ("_", ["alt çizgi", "alt tire", "underscore", "andırskor", "andırskór"]),
    ("|", ["boru", "pipe", "payp", "dikey çizgi", "düz çizgi"]),
    (">=", ["büyük eşit", "büyük eşittir", "büyüktür eşittir", "büyüktür veya eşittir", "büyük ya da eşit",
            "greater equal"]),
    ("<=", ["küçük eşit", "küçük eşittir", "küçüktür eşittir", "küçüktür veya eşittir", "küçük ya da eşit",
            "less equal"]),
    ("==", ["eşit eşit", "eşittir eşittir", "çift eşittir", "çift eşit", "iki eşittir", "2 eşittir", "equals equals"]),
    ("!=", ["eşit değil", "eşit değildir", "ünlem eşittir", "ünlem eşit", "not equal", "bang equals"]),
    ("+=", ["artı eşittir", "artı eşit", "plus equals"]),
    ("-=", ["eksi eşittir", "eksi eşit", "tire eşittir", "minus equals"]),
    ("=>", ["eşittir büyüktür", "kalın ok", "fat arrow"]),
    ("->", ["tire büyüktür", "eksi büyüktür", "ok işareti", "arrow"]),
    ("||", ["çift boru", "boru boru", "veya veya", "or or", "çift pipe"]),
    ("<<", ["çift küçüktür", "küçüktür küçüktür", "iki küçüktür"]),
    ("**", ["çift yıldız", "yıldız yıldız", "iki yıldız", "üssü işareti"]),
    ("++", ["artı artı", "çift artı", "plus plus"]),
    ("*=", ["çarpı eşittir", "yıldız eşittir"]),
    ("/=", ["bölü eşittir", "slash eşittir"]),
    ("^", ["üzeri", "üssü", "şapka", "caret", "keret"]),
    ("*", ["çarpı", "kere işareti", "times"]),
    ("%", ["mod", "modülo", "modulo", "kalan işareti"]),
    (">>", ["çift büyüktür", "büyüktür büyüktür", "iki büyüktür", "2 büyüktür"]),
    (">", ["büyüktür", "büyüktür işareti", "greater than"]),
    ("<", ["küçüktür", "küçüktür işareti", "less than"]),
    ("&&", ["ve ve", "çift ampersand", "ampersand ampersand", "and and", "end end"]),
    ("&", ["ampersand", "ampersant", "ve işareti", "and işareti"]),
    ("*", ["yıldız", "asterisk", "asteriks", "star"]),
    ("~", ["tilde", "tilda", "tilt", "ev dizini", "home dizini"]),
    ("=", ["eşittir", "eşit", "equals", "eşit işareti"]),
    ("+", ["artı", "plus", "plas", "toplama işareti"]),
    ("$", ["dolar", "dolar işareti", "dollar"]),
    ("@", ["et işareti", "at işareti", "kuyruklu a"]),
    ("#", ["diyez", "kare işareti", "hashtag", "hash", "heş"]),
    ("%", ["yüzde işareti", "percent"]),
    ("!", ["ünlem", "ünlem işareti", "bang"]),
    ("?", ["soru işareti"]),
    ('"', ["çift tırnak", "tırnak", "quote"]),
    ("'", ["tek tırnak", "kesme işareti", "apostrof"]),
    ("(", ["parantez aç", "parantezi aç", "açık parantez"]),
    (")", ["parantez kapat", "parantezi kapat", "parantez kapa", "kapalı parantez"]),
    ("[", ["köşeli parantez aç", "köşeli aç"]),
    ("]", ["köşeli parantez kapat", "köşeli kapat"]),
    ("{", ["süslü parantez aç", "süslü aç"]),
    ("}", ["süslü parantez kapat", "süslü kapat"]),
    ("", ["boşluk", "space", "speys"]),  # a separator: "ls boşluk tire lah" -> ls -lah
]
_SHELL_WORDS = sorted(((spoken, symbol) for symbol, forms in SHELL_SYMBOLS for spoken in forms),
                      key=lambda pair: -len(pair[0].split()))
# Always on their own ("a | b", "a >= b"); |, ||, &&, &, ; start a new command.
_SPACED = {"|", "||", ">", ">>", "<", "<<", "&&", "&", ";", ">=", "<=", "==", "!=", "+=", "-=", "*=", "/=", "=>",
           "->"}
# Between two numbers these are arithmetic and get spaces ("2 + 3", "10 / 2"); elsewhere they glue ("-la", "/tmp").
_MATH = {"+", "-", "*", "/", "%", "^", "**"}
_GLUE_NEXT = {"-", "--", "$", "~", "\\", "/", ".", "=", "_", ":", "@", "+", "(", "[", "{", "#", "%", ","}
_GLUE_BOTH = {"=", "_", ":", "@"}
_GLUE_PREV = {")", "]", "}", ",", "++"}       # closing: "(a b)", "a,b", "i++"
_QUOTES = {'"', "'"}                           # opening glues to the next word, closing to the last one
# Words after which "." is a path of its own ("git add ."), not a file extension.
_DOT_ALONE_AFTER = {"add", "rm", "cd", "ls", "cp", "mv", "open", "code", "find", "grep", "du", "tree", "source",
                    "chmod", "chown", "git", "diff", "cursor", "vim", "nvim", "explorer", "start"}


# How the recognizer tends to write command names said aloud, at the start of a command.
_COMMAND_ALIASES = sorted([
    ("el es", "ls"), ("eles", "ls"), ("les", "ls"), ("si di", "cd"), ("sidi", "cd"), ("ce de", "cd"), ("cede", "cd"),
    ("pi dabılyu di", "pwd"), ("pe ve de", "pwd"), ("kat", "cat"), ("ket", "cat"), ("em vi", "mv"), ("si pi", "cp"),
    ("ar em", "rm"), ("em ke dir", "mkdir"), ("gid", "git"), ("pip", "pip"), ("en pi em", "npm"), ("pi es", "ps"),
], key=lambda pair: -len(pair[0].split()))


# Letters spelled out, Turkish and English names: "tire el a haş" -> "-lah".
LETTER_NAMES = {
    "a": "a", "be": "b", "ce": "c", "çe": "ç", "de": "d", "e": "e", "fe": "f", "ge": "g", "he": "h", "haş": "h",
    "ı": "ı", "i": "i", "je": "j", "ke": "k", "ka": "k", "ha": "h", "le": "l", "el": "l", "me": "m", "em": "m", "ne": "n",
    "en": "n", "o": "o", "ö": "ö", "pe": "p", "re": "r", "er": "r", "se": "s", "es": "s", "şe": "ş", "te": "t",
    "u": "u", "ü": "ü", "ve": "v", "ye": "y", "ze": "z", "kü": "q", "kû": "q", "iks": "x", "ikis": "x", "eks": "x",
    "dabılyu": "w", "dablyu": "w", "dabliyu": "w", "çift ve": "w",
    "ey": "a", "bi": "b", "si": "c", "di": "d", "ef": "f", "ci": "g", "eyç": "h", "eyc": "h", "ay": "i",
    "cey": "j", "key": "k", "pi": "p", "kyu": "q", "ar": "r", "ti": "t", "yu": "u", "vi": "v", "vay": "y",
    "zi": "z", "zet": "z", "zed": "z",
}


def _spell(tokens):
    """Joins spelled letters into one word: after "-" / "--" / "+" ("tire el a haş" -> -lah, "tire l" -> -l), when
    two or more follow each other and one is a letter name ("el a haş" -> lah), or three or more letters
    ("p a s s w d" -> passwd). A lone "a" or "cp a b" stays as said."""
    out, k = [], 0
    while k < len(tokens):
        kind, value, spoken = tokens[k]
        run = []
        while k + len(run) < len(tokens) and tokens[k + len(run)][0] == "word" and (
                tokens[k + len(run)][1] in LETTER_NAMES or re.fullmatch(r"[a-zçğıöşü]", tokens[k + len(run)][1])):
            run.append(tokens[k + len(run)][1])
        after_dash = bool(out) and out[-1][0] == "sym" and out[-1][1] in ("-", "--", "+")  # -lah, --x, +x
        named = sum(len(w) > 1 for w in run)
        # The recognizer itself often writes spelled letters as letters: "p a s s w d".
        if run and (after_dash or (len(run) >= 2 and named >= 1) or len(run) >= 3):
            joined = "".join(LETTER_NAMES.get(w, w) for w in run)
            out.append(("word", joined, joined))
            k += len(run)
            continue
        out.append((kind, value, spoken))
        k += 1
    return out


def _is_number(word):
    return re.fullmatch(r"[\d.,]+|[a-z]", word) is not None and any(c.isdigit() for c in word) or word in ("x", "y", "n")


def _tokens(text):
    """("sym", symbol, spoken) / ("word", word, word) of a spoken command, spelled letters already joined."""
    text = text.replace("I", "i").replace("İ", "i").lower()
    text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", text)   # Damga's "8.000" is 8000 here
    text = re.sub(r"[,!?…]|\.(?=\s|$)", " ", text)      # the recognizer's punctuation
    glued = r"(tire|slaş|slash|maynus|minus)"  # said fast these stick to the next word: "estireler"
    text = re.sub(r"(?<=\w)(?<!back)(?<!bek)" + glued + r"(?=\w|\s|$)", r" \1 ", text)
    text = re.sub(r"(?<=\s)" + glued + r"(?=\w)", r"\1 ", " " + text).strip()
    text = re.sub(r"\bçift ve\b", "dabılyu", text)  # "w" said as two words
    words, tokens = text.split(), []
    for spoken, name in _COMMAND_ALIASES:  # only as the first word of a command
        n = len(spoken.split())
        for at in [0] + [k + 1 for k, w in enumerate(words) if w in ("boru", "pipe", "payp", "|", "||", "&&", ";")]:
            if words[at:at + n] == spoken.split():
                words[at:at + n] = [name]
    i = 0
    while i < len(words):
        for spoken, symbol in _SHELL_WORDS:
            n = len(spoken.split())
            if words[i:i + n] == spoken.split():
                if symbol:
                    tokens.append(("sym", symbol, spoken))
                i += n
                break
        else:
            tokens.append(("word", words[i], words[i]))
            i += 1
    return _spell(tokens)


def spell_letters(text):
    """Only joins spelled letters and fixes command names, keeping everything else as said:
    "pi ey es es dabılyu di" -> "passwd", "ls tire el a haş" -> "ls tire lah". Run it before ITN, whose own
    spelling rules would read some of these letters differently; then ITN, then `shell_form`."""
    return " ".join(spoken if kind == "sym" else value for kind, value, spoken in _tokens(text))


def shell_form(text):
    """Spoken command -> shell text: "LS tire lah" -> "ls -lah", "cd slash tmp" -> "cd /tmp",
    "cat dosya nokta txt" -> "cat dosya.txt", "ps aux boru grep python" -> "ps aux | grep python"."""
    tokens = [(kind, value) for kind, value, _ in _tokens(text)]
    out, prev, quotes = "", None, 0
    for k, (kind, value) in enumerate(tokens):
        after = tokens[k + 1] if k + 1 < len(tokens) else None
        if value in _SPACED and kind == "sym":
            out, prev = out.rstrip() + " " + value + " ", (kind, value)
            continue
        if (kind == "sym" and value in _MATH and prev and prev[0] == "word" and _is_number(prev[1])
                and after and after[0] == "word" and _is_number(after[1])):
            out, prev = out.rstrip() + " " + value, ("word", value)  # "2 + 3": the next number gets its space
            continue
        piece = "" if out.endswith(" ") else out.split(" ")[-1]      # what is typed right before
        command = re.split(r"(?:\|\|? |&& |& |; )", out)[-1].split()  # the command it belongs to
        is_name = len(command) == 1 and re.fullmatch(r"\w+", piece) is not None  # "cd", "git"
        glue = False
        if kind == "sym" and value in _QUOTES:
            quotes += 1
            closing = quotes % 2 == 0
            out += value if closing or not out or out.endswith(" ") else " " + value
            prev = (kind, value if not closing else ")")  # an opening quote glues to what follows
            if closing:
                prev = ("word", value)
            continue
        if prev and not (prev[0] == "sym" and prev[1] in _SPACED):
            pkind, pvalue = prev
            if pkind == "sym" and pvalue in _QUOTES:
                glue = True                       # '"merhaba'
            elif kind == "sym" and value in _GLUE_PREV:
                glue = True                       # "a)", "a,b"
            elif pkind == "sym" and pvalue in _GLUE_NEXT:
                glue = True                       # "-lah", "/tmp", ".txt", "~/", "$HOME"
            elif kind == "sym" and value in _GLUE_BOTH:
                glue = True                       # "a=b", "dosya_adi", "localhost:8000"
            elif kind == "sym" and value in ("(", "["):
                glue = pkind == "word" and not is_name  # "print(1)", "a[0]", but "echo (a b)"
            elif kind == "sym" and value == "/":
                # "src slash main" -> src/main, but "cd slash tmp" -> cd /tmp and "ls -la /tmp"
                glue = pkind == "sym" or not (is_name or piece.startswith("-"))
            elif kind == "sym" and value == ".":
                # "dosya nokta txt" -> dosya.txt, but "git add nokta" -> git add . and "cd nokta nokta" -> cd ..
                glue = pkind == "sym" or (not is_name and pvalue not in _DOT_ALONE_AFTER
                                          and after is not None and after[0] == "word")
        out += value if glue or not out or out.endswith(" ") else " " + value
        prev = (kind, value)
    return re.sub(r" {2,}", " ", out).strip()



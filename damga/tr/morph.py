"""Turkish inflection helpers shared by the grammars (pure Python, no pynini import).

Builds the suffixed forms of a word from vowel harmony, the final consonant and softening (``dört`` → ``dördü``).
"""
from __future__ import annotations

VOWELS = "aeıioöuü"
_BACK = set("aıou")
_HARD = set("çfhkpsşt")
# Final-consonant softening before a vowel-initial suffix.
_SOFTEN = {"dört": "dörd"}


def case_suffixes(word: str) -> list[tuple[str, str]]:
    """``(surface, suffix)`` pairs for the case endings of ``word``, e.g. ``("altıda", "da")``.

    The genitive is left out on purpose: ``altının`` is also *of the gold* and ``onun`` is *his/hers*.
    """
    last_v = [c for c in word if c in VOWELS][-1]
    a = "a" if last_v in _BACK else "e"
    i = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}[last_v]
    d = "t" if word[-1] in _HARD else "d"
    ends_vowel = word[-1] in VOWELS
    y = "y" if ends_vowel else ""
    soft = _SOFTEN.get(word, word)
    forms = [
        (word + d + a, d + a),                # altıda, beşte
        (word + d + a + "n", d + a + "n"),    # altıdan, beşten
        (word + d + a + "ki", d + a + "ki"),  # altıdaki
        (soft + y + a, y + a),                # altıya, dörde, üçe
        (soft + y + i, y + i),                # altıyı, dördü, beşi
        (word + y + "l" + a, y + "l" + a),    # altıyla, beşle
        (word + d + i + "r", d + i + "r"),    # altıdır, beştir
    ]
    return forms


def _harmony(word: str) -> tuple[str, str]:
    last_v = [c for c in word if c in VOWELS][-1]
    a = "a" if last_v in _BACK else "e"
    i = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}[last_v]
    return a, i


def more_suffixes(word: str) -> dict[str, list[tuple[str, str]]]:
    """Inflections beyond the case endings (genitive, possessive, lik, li, plural, past), grouped by kind, as
    ``(surface, suffix)`` pairs like ``case_suffixes``.

    Many of these are also ordinary words (``onun``, ``ikili``), so grammars use them alone only where unambiguous."""
    a, i = _harmony(word)
    ends_vowel = word[-1] in VOWELS
    soft = _SOFTEN.get(word, word)
    d = "t" if word[-1] in _HARD else "d"
    out: dict[str, list[tuple[str, str]]] = {}
    gen = ("n" + i + "n") if ends_vowel else (i + "n")
    out["genitive"] = [((word if ends_vowel else soft) + gen, gen)]
    poss = ("s" + i) if ends_vowel else i
    stem = word if ends_vowel else soft
    out["possessive"] = [(stem + poss + rest, poss + rest)
                         for rest in ("", "n" + i, "n" + i + "n", "n" + a, "nd" + a, "nd" + a + "n", "nd" + a + "ki")]
    out["lik"] = [(word + "l" + i + "k", "l" + i + "k")]
    out["li"] = [(word + "l" + i, "l" + i)]
    pa, pi = ("a", "ı") if a == "a" else ("e", "i")
    pl = "l" + pa + "r"
    out["plural"] = [(word + pl + rest, pl + rest)
                     for rest in ("", pa, "d" + pa, "d" + pa + "n", "d" + pa + "ki", pi, pi + "n", pi + "n" + pa, pi + "nd" + pa)]
    past = [("yd" + i) if ends_vowel else (d + i), ("ym" + i + "ş") if ends_vowel else ("m" + i + "ş")]
    out["past"] = [(word + p, p) for p in past]
    return out


# A suffix after an abbreviation follows its letter reading (``TL'ye``), so ``reinflect`` rebuilds it on the spoken word.
_KINDS = [  # (kind, written forms), checked in order; the y/n/s buffer letters decide between look-alikes
    ("locative_ki", "daki deki taki teki"),
    ("ablative", "dan den tan ten"),
    ("locative", "da de ta te"),
    ("genitive", "nın nin nun nün ın in un ün"),
    ("instrumental", "yla yle la le"),
    ("lik", "lık lik luk lük"),
    ("copula", "dır dir dur dür tır tir tur tür"),
    ("plural", "lar ler"),
    ("possessive", "sı si su sü"),
    ("dative", "ya ye a e"),
    ("accusative", "yı yi yu yü ı i u ü"),
]
SUFFIX_KIND = {form: kind for kind, forms in _KINDS for form in forms.split()}
_POSSESSED = {"Türk lirası": "Türk lira"}   # compounds that already end in the possessive (-sı)


def reinflect(word: str, suffix: str) -> str | None:
    """``word`` with the case of the written ``suffix`` in its own harmony (``("kuruş", "den")`` → ``kuruştan``);
    None for an unknown suffix."""
    kind = SUFFIX_KIND.get(suffix)
    if kind is None:
        return None
    if word in _POSSESSED:                       # Türk lirası + case: the n buffer after the possessive
        stem = _POSSESSED[word]
        a, i = _harmony(word)
        return {
            "locative_ki": word + "nd" + a + "ki", "ablative": word + "nd" + a + "n", "locative": word + "nd" + a,
            "genitive": word + "n" + i + "n", "instrumental": word + "yl" + a, "lik": stem + "l" + i + "k",
            "copula": word + "d" + i + "r", "plural": stem + "l" + a + "r" + i, "possessive": word,
            "dative": word + "n" + a, "accusative": word + "n" + i,
        }[kind]
    a, i = _harmony(word)
    vowel = word[-1] in VOWELS
    d = "t" if word[-1] in _HARD else "d"
    plural = "lar" if a == "a" else "ler"
    return word + {
        "locative_ki": d + a + "ki", "ablative": d + a + "n", "locative": d + a,
        "genitive": ("n" if vowel else "") + i + "n", "instrumental": ("y" if vowel else "") + "l" + a,
        "lik": "l" + i + "k", "copula": d + i + "r", "plural": plural,
        "possessive": ("s" if vowel else "") + i, "dative": ("y" if vowel else "") + a,
        "accusative": ("y" if vowel else "") + i,
    }[kind]

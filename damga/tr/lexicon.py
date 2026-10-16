"""Turkish word lists shared by the grammars and the streaming wrapper.

Pure data, no pynini import: the streaming normalizer and the native runtime load it without the grammar toolchain.
"""
from __future__ import annotations

DIGITS: list[tuple[str, str]] = [("bir", "1"), ("iki", "2"), ("üç", "3"), ("dört", "4"), ("beş", "5"),
                                 ("altı", "6"), ("yedi", "7"), ("sekiz", "8"), ("dokuz", "9")]
TIES: list[tuple[str, str]] = [("on", "1"), ("yirmi", "2"), ("otuz", "3"), ("kırk", "4"), ("elli", "5"),
                               ("altmış", "6"), ("yetmiş", "7"), ("seksen", "8"), ("doksan", "9")]
ZERO = "sıfır"
SCALES = ["yüz", "bin", "milyon", "milyar", "trilyon"]
# Scale words that stay words after a decimal (``2,5 milyon``, ``12,3 milyar``).
QUANTITY_WORDS = ["bin", "milyon", "milyar", "trilyon"]

# Everything a bare spoken number can consist of (plus sign and decimal separator).
NUMBER_WORDS: list[str] = [ZERO] + [w for w, _ in DIGITS] + [w for w, _ in TIES] + SCALES + ["artı", "eksi", "virgül"]

MONTHS = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"]
YEAR_WORDS = ["yılında", "yılı", "yılının", "yılından", "yılına", "yıl", "senesinde", "senesi", "senesinden", "senesine", "sene",
              "yılındaki", "yılıyla", "yılları", "yıllarında", "yıllarda", "yıllarından", "yıllarına", "yıllara",
              "yıllarındaki", "yıllarının"]

CURRENCY_WORDS = ["lira", "kuruş", "dolar", "euro", "avro", "sterlin", "sent"]
SEPARATOR_WORDS = ["nokta", "et", "at", "alt", "çizgi", "tire", "www", "dot", "dat"]
UNIT_WORDS = ["kilometre", "metre", "kilo", "kilogram", "gram", "litre", "derece"]

# Streaming commit policy (see docs/streaming.md): the cut point moves left of a CONTINUATION word and never
# lands right before an ATTACH_NEXT word.
_ASCII_FOLD = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")

STREAMING_CONTINUATION: frozenset[str] = frozenset(
    NUMBER_WORDS + MONTHS + CURRENCY_WORDS + SEPARATOR_WORDS
    # ASCII-folded spellings are repaired before the grammar, so they continue a span too
    + [w.translate(_ASCII_FOLD) for w in NUMBER_WORDS + MONTHS if w.translate(_ASCII_FOLD) != w and w != "uç"]
    + ["buçuk", "çeyrek", "yüzde", "binde", "saat", "te", "re", "ti", "ar", "iban", "plaka", "plakam", "plakası",
       "geçe", "kala", "no", "numara", "daire", "kat"]
    + list("abcçdefgğhıijklmnoöprsştuüvyz")
)
STREAMING_ATTACH_NEXT: frozenset[str] = frozenset(
    SEPARATOR_WORDS + CURRENCY_WORDS + UNIT_WORDS
    + ["altçizgi", "artı", "virgül", "buçuk", "çeyrek", "geçe", "kala", "yılında", "yılı", "bin", "yüz", "milyon", "milyar",
       "dahili"]
)

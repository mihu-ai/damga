import pytest

from damga.tr.itn.repair import repair_spelling


@pytest.mark.parametrize("src,expected", [
    ("yuz elli lira", "yüz elli lira"),
    ("uc bin dort yuz", "üç bin dört yüz"),
    ("sifir bes", "sıfır beş"),
    ("altmis yedi", "altmış yedi"),
    ("yirmibeş", "yirmi beş"),
    ("onbeş ekim", "on beş ekim"),
    ("üçyüzkırkbeş", "üç yüz kırk beş"),
    ("yirmibes", "yirmi beş"),
    ("Yuz Elli", "Yüz Elli"),
    ("YUZ ELLI", "YÜZ ELLİ"),
    ("yuz, elli.", "yüz, elli."),
    ("onbeşinci", "on beşinci"),
])
def test_repair_restores_number_words(src, expected):
    assert repair_spelling(src) == expected


@pytest.mark.parametrize("text", [
    "uç noktası", "yüzük", "yüzbaşı", "onbaşı", "binbir gece", "dörtnala", "kırkayak", "birlikte",
    "merhaba dünya", "ali'nin kedisi", "https://mihu.ai", "ali@gmail.com", "0532 123 45 67", "",
])
def test_repair_leaves_ordinary_text_alone(text):
    assert repair_spelling(text) == text


def test_repair_is_idempotent():
    once = repair_spelling("yuz yirmibes lira")
    assert repair_spelling(once) == once


def test_repair_can_be_disabled():
    from damga import InverseNormalizer
    n = InverseNormalizer(use_cache=False, repair_spelling=False)
    assert n.normalize("yuz elli lira") != "150 TL"


@pytest.mark.parametrize("src,expected", [
    ("sifirdan basla", "sıfırdan basla"),
    ("bese kadar", "beşe kadar"),
    ("dortte bir", "dörtte bir"),
    ("altmisa", "altmışa"),
    ("yetmisten", "yetmişten"),
])
def test_repair_suffixed_folded_forms(src, expected):
    assert repair_spelling(src) == expected


@pytest.mark.parametrize("text", ["besi uşak", "beste yaptı", "yuzu güzel", "uce kadar", "altına girdi"])
def test_repair_suffix_does_not_touch_real_words(text):
    assert repair_spelling(text) == text


@pytest.mark.parametrize("src,expected", [
    ("a be ce", "ABC"),
    ("ka pe ka", "KPK"),
    ("takip kodu Be Ce Fe", "takip kodu BCF"),
    ("he he he", "he he he"),
    ("a be", "a be"),
    ("otuz dört ka ka beş yüz", "otuz dört ka ka beş yüz"),
])
def test_repair_joins_spelled_letters(src, expected):
    assert repair_spelling(src) == expected

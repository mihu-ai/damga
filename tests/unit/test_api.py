import pathlib

import pytest

from damga import InverseNormalizer, Normalizer


def test_normalizer_modes():
    assert Normalizer(mode="itn", use_cache=False).normalize("yirmi beş bin") == "25.000"
    assert Normalizer(mode="tn", use_cache=False).normalize("25.000") == "yirmi beş bin"
    with pytest.raises(ValueError):
        Normalizer(mode="xx")

def test_categories_subset():
    pytest.importorskip("pynini")
    n = InverseNormalizer(categories=["cardinal"], use_cache=False, backend="pynini")
    assert n.normalize("yüzde yirmi beş") == "yüzde 25"

def test_old_category_names():
    pytest.importorskip("pynini")
    n = InverseNormalizer(categories=["whitelist"], use_cache=False, backend="pynini")
    assert n.categories == ("lexicon_entry",)
    assert n.normalize("ka de ve") == "KDV"
    en = InverseNormalizer(lang="en", categories=["electronic"], use_cache=False, backend="pynini")
    assert en.categories == ("email_url",)

def test_strict_mode():
    pytest.importorskip("pynini")
    n = InverseNormalizer(strict=True, use_cache=False, backend="pynini")
    assert n.normalize("yirmi beş adet") == "yirmi beş adet"
    assert n.normalize("yüzde yirmi beş") == "%25"
    assert n.normalize("sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi") == "0532 123 45 67"

def test_custom_vocab():
    n = InverseNormalizer(custom_vocab={"e te es tur": "ETS Tur", "mihu": "Mihu"}, use_cache=False)
    assert n.normalize("e te es tur ile mihu") == "ETS Tur ile Mihu"

def test_cache_roundtrip(tmp_path: pathlib.Path):
    pytest.importorskip("pynini")
    a = InverseNormalizer(cache_dir=tmp_path, use_cache=True, backend="pynini")
    assert a.engine.loaded_from_cache is False and a.engine.far_file.exists()
    b = InverseNormalizer(cache_dir=tmp_path, use_cache=True, backend="pynini")
    assert b.engine.loaded_from_cache is True
    assert b.normalize("on beş") == "15"

def test_turkish_unicode_preserved():
    n = InverseNormalizer(use_cache=False)
    assert n.normalize("İSTANBUL'DA ŞİŞLİ") == "İSTANBUL'DA ŞİŞLİ"
    assert n.normalize("İSTANBUL'DA YİRMİ BEŞ KİŞİ") == "İSTANBUL'DA 25 KİŞİ"
    assert n.normalize("ığdır çığ") == "ığdır çığ"
    assert InverseNormalizer(use_cache=False, preserve_case=False).normalize("İSTANBUL'DA ŞİŞLİ") == "istanbul'da şişli"

def test_brackets_and_specials_safe():
    n = InverseNormalizer(use_cache=False)
    for s in ["[test] (x) {y} a\\b", "100% [on]", "a|b"]:
        assert n.normalize(s)

def test_long_transcript():
    n = InverseNormalizer(use_cache=False)
    text = " ".join(["merhaba telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi ve fiyat yüz elli lira"] * 20)
    out = n.normalize(text)
    assert out.count("0532 123 45 67") == 20 and out.count("150 TL") == 20

def test_long_transcript_keeps_case_across_alignment_windows():
    n = InverseNormalizer(use_cache=False)
    text = " ".join(["Ali Bey on dört Haziran'da İstanbul'a yüz elli lira gönderdi."] * 120)
    out = n.normalize(text)
    assert out.split(". ") == ["Ali Bey 14 Haziran'da İstanbul'a 150 TL gönderdi"] * 119 + ["Ali Bey 14 Haziran'da İstanbul'a 150 TL gönderdi."]

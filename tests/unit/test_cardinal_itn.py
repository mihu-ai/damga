import pytest

CASES = [
    ("sıfır", "0"),
    ("bir", "bir"),
    ("dokuz", "9"),
    ("on", "10"),
    ("on beş", "15"),
    ("doksan dokuz", "99"),
    ("yüz", "100"),
    ("yüz bir", "101"),
    ("iki yüz on beş", "215"),
    ("dokuz yüz doksan dokuz", "999"),
    ("bin", "1.000"),
    ("bin bir", "1.001"),
    ("iki bin yirmi altı", "2.026"),
    ("yirmi beş bin", "25.000"),
    ("yirmi beş bin altı yüz", "25.600"),
    ("yüz bin", "100.000"),
    ("dokuz yüz doksan dokuz bin dokuz yüz doksan dokuz", "999.999"),
    ("bir milyon", "1.000.000"),
    ("bir milyon iki yüz elli bin", "1.250.000"),
    ("üç milyar", "3.000.000.000"),
    ("eksi on iki", "-12"),
    ("eksi yüz", "-100"),
]

@pytest.mark.parametrize("spoken,written", CASES)
def test_cardinal(itn, spoken, written):
    assert itn.normalize(spoken) == written

def test_cardinal_in_sentence(itn):
    assert itn.normalize("kilometresi doksan bin olarak kayıtlı") == "kilometresi 90.000 olarak kayıtlı"
    assert itn.normalize("Toplam yirmi beş bin altı yüz adet var.") == "Toplam 25.600 adet var."

def test_words_untouched(itn):
    assert itn.normalize("merhaba dünya") == "merhaba dünya"
    assert itn.normalize("onun evi") == "onun evi"
    assert itn.normalize("birlikte") == "birlikte"

def test_record_diagnostics(itn):
    r = itn.normalize_with_details("on beş")
    assert r.text == "15" and 'cardinal(integer="15")' in r.record and r.changed

def test_batch(itn):
    assert itn.normalize_batch(["iki", "üç"]) == ["2", "3"]

def test_empty(itn):
    assert itn.normalize("") == ""
    assert itn.normalize("   ") == ""


def test_itn_style_options_default_unchanged():
    pytest.importorskip("pynini")
    from damga import InverseNormalizer

    default = InverseNormalizer(use_cache=False)
    assert default.normalize("iki bin yirmi dört seçimleri") == "2.024 seçimleri"
    assert default.normalize("beş milyon kişi") == "5.000.000 kişi"
    styled = InverseNormalizer(use_cache=False, backend="pynini", group_four_digits=False, scale_words=True)
    assert styled.normalize("iki bin yirmi dört seçimleri") == "2024 seçimleri"
    assert styled.normalize("bin beş yüz kişi") == "1500 kişi"
    assert styled.normalize("yirmi beş bin altı yüz") == "25.600"
    assert styled.normalize("beş milyon kişi") == "5 milyon kişi"
    assert styled.normalize("elli altı milyar dolar") == "56 milyar $"
    assert styled.normalize("bir milyona yaklaştı") == "1 milyona yaklaştı"
    assert styled.normalize("iki milyon üç yüz bin") == "2.300.000"
    assert styled.normalize("on iki virgül üç milyon") == "12,3 milyon"

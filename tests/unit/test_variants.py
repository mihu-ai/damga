import pytest

from damga import InverseNormalizer, Normalizer, TextNormalizer
from damga.core.variants import closest, combine, parse_record
from tests.conftest import load_golden


@pytest.fixture(scope="module")
def tnv():
    return TextNormalizer(use_cache=False, variants=True)


def test_one_reading_is_the_default(tn):
    assert tn.variants is False
    assert tn.normalize_variants("Saat 09:30") == ["Saat dokuz otuz"]


@pytest.mark.parametrize("src,dst", load_golden("tn.tsv"))
def test_first_variant_is_the_default_output(tnv, src, dst):
    variants = tnv.normalize_variants(src)
    assert variants[0] == tnv.normalize(src) == dst
    assert len(variants) == len(set(variants))


@pytest.mark.parametrize("src,expected", [
    ("Saat 09:30'da geldi.", ["Saat dokuz otuzda geldi.", "Saat dokuz buçukta geldi."]),
    ("Saat 21:45", ["Saat yirmi bir kırk beş", "Saat dokuz kırk beş", "Saat ona çeyrek var"]),
    ("Saat 09:10", ["Saat dokuz on", "Saat dokuzu on geçe"]),
    ("Saat 13:15", ["Saat on üç on beş", "Saat bir on beş", "Saat biri çeyrek geçe"]),
    ("2,5 kg", ["iki virgül beş kilogram", "iki buçuk kilogram", "iki nokta beş kilogram"]),
    ("0,5 lt", ["sıfır virgül beş litre", "yarım litre", "sıfır nokta beş litre"]),
    ("%2,5'e indi", ["yüzde iki virgül beşe indi", "yüzde iki buçuğa indi", "yüzde iki nokta beşe indi"]),
    # point decimals (news, finance): nokta / virgül / the two numbers juxtaposed; a valid hh.mm also as a time
    ("1.6 milyon", ["bir nokta altı milyon", "bir virgül altı milyon", "bir altı milyon"]),
    ("Kur 6.97 oldu", ["Kur altı doksan yedi oldu", "Kur altı nokta doksan yedi oldu",
                       "Kur altı virgül doksan yedi oldu"]),
    ("Saat 17.30'da", ["Saat on yedi otuzda", "Saat beş otuzda", "Saat on yedi buçukta", "Saat beş buçukta"]),
    ("93,85 seviyesi", ["doksan üç virgül seksen beş seviyesi", "doksan üç nokta seksen beş seviyesi",
                        "doksan üç seksen beş seviyesi"]),
    # a numeric month is also read as a number
    ("30.04.2024'e kadar", ["otuz Nisan iki bin yirmi dörde kadar", "otuz sıfır dört iki bin yirmi dörde kadar",
                            "otuz dört iki bin yirmi dörde kadar"]),
    # N. before a capitalised word: a cardinal at the end of a sentence by default, an ordinal as the variant
    ("Toplamı 3. Güzel.", ["Toplamı üç. Güzel.", "Toplamı üçüncü Güzel."]),
    ("250 TL", ["iki yüz elli Türk lirası", "iki yüz elli lira"]),
    ("2,50 TL", ["iki lira elli kuruş", "iki Türk lirası elli kuruş", "iki buçuk lira"]),
    ("250 TL'ye", ["iki yüz elli Türk lirasına", "iki yüz elli liraya"]),
    ("2,50 TL'ye", ["iki lira elli kuruşa", "iki Türk lirası elli kuruşa", "iki buçuk liraya"]),
    ("0532 123 45 67", [
        "sıfır beş yüz otuz iki yüz yirmi üç kırk beş altmış yedi",
        "beş yüz otuz iki yüz yirmi üç kırk beş altmış yedi",
        "sıfır beş üç iki bir iki üç dört beş altı yedi",
    ]),
    ("Merhaba dünya", ["Merhaba dünya"]),
])
def test_alternative_readings(tnv, src, expected):
    assert tnv.normalize_variants(src) == expected


def test_combinations_default_first_then_one_change_at_a_time(tnv):
    v = tnv.normalize_variants("Saat 09:30, tutar 250 TL.")
    assert v[0] == "Saat dokuz otuz, tutar iki yüz elli Türk lirası."
    assert v[1:3] == ["Saat dokuz buçuk, tutar iki yüz elli Türk lirası.", "Saat dokuz otuz, tutar iki yüz elli lira."]
    assert v[3] == "Saat dokuz buçuk, tutar iki yüz elli lira."
    assert tnv.normalize_variants("Saat 09:30, tutar 250 TL.", n=2) == v[:2]


def test_normalize_matching_picks_what_was_said(tnv):
    assert tnv.normalize_matching("Saat 09:30'da geldi.", "saat dokuz buçukta geldi") == "Saat dokuz buçukta geldi."
    assert tnv.normalize_matching("Borç 2,50 TL", "borç iki buçuk lira") == "Borç iki buçuk lira"
    # recognizers write digits; the transcript is read out before comparing
    assert tnv.normalize_matching("Toplam 3.000 TL tutuyor.", "Toplam 3 bin lira tutuyor") == "Toplam üç bin lira tutuyor."
    # digits from the recognizer: their value decides, not their length
    assert tnv.normalize_matching("Randevunuz saat 16:45.", "Randevunu saat 16-45") == "Randevunuz saat on altı kırk beş."
    assert tnv.normalize_matching("Randevunuz saat 16:45.", "randevunuz saat 4-45") == "Randevunuz saat dört kırk beş."
    assert tnv.normalize_matching("Toplantı 19:30'da başlıyor.", "Toplantı 730'da başlıyor.") == "Toplantı yedi otuzda başlıyor."
    # a leading 0 written by the recognizer is the spoken "sıfır"
    assert tnv.normalize_matching("Numaram 0532 944 75 90.", "Numaram 532-944-75-90") == \
        "Numaram beş yüz otuz iki dokuz yüz kırk dört yetmiş beş doksan."
    assert tnv.normalize_matching("Numaram 0532 944 75 90.", "Numaram 0532 944 75 90") == \
        "Numaram sıfır beş yüz otuz iki dokuz yüz kırk dört yetmiş beş doksan."
    # nothing distinguishes the readings → the default
    assert tnv.normalize_matching("Saat 09:30", "tamam") == "Saat dokuz otuz"


def test_backends_agree():
    pytest.importorskip("pynini")
    a = TextNormalizer(use_cache=False, variants=True, backend="native")
    b = TextNormalizer(use_cache=False, variants=True, backend="pynini")
    for s in ("Saat 21:30'da 2,5 kg ve 250 TL.", "Numaram 0532 123 45 67, saat 10:45"):
        assert a.normalize_variants(s, n=50) == b.normalize_variants(s, n=50)


def test_itn_rejects_variants():
    with pytest.raises(ValueError, match="ITN has no variants"):
        InverseNormalizer(use_cache=False, variants=True)


def test_deterministic_still_works_with_a_warning():
    with pytest.warns(DeprecationWarning, match="use variants="):
        old = TextNormalizer(use_cache=False, deterministic=False)
    assert old.variants is True
    assert old.normalize_variants("2,5")[1] == "iki buçuk"
    with pytest.warns(DeprecationWarning):
        assert TextNormalizer(lang="en", deterministic=True).variants is False
    with pytest.warns(DeprecationWarning), pytest.raises(ValueError, match="ITN has no variants"):
        InverseNormalizer(use_cache=False, deterministic=False)


def test_normalizer_facade():
    assert Normalizer(mode="tn", variants=True, use_cache=False).normalize_variants("2,5")[1] == "iki buçuk"
    assert Normalizer(mode="itn", use_cache=False).normalize_variants("yirmi beş") == ["25"]


def test_parse_record_and_combine():
    toks = parse_record('word="a \\"b\\"" time(hours="09" minutes="30" suffix="da") word="."')
    assert [t.cls for t in toks] == ["word", "time", "word"]
    assert toks[0].fields == {"word": 'a "b"'} and toks[1].fields["suffix"] == "da"
    assert parse_record("garbage") is None
    assert combine([["a"], ["b", "B"], ["c", "C"]], 10) == ["a b c", "a B c", "a b C", "a B C"]
    assert closest(["x y", "x z"], "X, z!") == "x z"
    assert closest(["a b", "a"], "a b") == "a b" and closest(["a", "a b"], "a") == "a"


def test_variants_never_leak_marks():
    tnv = TextNormalizer(variants=True)
    for text in ("diyorum G7. Getir", "Model A4. Sonra", "Bu 3'ün 3. kuvveti değil mi?", "Mesai 09.00 - 17.00 arası",
                 "Burası da -3. kattı.", "3'ün 1. kuvveti, 0. kuvveti"):
        for v in tnv.normalize_variants(text, n=20):
            assert "º" not in v and "−" not in v, (text, v)
        assert "º" not in tnv.normalize(text) and "−" not in tnv.normalize(text)


def test_rank_matching_distance_and_threshold(tnv):
    ranked = tnv.rank_matching("Saat 09:30'da geldi.", "saat dokuz buçukta geldi")
    assert ranked[0] == ("Saat dokuz buçukta geldi.", 0.0)
    assert ranked[1][0] == "Saat dokuz otuzda geldi." and ranked[1][1] > 0
    # a transcript of something else: the closest reading is still far, max_distance falls back to the default
    text, other = "Toplam 3.000 TL tutuyor.", "bambaşka bir cümle bu"
    assert tnv.rank_matching(text, other)[0][1] > 1
    assert tnv.normalize_matching(text, other) == "Toplam üç bin lira tutuyor."
    assert tnv.normalize_matching(text, other, max_distance=0.5) == "Toplam üç bin Türk lirası tutuyor."
    assert tnv.normalize_matching(text, "toplam üç bin lira tutuyor", max_distance=0.5) == "Toplam üç bin lira tutuyor."


def test_normalize_in_context_uses_the_scorer(tnv):
    text = "Saat 09:30'da geldi."
    seen: list[list[str]] = []

    def longest(variants):
        seen.append(list(variants))
        return [len(v) for v in variants]

    assert tnv.normalize_in_context(text, longest) == "Saat dokuz buçukta geldi."
    assert seen == [tnv.normalize_variants(text)]
    # ties and small wins keep the default
    assert tnv.normalize_in_context(text, lambda vs: [0.0] * len(vs)) == "Saat dokuz otuzda geldi."
    assert tnv.normalize_in_context(text, lambda vs: [0.0, 0.5], margin=1.0) == "Saat dokuz otuzda geldi."
    # one reading: the scorer is not called
    assert tnv.normalize_in_context("Merhaba dünya", lambda vs: 1 / 0) == "Merhaba dünya"


def test_pick_scored():
    from damga.core.variants import pick_scored

    assert pick_scored(["a", "b", "c"], [1.0, 3.0, 3.0]) == "b"
    assert pick_scored(["a", "b"], [1.0, 1.5], margin=1.0) == "a"
    with pytest.raises(ValueError):
        pick_scored(["a", "b"], [1.0])


def test_half_past_twelve_is_also_yarim():
    tn = TextNormalizer(variants=True, use_cache=False)
    assert tn.normalize("12:30'da geleceğim") == "on iki otuzda geleceğim"
    assert "yarımda geleceğim" in tn.normalize_variants("12:30'da geleceğim")
    assert tn.normalize_matching("12:30'da geleceğim", "yarımda geleceğim") == "yarımda geleceğim"
    assert all("yarım" not in v for v in tn.normalize_variants("09:30'da"))

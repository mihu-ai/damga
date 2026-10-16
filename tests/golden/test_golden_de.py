import pytest

from tests.conftest import load_golden

TN = load_golden("de/tn.tsv")
ITN = load_golden("de/itn.tsv", with_xfail=True)


@pytest.fixture(scope="module")
def de_tn():
    from damga import TextNormalizer
    return TextNormalizer(lang="de", use_cache=False)


@pytest.fixture(scope="module")
def de_itn():
    from damga import InverseNormalizer
    return InverseNormalizer(lang="de", use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_golden_de_tn(de_tn, written, spoken):
    assert de_tn.normalize(written) == spoken


@pytest.mark.parametrize("spoken,written", ITN)
def test_golden_de_itn(de_itn, spoken, written):
    assert de_itn.normalize(spoken) == written


@pytest.fixture(scope="module")
def de_tn_variants():
    from damga import TextNormalizer
    return TextNormalizer(lang="de", variants=True, use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_de_first_variant_is_the_default_reading(de_tn_variants, written, spoken):
    assert de_tn_variants.normalize_variants(written, n=8)[0] == spoken


@pytest.mark.parametrize("written,alternative", [
    ("seit 2012", "seit zwanzig zwölf"),
    ("seit 2012", "seit zweitausendundzwölf"),
    ("seit 2012", "seit zwotausendzwölf"),
    ("bis 2030", "bis zweitausenddreißig"),
    ("100 Menschen", "einhundert Menschen"),
    ("1.000 Euro", "eintausend Euro"),
    ("2,5 Prozent", "zweieinhalb Prozent"),
    ("1,5 Prozent", "anderthalb Prozent"),
    ("1,5 Prozent", "eineinhalb Prozent"),
    ("0,15", "null Komma fünfzehn"),
    ("in den 1990er Jahren", "in den neunziger Jahren"),
])
def test_de_alternative_readings(de_tn_variants, written, alternative):
    assert alternative in de_tn_variants.normalize_variants(written, n=20)


@pytest.mark.parametrize("written,heard,expected", [
    ("Im Jahr 2012 haben wir 100 Mio. Euro gezahlt.", "im jahr zwanzig zwölf haben wir einhundert millionen euro gezahlt",
     "Im Jahr zwanzig zwölf haben wir einhundert Millionen Euro gezahlt."),
    ("seit 2012", "seit zweitausendzwölf", "seit zweitausendzwölf"),
    ("um 2,5 Prozent", "um zweieinhalb prozent", "um zweieinhalb Prozent"),
    ("bis 2030", "bis zweitausenddreißig", "bis zweitausenddreißig"),
])
def test_de_matching_picks_the_heard_reading(de_tn_variants, written, heard, expected):
    assert de_tn_variants.normalize_matching(written, heard) == expected


def test_de_default_has_one_reading(de_tn):
    assert de_tn.normalize_variants("seit 2012 und 100 Menschen", n=10) == ["seit zweitausendzwölf und hundert Menschen"]


def test_de_readings_differ_in_words(de_tn_variants):
    readings = de_tn_variants.normalize_variants("Es kostet 100 Mio. Euro.", n=20)
    keys = [" ".join(r.lower().replace(".", " ").split()) for r in readings]
    assert len(keys) == len(set(keys))

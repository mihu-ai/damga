import pytest

from tests.conftest import load_golden

TN = load_golden("es/tn.tsv")
ITN = load_golden("es/itn.tsv", with_xfail=True)


@pytest.fixture(scope="module")
def es_tn():
    from damga import TextNormalizer
    return TextNormalizer(lang="es", use_cache=False)


@pytest.fixture(scope="module")
def es_itn():
    from damga import InverseNormalizer
    return InverseNormalizer(lang="es", use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_golden_es_tn(es_tn, written, spoken):
    assert es_tn.normalize(written) == spoken


@pytest.mark.parametrize("spoken,written", ITN)
def test_golden_es_itn(es_itn, spoken, written):
    assert es_itn.normalize(spoken) == written


# Variants: the readings speakers also use, the default always first.

@pytest.fixture(scope="module")
def es_variants():
    from damga import TextNormalizer
    return TextNormalizer(lang="es", variants=True, use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_first_variant_is_the_default(es_variants, written, spoken):
    assert es_variants.normalize_variants(written, n=5)[0] == spoken


@pytest.mark.parametrize("written,reading", [
    ("2,5 millones de empleos", "dos millones y medio de empleos"),
    ("1,5 millones", "un millón y medio"),
    ("un 3,5 % más", "un tres y medio por ciento más"),
    ("21 países", "veintiuno países"),
    ("a las 9:30", "a las nueve treinta"),
    ("a las 11.45 horas", "a las once cuarenta y cinco horas"),
    ("cuesta 1,50 €", "cuesta un euro cincuenta"),
    ("el 80.º aniversario", "el octogésimo aniversario"),
    ("500.000 personas", "medio millón de personas"),
    ("En 2012 hubo elecciones", "En el dos mil doce hubo elecciones"),
    ("en marzo de 2014", "en marzo del dos mil catorce"),
    ("hasta 2020", "hasta el año dos mil veinte"),
    ("el 1 de enero", "el primero de enero"),
    ("el 1,3 %", "el uno punto tres por ciento"),
])
def test_other_readings(es_variants, written, reading):
    assert reading in es_variants.normalize_variants(written, n=20)


@pytest.mark.parametrize("written", ["unos 500.000.", "1,5 millones de euros", "Antes de 2010 no."])
def test_no_ungrammatical_readings(es_variants, written):
    readings = es_variants.normalize_variants(written, n=20)
    assert not any(bad in r for r in readings for bad in ("millón de.", "uno y medio millones", "de el "))


def test_matching_picks_what_was_said(es_variants):
    written = "En 2012 se perdieron 2,5 millones de empleos."
    heard = "en el dos mil doce se perdieron dos millones y medio de empleos"
    assert es_variants.normalize_matching(written, heard) == "En el dos mil doce se perdieron dos millones y medio de empleos."
    # a transcript of something else is not trusted with max_distance: the default stays
    assert es_variants.normalize_matching(written, "algo distinto", max_distance=0.5) == es_variants.normalize(written)


def test_default_has_one_reading(es_tn):
    assert es_tn.normalize_variants("En 2012 se perdieron 2,5 millones de empleos.", n=10) == [
        "En dos mil doce se perdieron dos coma cinco millones de empleos."]

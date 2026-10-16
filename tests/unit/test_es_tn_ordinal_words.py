"""Spanish TN ``formal_ordinals=True``: written ordinals from 11 to 100 read as ordinal words."""
from __future__ import annotations

import pytest

import damga
from damga.es.tn.normalizer import TextNormalizer, ordinal_words


@pytest.fixture(scope="module")
def formal():
    return TextNormalizer(formal_ordinals=True)


@pytest.fixture(scope="module")
def default():
    return TextNormalizer()


CASES = [
    ("el 80.º aniversario", "el octogésimo aniversario"),
    ("la 11.ª edición", "la undécima edición"),
    ("el 11.º puesto", "el undécimo puesto"),
    ("el 11.ᵉʳ puesto", "el undécimo puesto"),
    ("el 12.º congreso", "el duodécimo congreso"),
    ("la 12.ª vez", "la duodécima vez"),
    ("el 13.º piso", "el decimotercero piso"),
    ("el 13.ᵉʳ piso", "el decimotercer piso"),
    ("la 13.ª jornada", "la decimotercera jornada"),
    ("la 17.ª etapa", "la decimoséptima etapa"),
    ("el 20.º aniversario", "el vigésimo aniversario"),
    ("la 21.ª edición", "la vigésima primera edición"),
    ("el 21.º", "el vigésimo primero"),
    ("el 21.ᵉʳ aniversario", "el vigésimo primer aniversario"),
    ("el 23.ᵉʳ puesto", "el vigésimo tercer puesto"),
    ("la 33.ª vuelta", "la trigésima tercera vuelta"),
    ("el 45.º", "el cuadragésimo quinto"),
    ("el 99.º", "el nonagésimo noveno"),
    ("el 100.º aniversario", "el centésimo aniversario"),
    ("la 100.ª", "la centésima"),
    ("el 50ᵒ", "el quincuagésimo"),
    ("la 18ª", "la decimoctava"),
    ("el 11er lugar", "el undécimo lugar"),
    # in sentences with punctuation
    ("Celebramos el 80.º aniversario.", "Celebramos el octogésimo aniversario."),
    ("El 12.º, el 21.º y el 23.ᵉʳ.", "El duodécimo, el vigésimo primero y el vigésimo tercer."),
    ("Quedó (15.ª) en la general.", "Quedó (decimoquinta) en la general."),
    ("¿Es la 30.ª edición?", "¿Es la trigésima edición?"),
    # ten and below: unchanged
    ("el 1.ᵉʳ puesto", "el primer puesto"),
    ("el 3.ᵉʳ piso", "el tercer piso"),
    ("la 5.ª edición", "la quinta edición"),
    ("el 10.º", "el décimo"),
    # above 100: the default cardinal
    ("el 101.º", "el ciento uno"),
    ("el 1.011.º", "el mil once"),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_formal_ordinals(formal, text, expected):
    assert formal.normalize(text) == expected


@pytest.mark.parametrize("text", ["21 personas", "a las 11.45", "20 °C", "el 5.º", "el 101.º", "13 de mayo"])
def test_same_without_ordinal_11_to_100(formal, default, text):
    assert formal.normalize(text) == default.normalize(text)


def test_default_reads_cardinal(default):
    assert default.normalize("el 80.º aniversario") == "el ochenta aniversario"
    assert default.normalize("la 21.ª edición") == "la veintiuna edición"


def test_native_backend():
    n = TextNormalizer(formal_ordinals=True, backend="native")
    assert n.engine.backend == "native"
    assert n.normalize("la 21.ª edición") == "la vigésima primera edición"


def test_api_passthrough():
    n = damga.Normalizer(mode="tn", lang="es", formal_ordinals=True)
    assert n.normalize("el 80.º aniversario") == "el octogésimo aniversario"


def test_ordinal_words():
    assert [ordinal_words(n) for n in (11, 19, 20, 22, 70, 100)] == [
        "undécimo", "decimonoveno", "vigésimo", "vigésimo segundo", "septuagésimo", "centésimo"]
    assert ordinal_words(31, "ª") == "trigésima primera"
    assert ordinal_words(101) is None

import pathlib
import threading

import pytest

from damga import InverseNormalizer, TextNormalizer
from damga.core import engine as engine_mod

GOLDEN = pathlib.Path(__file__).resolve().parents[1] / "golden"


def _inputs(name):
    out = []
    for line in (GOLDEN / name).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "\t" in line:
            out.append(line.split("\t")[0])
    return out


both = pytest.mark.skipif(not (engine_mod.native_available() and engine_mod.pynini_available()), reason="needs both backends")
native = pytest.mark.skipif(not engine_mod.native_available(), reason="native runtime not built")


@native
def test_native_backend_is_selected_by_default():
    n = InverseNormalizer()
    assert n.engine.backend in ("native", "pynini")
    assert InverseNormalizer(backend="native").engine.backend == "native"


@both
@pytest.mark.parametrize("name", ["itn.tsv", "itn_asr.tsv"])
def test_itn_backends_agree(name):
    a = InverseNormalizer(backend="native")
    b = InverseNormalizer(backend="pynini", use_cache=False)
    for text in _inputs(name):
        assert a.normalize(text) == b.normalize(text), text


@both
def test_tn_backends_agree():
    a = TextNormalizer(backend="native")
    b = TextNormalizer(backend="pynini", use_cache=False)
    for text in _inputs("tn.tsv"):
        assert a.normalize(text) == b.normalize(text), text


@native
def test_native_custom_vocab_post_pass():
    n = InverseNormalizer(backend="native", custom_vocab={"mihu": "Mihu", "ets tur": "ETS Tur"})
    assert n.normalize("mihu ile ets tur anlaştı, numara on iki") == "Mihu ile ETS Tur anlaştı, No: 12"


@native
def test_native_rejects_custom_categories():
    with pytest.raises(ValueError):
        InverseNormalizer(backend="native", categories=["cardinal"])


@native
def test_many_threads_share_one_native_normalizer():
    # The native runtime releases the GIL while it composes; Python objects must only be built with it held.
    # Building the result bytes without the GIL corrupted the interpreter heap and crashed under load.
    tn, itn = TextNormalizer(backend="native"), InverseNormalizer(backend="native")
    tn_in = ["Randevunuz 15:30'da, ücret 250 TL.", "Borcunuz 2.500,40 TL, son ödeme 28.10.2026.", "Numaram 0532 123 45 67."]
    itn_in = ["iki bin beş yüz lira kırk kuruş", "sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi", "saat on beş otuzda"]
    expected = [tn.normalize(s) for s in tn_in] + [itn.normalize(s) for s in itn_in]
    wrong: list[str] = []

    def work():
        for _ in range(150):
            got = [tn.normalize(s) for s in tn_in] + [itn.normalize(s) for s in itn_in]
            if got != expected:
                wrong.append(repr(got))

    threads = [threading.Thread(target=work) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not wrong


# Variants for the languages whose readings come from a variants grammar (damga.core.readings).
EN_SENTENCES = ["In 2013 we paid €5 million.", "on 6 December 2012", "It grew 1.5% to 0.7 billion",
                "105 jobs in the 1990s", "about 1300 persons", "no numbers here at all"]


@both
def test_readings_backends_agree():
    a = TextNormalizer(lang="en", variants=True, backend="native")
    b = TextNormalizer(lang="en", variants=True, backend="pynini", use_cache=False)
    for text in EN_SENTENCES:
        assert a.normalize_variants(text, n=8) == b.normalize_variants(text, n=8), text


@native
def test_readings_start_with_the_default_and_are_distinct():
    det = TextNormalizer(lang="en", backend="native")
    tn = TextNormalizer(lang="en", variants=True, backend="native")
    for text in EN_SENTENCES:
        variants = tn.normalize_variants(text, n=8)
        assert variants[0] == det.normalize(text) == tn.normalize(text)
        assert len(variants) == len(set(variants))
        assert det.normalize_variants(text, n=8) == [det.normalize(text)]
    assert tn.normalize_matching("In 2013 we paid €5 million.", "in twenty thirteen we paid five million euro") \
        == "In twenty thirteen we paid five million euro."


@native
def test_nbest_is_thread_safe():
    tn = TextNormalizer(lang="en", variants=True, backend="native")
    expected = {t: tn.normalize_variants(t, n=8) for t in EN_SENTENCES}
    errors = []

    def work():
        try:
            for _ in range(30):
                for t in EN_SENTENCES:
                    if tn.normalize_variants(t, n=8) != expected[t]:
                        errors.append(t)
        except Exception as e:  # pragma: no cover - reported below
            errors.append(repr(e))

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors[:3]

import pytest

from damga.streaming import StreamingNormalizer


@pytest.fixture(scope="module")
def sn():
    return StreamingNormalizer(mode="itn", stable_after=2, use_cache=False)

def test_number_not_committed_early(sn):
    sn.reset()
    r1 = sn.update("yirmi beş", is_final=False)
    assert r1.text == "25" and r1.committed == ""
    r2 = sn.update("yirmi beş bin", is_final=False)
    assert r2.text == "25.000" and r2.committed == ""
    r3 = sn.update("yirmi beş bin altı yüz", is_final=True)
    assert r3.text == "25.600" and r3.is_final and r3.committed == "25.600"

def test_stable_prefix_commits(sn):
    sn.reset()
    sn.update("merhaba ben derya toplam tutar", is_final=False)
    r = sn.update("merhaba ben derya toplam tutar yirmi", is_final=False)
    assert r.committed == "merhaba ben derya"
    assert r.provisional == "toplam tutar 20"
    r = sn.update("merhaba ben derya toplam tutar yirmi beş bin lira", is_final=True)
    assert r.text == "merhaba ben derya toplam tutar 25.000 TL"

def test_final_equals_batch(sn):
    from damga import InverseNormalizer
    batch = InverseNormalizer(use_cache=False)
    s = "faturayı pınar nokta yılmaz et hotmail nokta com adresine gönderin"
    sn.reset(); words = s.split()
    for i in range(1, len(words) + 1):
        r = sn.update(" ".join(words[:i]), is_final=(i == len(words)))
    assert r.text == batch.normalize(s) == "faturayı pinar.yilmaz@hotmail.com adresine gönderin"

def test_revised_hypothesis(sn):
    sn.reset()
    sn.update("saat dokuz", is_final=False)
    r = sn.update("saat dokuz otuz", is_final=False)
    assert r.committed == ""
    r = sn.update("saat dokuz otuzda görüşürüz", is_final=True)
    assert r.text.startswith("saat 09:30")

def test_reset_between_utterances(sn):
    sn.reset()
    sn.update("bir iki üç", is_final=True)
    r2 = sn.update("dört", is_final=True)
    assert r2.text == "4" and "1" not in r2.text

def test_flush(sn):
    sn.reset()
    sn.update("yüzde on iki", is_final=False)
    r = sn.flush()
    assert r.text == "%12" and r.is_final

def test_bounded_buffer():
    sn = StreamingNormalizer(mode="itn", stable_after=1, max_pending_words=5, use_cache=False)
    words = ["kelime"] * 12
    r = sn.update(" ".join(words), is_final=False)
    assert len(r.committed.split()) >= 7
    r = sn.update(" ".join(words + ["on"]), is_final=True)
    assert r.text == " ".join(words) + " 10"

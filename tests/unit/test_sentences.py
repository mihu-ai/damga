from damga.streaming import SentenceSplitter, split_sentences


def test_splitter_waits_for_whitespace_after_period():
    # an LLM streams "25.600" and "15.10.2026" in pieces; neither may be cut at its dots
    pieces = ["Borcunuz 25", ".", "600 TL", ". Son ödeme 15", ".10", ".2026", " tarihinde", ".", " İyi günler!"]
    assert list(split_sentences(pieces)) == ["Borcunuz 25.600 TL.", "Son ödeme 15.10.2026 tarihinde.", "İyi günler!"]


def test_splitter_keeps_ordinals_and_abbreviations():
    text = "Sıranız 3. sırada. Dr. Ahmet Bey sizi arayacak.\nTeşekkürler"
    assert list(split_sentences([text])) == ["Sıranız 3. sırada.", "Dr. Ahmet Bey sizi arayacak.", "Teşekkürler"]


def test_splitter_min_chars_and_flush():
    sp = SentenceSplitter(min_chars=12)
    assert sp.feed("Evet. Tutar 250 TL. ") == ["Evet. Tutar 250 TL."]
    assert sp.feed("Tamam") == [] and sp.flush() == ["Tamam"] and sp.flush() == []

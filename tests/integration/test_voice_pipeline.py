"""Damga inside a real voice pipeline, end to end, without network, models or API keys.

These tests replay what a deployment does:

    caller speaks → streaming STT → Damga ITN → LLM → Damga TN → TTS → caller hears
    call recording → batch STT → Damga ITN per segment → CRM

The recognizer, the LLM and the voice are stand-ins with the same call shapes as the real ones
(Mihu STT's ``accept_pcm16`` → ``(text, is_final)``, a token stream, a ``speak(text)`` call).  The
recognizer scripts replay the hypotheses a streaming recognizer actually emits: a growing partial
transcript per audio chunk, revisions at the tail, then one final per utterance.
"""
import re
import threading

import pytest

from damga import InverseNormalizer, TextNormalizer
from damga.streaming import StreamingNormalizer, split_sentences

# Partial hypotheses Mihu STT emitted for a real recording ("Merhaba, 34 ABC 1023 plakalı aracınız hazır."),
# one per 100 ms chunk with repeats removed.  The recognizer misheard "a be ce" as "de bence"; Damga
# normalizes what it is given and cannot repair that.
PLATE_TURN = [
    "Mer", "Merhaba", "Merhaba otuz", "Merhaba otuz dört", "Merhaba otuz dört de bence",
    "Merhaba otuz dört de bence bin y", "Merhaba otuz dört de bence bin yirmi ü",
    "Merhaba otuz dört de bence bin yirmi üç pla", "Merhaba otuz dört de bence bin yirmi üç plakalı",
    "Merhaba otuz dört de bence bin yirmi üç plakalı aracınız",
    "Merhaba otuz dört de bence bin yirmi üç plakalı aracınız hazır",
]

# A caller dictating a phone number; the tail is revised twice ("otuz" → "otuz iki", "yüz" → "yüz yirmi üç").
PHONE_TURN = [
    "telefon", "telefon numaram", "telefon numaram sıfır beş", "telefon numaram sıfır beş otuz",
    "telefon numaram sıfır beş otuz iki", "telefon numaram sıfır beş otuz iki yüz",
    "telefon numaram sıfır beş otuz iki yüz yirmi üç", "telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş",
    "telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi",
]


class ScriptedRecognizer:
    """Streaming recognizer stand-in with Mihu STT's contract: every chunk returns (hypothesis, is_final).

    After the last hypothesis of each turn it returns the turn once more with is_final=True (the
    recognizer heard enough trailing silence), then ("", False) while nobody speaks.
    """

    def __init__(self, *turns):
        self.events = []
        for turn in turns:
            self.events += [(h, False) for h in turn] + [(turn[-1], True), ("", False)]

    def accept_pcm16(self, pcm: bytes, sample_rate: int = 16000):
        return self.events.pop(0) if self.events else ("", False)


class FakeLLM:
    """Streams a reply token by token, the way an LLM API does, and records what it was asked."""

    def __init__(self, reply_tokens, log):
        self.reply_tokens, self.log, self.prompts = reply_tokens, log, []

    def stream(self, prompt: str):
        self.prompts.append(prompt)
        for token in self.reply_tokens:
            self.log.append(("llm", token))
            yield token


class FakeVoice:
    """TTS stand-in: records every sentence it is asked to speak."""

    def __init__(self, log):
        self.log, self.spoken = log, []

    def speak(self, text: str) -> bytes:
        self.spoken.append(text)
        self.log.append(("tts", text))
        return text.encode()


def run_call(recognizer, llm, voice, tn, chunks):
    """The voice-agent loop: what a LiveKit / Pipecat / SIP handler runs per call."""
    sn = StreamingNormalizer(mode="itn", stable_after=2)      # one per call: it holds the commit state
    captions, finals = [], []
    for chunk in chunks:
        text, is_final = recognizer.accept_pcm16(chunk, 16000)
        if not text.strip():
            continue
        res = sn.update(text, is_final=is_final)
        captions.append(res)                                   # live caption shown while the caller speaks
        if is_final:
            finals.append(res.text)
            for sentence in split_sentences(llm.stream(res.text)):
                voice.speak(tn.normalize(sentence))
    return captions, finals


@pytest.fixture(scope="module")
def itn_shared():
    return InverseNormalizer()


@pytest.fixture(scope="module")
def tn_shared():
    return TextNormalizer()


# --------------------------------------------------------------------------- live captions (streaming ITN)


@pytest.mark.parametrize("turn", [PLATE_TURN, PHONE_TURN], ids=["plate", "phone"])
def test_live_caption_committed_part_never_changes(turn, itn_shared):
    sn = StreamingNormalizer(mode="itn", stable_after=2)
    committed = []
    for hyp in turn:
        res = sn.update(hyp, is_final=False)
        assert res.text == (res.committed + " " + res.provisional).strip()
        committed.append(res.committed)
    # What was shown as committed is only ever extended, never rewritten on screen.
    for before, after in zip(committed, committed[1:]):
        assert after.startswith(before)
    assert committed[-1], "a long utterance commits a prefix before it ends"
    final = sn.update(turn[-1], is_final=True)
    # At the end of the turn the caption equals batch normalization of the final transcript.
    assert final.text == itn_shared.normalize(turn[-1])


def test_live_caption_shows_digits_while_caller_is_still_talking():
    sn = StreamingNormalizer(mode="itn", stable_after=2)
    shown = [sn.update(h, is_final=False).text for h in PHONE_TURN]
    # Digits appear as soon as they are heard, in the groups the caller speaks; once eleven digits
    # make a phone number the caption regroups into the phone format.
    assert shown == [
        "telefon", "telefon numaram", "telefon numaram 0 5", "telefon numaram 0 5 30", "telefon numaram 0 5 32",
        "telefon numaram 0 5 32 100", "telefon numaram 0 5 32 123", "telefon numaram 0 5 32 123 45",
        "telefon numaram 0532 123 45 67",
    ]
    assert sn.update(PHONE_TURN[-1], is_final=True).text == "telefon numaram 0532 123 45 67"


def test_real_recording_hypotheses(itn_shared):
    sn = StreamingNormalizer(mode="itn", stable_after=2)
    for hyp in PLATE_TURN:
        sn.update(hyp, is_final=False)
    final = sn.update(PLATE_TURN[-1], is_final=True).text
    assert final == "Merhaba 34 de bence 1.023 plakalı aracınız hazır"
    assert "ABC" not in final                                  # a recognizer error is not invented away


# --------------------------------------------------------------------------- full voice-agent turn


def test_voice_agent_turn_itn_into_llm_tn_into_voice(tn_shared):
    log = []
    # The LLM writes like people write; "25.600" and "15.10.2026" arrive split across tokens.
    reply = ["Teşekkürler. ", "Kalan borcunuz 25", ".", "600 TL", ". Son ödeme tarihi 15", ".10", ".2026",
             " tarihinde", ". Sizi 0532 123 45 67 numarasından saat 14", ":30'da arayacağız."]
    llm, voice = FakeLLM(reply, log), FakeVoice(log)
    captions, finals = run_call(ScriptedRecognizer(PHONE_TURN), llm, voice, tn_shared, [b"\0" * 3200] * 20)

    # ITN → LLM: the model receives the written form, not words it would have to add up.
    assert finals == ["telefon numaram 0532 123 45 67"]
    assert llm.prompts == ["telefon numaram 0532 123 45 67"]

    # TN → voice: one call per complete sentence, every number in spoken form.
    assert voice.spoken == [
        "Teşekkürler.",
        "Kalan borcunuz yirmi beş bin altı yüz Türk lirası.",
        "Son ödeme tarihi on beş Ekim iki bin yirmi altı tarihinde.",
        "Sizi sıfır beş yüz otuz iki yüz yirmi üç kırk beş altmış yedi numarasından saat on dört otuzda arayacağız.",
    ]
    assert not any(re.search(r"\d", s) for s in voice.spoken)

    # Speech starts before the LLM has finished: the first sentence is spoken while tokens still stream.
    first_tts = log.index(("tts", "Teşekkürler."))
    assert first_tts < len(log) - 1 and ("llm", reply[-1]) in log[first_tts:]


def test_two_turns_in_one_call_start_clean(tn_shared):
    log = []
    llm, voice = FakeLLM(["Tamam."], log), FakeVoice(log)
    _, finals = run_call(ScriptedRecognizer(PHONE_TURN, ["evet", "evet yüzde on beş"]), llm, voice, tn_shared,
                         [b""] * 40)
    assert finals == ["telefon numaram 0532 123 45 67", "evet %15"]   # nothing from turn 1 leaks into turn 2
    assert voice.spoken == ["Tamam.", "Tamam."]


def test_silence_between_turns_is_ignored(tn_shared):
    rec = ScriptedRecognizer(["on beş lira"])
    _, finals = run_call(rec, FakeLLM([], []), FakeVoice([]), tn_shared, [b""] * 10)
    assert finals == ["15 TL"]


# --------------------------------------------------------------------------- batch: call recordings → CRM


def test_recording_is_normalized_per_segment(itn_shared):
    # transcribe_segments() output for a recording: two separate utterances.
    segments = [{"start": 0.0, "end": 1.2, "text": "toplantı saat on"},
                {"start": 1.9, "end": 3.0, "text": "beş dakika sürecek"}]
    rows = [(s["start"], itn_shared.normalize(s["text"])) for s in segments]
    assert rows == [(0.0, "toplantı saat 10"), (1.9, "5 dk sürecek")]
    # Normalizing the joined text instead glues the numbers across the pause into a different time.
    assert itn_shared.normalize(" ".join(s["text"] for s in segments)) == "toplantı saat 15 dk sürecek"


# --------------------------------------------------------------------------- many calls on one server


def test_concurrent_calls_share_normalizers_but_not_streaming_state(itn_shared, tn_shared):
    # One InverseNormalizer / TextNormalizer per process, one StreamingNormalizer per call.
    a, b = StreamingNormalizer(mode="itn"), StreamingNormalizer(mode="itn")
    for ha, hb in zip(PHONE_TURN, PLATE_TURN):                 # two callers, chunks interleaved
        a.update(ha, is_final=False)
        b.update(hb, is_final=False)
    assert a.update(PHONE_TURN[-1], is_final=True).text == "telefon numaram 0532 123 45 67"
    assert b.update(PLATE_TURN[-1], is_final=True).text == "Merhaba 34 de bence 1.023 plakalı aracınız hazır"

    texts = ["Kalan borcunuz 25.600 TL.", "Son ödeme tarihi 15.10.2026.", "Saat 14:30'da arayacağız."] * 20
    expected = [tn_shared.normalize(t) for t in texts]
    results = [None] * len(texts)

    def worker(i):
        results[i] = tn_shared.normalize(texts[i])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(texts))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == expected

"""ElevenLabs with Damga: TN before text-to-speech, ITN after speech-to-text.

    pip install damga elevenlabs
    export ELEVENLABS_API_KEY=...
    python examples/elevenlabs_stt_tts.py tts "Borcunuz 2.500,40 TL, son ödeme 15.10.2026." --out reply.mp3
    python examples/elevenlabs_stt_tts.py stt call.mp3
    python examples/elevenlabs_stt_tts.py roundtrip "Bizi 0850 123 45 67'den 09:30'dan sonra arayın."

TTS: text (an LLM reply, a template, a database row) is cut into sentences, every sentence goes
through TextNormalizer ("2.500,40 TL" → "iki bin beş yüz lira kırk kuruş") and only then to the
voice, so amounts, dates and phone numbers are read the same way every time.  ElevenLabs' own
text normalization is turned off; Damga already sends the spoken form.

STT: Scribe's transcript goes through InverseNormalizer, so numbers, dates, amounts and e-mail
addresses come back in written form whichever way the recognizer spelled them.

roundtrip: text → TN → TTS → mp3 → STT → ITN, to hear and check both directions at once.
"""
import argparse
import sys
import time

from elevenlabs.client import ElevenLabs

from damga import InverseNormalizer, TextNormalizer
from damga.streaming import split_sentences

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["tts", "stt", "roundtrip"])
ap.add_argument("input", help="text for tts / roundtrip, an audio file for stt")
ap.add_argument("--voice", default=None, help="voice id (default: the first voice of the account)")
ap.add_argument("--model", default="eleven_multilingual_v2")
ap.add_argument("--out", default="elevenlabs_out.mp3")
args = ap.parse_args()

client = ElevenLabs()  # reads ELEVENLABS_API_KEY


def tts(text: str, out: str) -> None:
    tn = TextNormalizer()
    voice = args.voice or client.voices.search(page_size=1).voices[0].voice_id
    audio = b""
    t0 = time.time()
    # Sentence by sentence: with a streamed LLM reply, pass the token stream to split_sentences and
    # speech starts after the first sentence instead of after the whole answer.
    for sentence in split_sentences([text]):
        spoken = tn.normalize(sentence)
        print(f"TEXT : {sentence}\nTN   : {spoken}\n")
        chunks = client.text_to_speech.convert(voice_id=voice, text=spoken, model_id=args.model,
                                               output_format="mp3_44100_128", apply_text_normalization="off")
        audio += b"".join(chunks)
    with open(out, "wb") as f:
        f.write(audio)
    print(f"→ {out}  ({len(audio) // 1024} KB, {time.time() - t0:.1f}s, voice {voice})")


def stt(path: str) -> None:
    itn = InverseNormalizer()
    t0 = time.time()
    with open(path, "rb") as f:
        res = client.speech_to_text.convert(file=f, model_id="scribe_v1", language_code="tr")
    print(f"STT  : {res.text}\nITN  : {itn.normalize(res.text)}   ({time.time() - t0:.1f}s)")


try:
    if args.mode == "tts":
        tts(args.input, args.out)
    elif args.mode == "stt":
        stt(args.input)
    else:
        tts(args.input, args.out)
        print()
        stt(args.out)
except Exception as e:  # missing key, unknown voice, quota …
    sys.exit(f"{type(e).__name__}: {e}")

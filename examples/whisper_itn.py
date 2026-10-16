"""Whisper / faster-whisper → Damga ITN.

    python examples/whisper_itn.py audio.wav                 # openai-whisper if installed, else faster-whisper
    python examples/whisper_itn.py audio.wav --engine faster --model small

Prints each segment twice: the recognizer's text and its normalized written form.
"""
import argparse
import sys

from damga import InverseNormalizer

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("--engine", choices=["auto", "whisper", "faster"], default="auto")
ap.add_argument("--model", default="small")
args = ap.parse_args()

itn = InverseNormalizer()
PROMPT = "Telefon numarası, e-posta adresi, tutar ve tarih içeren bir görüşme."


def segments_whisper():
    import whisper
    model = whisper.load_model(args.model)
    res = model.transcribe(args.audio, language="tr", initial_prompt=PROMPT)
    for seg in res["segments"]:
        yield seg["start"], seg["end"], seg["text"].strip()


def segments_faster():
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segs, _info = model.transcribe(args.audio, language="tr", vad_filter=True, initial_prompt=PROMPT)
    for seg in segs:
        yield seg.start, seg.end, seg.text.strip()


engine = args.engine
if engine == "auto":
    try:
        import whisper  # noqa: F401
        engine = "whisper"
    except ImportError:
        engine = "faster"

try:
    segments = segments_whisper() if engine == "whisper" else segments_faster()
    for start, end, text in segments:
        print(f"[{start:7.2f} → {end:7.2f}] ASR : {text}")
        print(f"{'':20} ITN : {itn.normalize(text)}")
except ImportError as e:
    sys.exit(f"{e}\ninstall one of: pip install openai-whisper   |   pip install faster-whisper")

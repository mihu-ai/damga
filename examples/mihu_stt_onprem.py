"""Mihu Turkish STT on-prem (runs on your CPU) → Damga ITN, batch and streaming.

    pip install damga turkish-stt soundfile
    python examples/mihu_stt_onprem.py audio.wav [more.wav ...]
    python examples/mihu_stt_onprem.py audio.wav --model-dir /models/mihu-stt    # another model folder
    python examples/mihu_stt_onprem.py audio.wav --fp32                          # unquantized encoder

The recognizer writes numbers, dates and e-mail addresses as words ("sıfır beş otuz iki …");
Damga turns them into their written form ("0532 …").  For every file: one-shot transcription,
timed segments, then the first file again as a simulated live stream (100 ms chunks) so you can
watch the normalized text grow while the speaker is still talking.

Audio never leaves the machine.  The default model downloads once from Hugging Face and is cached;
--model-dir loads a folder with tokens.txt, encoder(.int8).onnx, decoder.onnx and joiner.int8.onnx.
"""
import argparse

import mihu_stt
import numpy as np
import soundfile as sf

from damga import InverseNormalizer
from damga.streaming import StreamingNormalizer

ap = argparse.ArgumentParser()
ap.add_argument("audio", nargs="+")
ap.add_argument("--model-dir", default=None, help="local model folder (default: the built-in model)")
ap.add_argument("--fp32", action="store_true", help="use the unquantized encoder")
args = ap.parse_args()
model = {"model_dir": args.model_dir, "quantized": not args.fp32}

itn = InverseNormalizer()

# 1) Batch: whole file → text → ITN.  Normalize per segment: a segment is one utterance, and phone
#    numbers or amounts must not be glued across two utterances.
for path in args.audio:
    text = mihu_stt.transcribe(path, **model)
    print(f"{path}\n  STT : {text}\n  ITN : {itn.normalize(text)}")
    for seg in mihu_stt.transcribe_segments(path, **model):
        print(f"  [{seg['start']:6.2f} → {seg['end']:6.2f}] {itn.normalize(seg['text'])}")

# 2) Streaming: the recognizer returns a growing hypothesis per chunk and is_final at the end of a
#    turn.  StreamingNormalizer keeps the stable prefix ("committed") and re-renders only the tail
#    ("provisional"); on is_final the whole turn is normalized once more and the normalizer resets.
audio, sr = sf.read(args.audio[0], dtype="float32")
if audio.ndim > 1:
    audio = audio.mean(axis=1)
stt = mihu_stt.StreamingSTT(**model)
sn = StreamingNormalizer(mode="itn", stable_after=2)

print("\nstreaming:")
step = sr // 10
silence = [np.zeros(step, dtype="float32")] * 30                # 3 s of silence: the recognizer closes the turn
chunks = [audio[i:i + step] for i in range(0, len(audio), step)] + silence
shown = ""
for chunk in chunks:
    text, is_final = stt.accept_float32(chunk, sr)
    if not text.strip():
        if is_final:
            sn.reset()
        continue
    res = sn.update(text, is_final=is_final)
    if is_final:
        print(f"FINAL {res.text}")
        shown = ""
    elif res.text != shown:                                      # print only when the rendering changes
        print(f"      {res.committed} \033[2m{res.provisional}\033[0m")
        shown = res.text

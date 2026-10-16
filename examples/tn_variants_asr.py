"""Pick the TN reading a speaker actually said, with a recognizer: training text that matches the audio.

    pip install damga turkish-stt soundfile
    python examples/tn_variants_asr.py call.wav "Toplam 3.000 TL tutuyor."
    python examples/tn_variants_asr.py --manifest data.tsv --out train.tsv    # audio<TAB>written text per line

A written sentence has one default reading ("3.000 TL" → "üç bin Türk lirası"), but the speaker may have
said "üç bin lira".  TextNormalizer(variants=True) lists the readings, Mihu Turkish STT transcribes the
recording on your CPU, and normalize_matching() keeps the reading closest to the transcript.  Use the output as
TTS or ASR training text, or as the reference for an ASR test set.  Any recognizer works: only the transcript
string is passed to Damga.
"""
import argparse
import sys

import mihu_stt

from damga import TextNormalizer

ap = argparse.ArgumentParser()
ap.add_argument("audio", nargs="?")
ap.add_argument("text", nargs="?", help="the written sentence the recording was made from")
ap.add_argument("--manifest", help="TSV: audio path<TAB>written text")
ap.add_argument("--out", help="write audio<TAB>chosen reading to this TSV")
args = ap.parse_args()

if args.manifest:
    with open(args.manifest, encoding="utf-8") as f:
        pairs = [line.rstrip("\n").split("\t", 1) for line in f if line.strip()]
elif args.audio and args.text:
    pairs = [[args.audio, args.text]]
else:
    sys.exit("give an audio file and its written text, or --manifest")

tn = TextNormalizer(variants=True)
rows, changed = [], 0
for audio, text in pairs:
    heard = mihu_stt.transcribe(audio)
    variants = tn.normalize_variants(text, n=50)
    chosen = tn.normalize_matching(text, heard)
    changed += chosen != variants[0]
    rows.append((audio, chosen))
    print(f"{audio}\n  text    : {text}\n  default : {variants[0]}\n  heard   : {heard}\n"
          f"  chosen  : {chosen}{'' if chosen == variants[0] else '   ← not the default'}\n")

print(f"{len(rows)} recordings, {changed} read differently from the default")
if args.out:
    with open(args.out, "w", encoding="utf-8") as f:
        f.writelines(f"{a}\t{c}\n" for a, c in rows)
    print(f"→ {args.out}")

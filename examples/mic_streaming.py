"""Live microphone → Mihu Turkish STT → Damga streaming ITN.

    pip install damga turkish-stt sounddevice
    python examples/mic_streaming.py                 # default input device
    python examples/mic_streaming.py --device 0      # pick a device (see --list)
    python examples/mic_streaming.py --list

Speak; the current line shows the recognizer's hypothesis and its normalized form and is redrawn
as the hypothesis changes.  When the recognizer detects the end of your turn the final line is
printed and a new turn starts.  Ctrl-C to stop.
"""
import argparse
import queue
import shutil
import sys

import mihu_stt
import numpy as np
import sounddevice as sd

from damga.streaming import StreamingNormalizer

ap = argparse.ArgumentParser()
ap.add_argument("--device", type=int, default=None)
ap.add_argument("--list", action="store_true")
ap.add_argument("--rate", type=int, default=16000)
ap.add_argument("--chunk-ms", type=int, default=100)
args = ap.parse_args()

if args.list:
    print(sd.query_devices())
    sys.exit(0)

print("loading Mihu STT …", flush=True)
stt = mihu_stt.StreamingSTT()                    # on-prem, CPU
sn = StreamingNormalizer(mode="itn", stable_after=2)
frames: "queue.Queue[np.ndarray]" = queue.Queue()


def on_audio(indata, _frames, _time, status):
    if status:
        print(status, file=sys.stderr)
    frames.put(indata[:, 0].copy())


block = args.rate * args.chunk_ms // 1000
turn = 1
print("listening — speak Turkish, Ctrl-C to stop")
print('  try="telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi"')
print('       "yarın saat on dörtte iki bin beş yüz lira ödeyeceğim"\n')
try:
    with sd.InputStream(samplerate=args.rate, channels=1, dtype="float32", blocksize=block,
                        device=args.device, callback=on_audio):
        while True:
            text, is_final = stt.accept_float32(frames.get(), args.rate)
            if not text.strip():
                if is_final:
                    sn.reset()
                continue
            res = sn.update(text, is_final=is_final)   # resets itself after a final
            if is_final:
                sys.stdout.write("\r\033[K")
                print(f"[{turn:02d}] STT : {text}\n     ITN : {res.text}\n")
                turn += 1
            else:
                # One terminal row only: "\r" goes back to the start of the last row, so a line that wraps would
                # leave a copy of itself behind on every update.  Show the end of the hypothesis instead.
                width = shutil.get_terminal_size((80, 20)).columns - 4
                live = res.text if len(res.text) <= width else "…" + res.text[-(width - 1):]
                sys.stdout.write(f"\r\033[K … {live}")
                sys.stdout.flush()
except KeyboardInterrupt:
    print("\nbye")

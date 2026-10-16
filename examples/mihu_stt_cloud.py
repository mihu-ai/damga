"""Mihu Turkish STT cloud API → Damga ITN, file upload and live stream.

    pip install damga websockets              # websockets only for --stream
    export MIHU_STT_BASE_URL=https://<your-endpoint>/v1  MIHU_STT_API_KEY=...
    python examples/mihu_stt_cloud.py audio.wav              # POST /v1/audio/transcriptions
    python examples/mihu_stt_cloud.py audio.wav --stream     # WS /v1/stream, 16 kHz mono PCM16 wav

The API returns spoken-form Turkish ("sıfır beş otuz iki …"); Damga turns it into the written form
on your side.  Upload works with any audio file; --stream sends a 16 kHz mono 16-bit wav in 100 ms
chunks as if it were a microphone (convert with `ffmpeg -i in.mp3 -ar 16000 -ac 1 -sample_fmt s16 out.wav`).
The stream endpoint sends one {"event": "final", "text": ...} per utterance, so each one is
normalized with InverseNormalizer as it arrives.
"""
import argparse
import asyncio
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave

from damga import InverseNormalizer

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("--stream", action="store_true", help="live stream over the WebSocket endpoint")
ap.add_argument("--base-url", default=os.environ.get("MIHU_STT_BASE_URL"))
ap.add_argument("--api-key", default=os.environ.get("MIHU_STT_API_KEY"))
args = ap.parse_args()
if not args.base_url or not args.api_key:
    sys.exit("set MIHU_STT_BASE_URL and MIHU_STT_API_KEY (or pass --base-url / --api-key)")
base = args.base_url.rstrip("/")

itn = InverseNormalizer()


def upload(path: str) -> dict:
    """multipart/form-data POST with the standard library: file, model, language."""
    boundary = uuid.uuid4().hex
    fields = {"model": "mihu-stt", "language": "tr"}
    body = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                    for k, v in fields.items())
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\n'
                 f"Content-Type: {ctype}\r\n\r\n").encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{base}/audio/transcriptions", data=body, method="POST", headers={
        "Authorization": f"Bearer {args.api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")


async def stream(path: str) -> None:
    import websockets

    with wave.open(path, "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
            sys.exit("--stream needs a 16 kHz mono 16-bit wav (see the ffmpeg line in the docstring)")
        pcm = w.readframes(w.getnframes())

    url = base.replace("https://", "wss://").replace("http://", "ws://") + "/stream"
    async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {args.api_key}"}) as ws:
        async def send():
            step = 3200                                       # 100 ms of 16 kHz PCM16
            for i in range(0, len(pcm), step):
                await ws.send(pcm[i:i + step])
                await asyncio.sleep(0.1)                      # real-time pace, like a microphone
            await ws.send(b"\x00" * 32000)                    # 1 s of silence closes the last utterance
            await asyncio.sleep(3)                            # let the last result arrive
            await ws.close()

        sender = asyncio.create_task(send())
        async for message in ws:
            event = json.loads(message)
            if event.get("event") == "final" and event.get("text"):
                print(f"STT : {event['text']}\nITN : {itn.normalize(event['text'])}\n")
        await sender


if args.stream:
    asyncio.run(stream(args.audio))
else:
    t0 = time.time()
    res = upload(args.audio)
    print(f"({time.time() - t0:.1f}s, audio {res.get('duration', '?')}s)")
    print(f"STT : {res['text']}\nITN : {itn.normalize(res['text'])}")

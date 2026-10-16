"""Ollama (or any LLM) → Damga TN → TTS.

    ollama serve && ollama pull llama3.1
    python examples/ollama_tn_tts.py "Toplam borcum ne kadar, son ödeme tarihi ne?"
    python examples/ollama_tn_tts.py --tts "piper --model tr_TR-dfki-medium --output_file -" "Saat kaç?"

The reply is streamed from Ollama, cut into sentences, and every sentence is normalized with
TextNormalizer before it is spoken: "2,50 TL" becomes "iki lira elli kuruş", "15.10.2026" becomes
"on beş ekim iki bin yirmi altı".  Without --tts the spoken form is printed.  Standard library only.
"""
import argparse
import json
import shlex
import subprocess
import sys
import urllib.error
import urllib.request

from damga import TextNormalizer
from damga.streaming import split_sentences

SYSTEM = ("Sen bir Türk bankasının müşteri temsilcisisin. Kısa ve net Türkçe cevap ver. "
          "Tutarları '2.500,40 TL', tarihleri '15.10.2026', saatleri '09:30' biçiminde yaz.")

ap = argparse.ArgumentParser()
ap.add_argument("prompt")
ap.add_argument("--model", default="llama3.1")
ap.add_argument("--host", default="http://localhost:11434")
ap.add_argument("--tts", default=None, help="shell command that reads text on stdin and plays or writes audio")
args = ap.parse_args()

tn = TextNormalizer()


def ollama_chat(messages):
    body = json.dumps({"model": args.model, "messages": messages, "stream": True}).encode()
    req = urllib.request.Request(f"{args.host}/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            chunk = json.loads(line)
            yield chunk.get("message", {}).get("content", "")
            if chunk.get("done"):
                return


def speak(sentence: str) -> None:
    spoken = tn.normalize(sentence)
    print(f"LLM : {sentence}\nTTS : {spoken}\n")
    if args.tts:
        subprocess.run(shlex.split(args.tts), input=spoken.encode("utf-8"), check=False)


try:
    # Normalize only at sentence boundaries: a number such as 25.600 arrives as several tokens.
    for sentence in split_sentences(ollama_chat([{"role": "system", "content": SYSTEM},
                                                 {"role": "user", "content": args.prompt}])):
        speak(sentence)
except urllib.error.URLError as e:
    sys.exit(f"cannot reach Ollama at {args.host}: {e}\nstart it with `ollama serve` and pull a model, e.g. `ollama pull {args.model}`")

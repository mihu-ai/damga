# Integrations: recognizers, language models, TTS

Damga has no opinion about where text comes from.  Two rules cover every
integration:

1. **ITN** (`InverseNormalizer`, `StreamingNormalizer(mode="itn")`) goes right
   after a speech recognizer and before anything that reads the text
   (an LLM, a CRM, a display, a database).
2. **TN** (`TextNormalizer`) goes right before a TTS voice, after whatever
   produced the written text (an LLM, a template, a database row).

```
microphone → ASR → Damga ITN → written text → LLM / CRM / display
LLM / database → written text → Damga TN → spoken text → TTS
```

For streaming recognizers there is one more rule: **send Damga the latest full
hypothesis of the current utterance, never a delta**, and call with
`is_final=True` when the recognizer closes the utterance.

Runnable versions of every snippet below are in `examples/`.  For a live call
and a batch transcription walked through step by step, see
[voice-pipeline.md](voice-pipeline.md) ([Türkçe](voice-pipeline.tr.md)).

## Mihu Turkish STT (`turkish-stt`), on-prem and cloud

The recognizer writes entities as words (`sıfır beş otuz iki yüz yirmi üç …`);
put Damga's ITN right after it.  It runs in two places:

**On-prem** (`pip install turkish-stt`): the model runs on your own CPU, audio
never leaves the machine.  Batch:

```python
import mihu_stt
from damga import InverseNormalizer

itn = InverseNormalizer()
text = mihu_stt.transcribe("audio.wav")                         # spoken form
print(itn.normalize(text))                                       # written form
for seg in mihu_stt.transcribe_segments("meeting.wav"):          # one utterance each
    print(seg["start"], seg["end"], itn.normalize(seg["text"]))
```

Streaming: the recognizer returns a growing hypothesis per chunk and
`is_final` at the end of a turn; feed both to `StreamingNormalizer`:

```python
import mihu_stt
from damga.streaming import StreamingNormalizer

stt = mihu_stt.StreamingSTT()          # model="v1" (previous model), model_dir=..., num_threads=...
sn = StreamingNormalizer(mode="itn", stable_after=2)
for pcm16 in audio_frames():           # 16 kHz int16 bytes, as they arrive
    text, is_final = stt.accept_pcm16(pcm16, 16000)
    if text.strip():
        res = sn.update(text, is_final=is_final)
        show(res.committed, res.provisional)   # committed never changes; provisional may
        if is_final:
            handle(res.text)                   # == InverseNormalizer().normalize(text); sn resets itself
```

`model_dir=` loads another model folder (`tokens.txt`, `encoder(.int8).onnx`,
`decoder.onnx`, `joiner.int8.onnx`) instead of the built-in one.

**Cloud**: the same recognizer behind an HTTP API, OpenAI-compatible for files
(`POST {base}/audio/transcriptions`, multipart `file`, Bearer key) and a
WebSocket for live audio (`{base}/stream`: send 16 kHz mono PCM16, receive one
`{"event": "final", "text": …}` per utterance).  The response is spoken form
as well, so the same rule applies:

```python
import requests
from damga import InverseNormalizer

r = requests.post(f"{BASE_URL}/audio/transcriptions", headers={"Authorization": f"Bearer {API_KEY}"},
                  files={"file": open("audio.wav", "rb")}, data={"language": "tr"})
print(InverseNormalizer().normalize(r.json()["text"]))
```

On the stream, normalize every `final` event with `InverseNormalizer` as it
arrives.

Examples: `examples/mihu_stt_onprem.py` (batch + simulated stream),
`examples/mic_streaming.py` (live microphone), `examples/mihu_stt_cloud.py`
(upload and `--stream`, standard library + `websockets`).

Hotwords: the recognizer accepts contextual biasing lists; feeding it the same
brand/domain lists Damga uses (`damga/tr/itn/data/*.tsv`) improves the
recognizer and the normalizer together.

## Whisper and faster-whisper

Whisper is trained on written text, so it often emits digits itself
(`saat 13.30`, `99 lira`).  It is inconsistent, though: the same clip may give
`kırk bir`, `41` or `40 bir`, and long digit strings come out grouped at
random.  Damga's grammars accept all three forms, so running ITN over Whisper
output makes it uniform, and the TN direction gives you a spoken form for
prompts and alignment.

```python
import whisper
from damga import InverseNormalizer

itn = InverseNormalizer()
model = whisper.load_model("small")
res = model.transcribe("audio.wav", language="tr")
print(itn.normalize(res["text"]))
for seg in res["segments"]:                     # per-segment is better: one utterance each
    print(seg["start"], seg["end"], itn.normalize(seg["text"]))
```

```python
from faster_whisper import WhisperModel
from damga import InverseNormalizer

itn = InverseNormalizer()
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.wav", language="tr", vad_filter=True)
for seg in segments:
    print(f"[{seg.start:6.2f} → {seg.end:6.2f}] {itn.normalize(seg.text)}")
```

Tips:

* Normalize **per segment**, not the concatenated text: a segment is a
  natural utterance boundary and the phone/e-mail grammars should not join
  numbers across segments.
* `initial_prompt="Telefon numarası, e-posta adresi, tutar ve tarih içeren bir görüşme."`
  nudges Whisper towards spoken-form output for entities, which Damga then
  formats consistently.
* For word-level timestamps (`word_timestamps=True`), normalize the segment
  text and keep the timestamps of the first and last word of each segment;
  Damga changes the token count, so per-word alignment is not preserved.
* Whisper's "streaming" wrappers (whisper-streaming, WhisperLive) emit
  partial hypotheses that are revised; feed those to
  `StreamingNormalizer.update(hypothesis, is_final=...)` exactly like any other
  streaming recognizer (next section).

Example: `examples/whisper_itn.py` (works with either library).

## Generic streaming recognizers (Vosk, sherpa-onnx, cloud ASR partials)

Every streaming recognizer gives you a growing partial hypothesis and a final
result per utterance.  Map them onto `StreamingNormalizer`:

```python
from damga.streaming import StreamingNormalizer

sn = StreamingNormalizer(mode="itn", stable_after=2)

# Vosk
import json
from vosk import KaldiRecognizer, Model
rec = KaldiRecognizer(Model("vosk-model-small-tr"), 16000)
for chunk in audio_frames():
    if rec.AcceptWaveform(chunk):                              # utterance closed
        final = json.loads(rec.Result())["text"]
        print("FINAL", sn.update(final, is_final=True).text)
    else:
        partial = json.loads(rec.PartialResult())["partial"]
        print("     ", sn.update(partial, is_final=False).text)

# sherpa-onnx online recognizer
stream = recognizer.create_stream()
for chunk in audio_frames():
    stream.accept_waveform(16000, chunk)
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)
    text = recognizer.get_result(stream)
    if recognizer.is_endpoint(stream):
        print("FINAL", sn.update(text, is_final=True).text)
        recognizer.reset(stream)
    elif text:
        print("     ", sn.update(text, is_final=False).text)
```

`res.committed` is the part that will not change any more (safe to send to an
LLM as it arrives), `res.provisional` is the tail that may still move.  Cloud
recognizers that mark results `is_final` (Google, Azure, Deepgram, …) follow
the same shape: interim result → `is_final=False`, final result → `is_final=True`.

Example: `examples/streaming_asr.py`.

## ElevenLabs: speech-to-text and text-to-speech

ElevenLabs covers both directions, so it shows both rules at once.

**STT (Scribe) → ITN:**

```python
from elevenlabs.client import ElevenLabs
from damga import InverseNormalizer

client = ElevenLabs()                                            # ELEVENLABS_API_KEY
with open("call.mp3", "rb") as f:
    res = client.speech_to_text.convert(file=f, model_id="scribe_v1", language_code="tr")
print(InverseNormalizer().normalize(res.text))
```

**TN → TTS:** cut the text into sentences, normalize each one, and send the
spoken form.  Turn ElevenLabs' own text normalization off so numbers are not
processed twice:

```python
from damga import TextNormalizer
from damga.streaming import split_sentences

tn = TextNormalizer()
for sentence in split_sentences(llm_tokens):                     # or [whole_text]
    audio = client.text_to_speech.convert(voice_id=VOICE_ID, text=tn.normalize(sentence),
                                          model_id="eleven_multilingual_v2", apply_text_normalization="off")
    play(b"".join(audio))
```

`Borcunuz 2.500,40 TL, son ödeme 15.10.2026.` reaches the voice as
`Borcunuz iki bin beş yüz lira kırk kuruş, son ödeme on beş ekim iki bin yirmi altı.`

Example: `examples/elevenlabs_stt_tts.py` (`tts`, `stt` and a `roundtrip`
that synthesizes a sentence and transcribes it back).  Every other cloud
recognizer or voice follows the same two patterns.

## Ollama and other LLMs

Damga contains no language model and does not call one.  LLMs appear in two
places around it:

**1. ASR → Damga ITN → LLM.**  Give the model the written form.  A model asked
to extract a callback number from `sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi`
has to do arithmetic; given `0532 123 45 67` it just copies.  The same goes
for amounts, dates and e-mail addresses in tool calls and function arguments.

**2. LLM → Damga TN → TTS.**  Models write like people write: `2,50 TL`,
`15.10.2026`, `%12,5`, `0532 123 45 67`.  TTS voices read written numbers
unreliably, in the wrong language or with the wrong grouping; TN turns the
reply into exactly what should be said.

```python
import json, urllib.request
from damga import TextNormalizer
from damga.streaming import split_sentences

tn = TextNormalizer()

def ollama_chat(messages, model="llama3.1", host="http://localhost:11434"):
    body = json.dumps({"model": model, "messages": messages, "stream": True}).encode()
    req = urllib.request.Request(f"{host}/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            chunk = json.loads(line)
            yield chunk["message"]["content"]
            if chunk.get("done"):
                return

# Normalize at sentence boundaries only: "25.600" may arrive as "25", ".", "600".
for sentence in split_sentences(ollama_chat([{"role": "user", "content": "Toplam borcum ne kadar?"}])):
    speak(tn.normalize(sentence))                   # your TTS call
```

`split_sentences` cuts only where the punctuation is followed by whitespace,
so numbers and dates arriving token by token stay whole; ordinals (`3. sırada`)
and common abbreviations (`Dr.`, `vb.`) are not sentence ends.

Rules of thumb:

* **Normalize whole sentences**, never raw token chunks.  A number, a date or
  a currency amount is routinely split across several LLM tokens.
* **Do not let the LLM "fix" entities Damga left as words.**  Damga leaves a
  10-digit phone number as words on purpose: the recognizer dropped a digit.
  Asking a model to guess the missing digit produces a confident wrong number.
  Ask the user to repeat instead.
* The same `TextNormalizer` works for any other generator: OpenAI-compatible
  APIs, vLLM, llama.cpp, templated replies, database rows.

Example: `examples/ollama_tn_tts.py` (stdlib only, prints the spoken form or
pipes it to a TTS command of your choice).

## TTS engines (Piper, Coqui, cloud voices)

Any TTS benefits from receiving spoken forms: `TextNormalizer().normalize(text)`
right before synthesis.  For voices that already read some numbers correctly,
restrict TN to the classes that need it:

```python
from damga import TextNormalizer
tn = TextNormalizer(categories=["money", "date", "time", "telephone", "percent"], backend="pynini")
```

(Custom category selections run on the pynini backend, so this needs
`pip install "damga[build]"`; the default full configuration runs on the native
runtime with no extra dependency.)

For a complete TN → voice loop see the ElevenLabs section above; any other
engine (Piper, Coqui, Cartesia, a CLI) takes the same `tn.normalize(sentence)`
per sentence.

## Voice-agent frameworks (Pipecat, LiveKit Agents, custom loops)

Put the normalizer in the transcription path, keyed by the utterance:

```python
from damga.streaming import StreamingNormalizer

class ITNStage:
    def __init__(self):
        self.sn = StreamingNormalizer(mode="itn")

    def on_interim(self, text: str) -> str:
        return self.sn.update(text, is_final=False).text

    def on_final(self, text: str) -> str:
        return self.sn.update(text, is_final=True).text     # resets for the next turn
```

On the reply side, normalize each sentence the LLM emits with `TextNormalizer`
before it reaches the TTS stage, as in the Ollama example.  Both normalizers
are thread-safe for concurrent `normalize()` calls (the native runtime releases
the GIL); keep one `StreamingNormalizer` per live utterance stream, since it
holds the commit state.

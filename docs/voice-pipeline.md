# How Damga works in a voice pipeline

*Türkçe: [voice-pipeline.tr.md](voice-pipeline.tr.md)*

Damga is the normalization layer at both ends of a voice pipeline: it turns a
recognizer's spoken-form output into written text (ITN), and text written by an
LLM into the form a voice should read (TN).  Damga contains no recognizer, LLM
or voice, so it works the same whichever ones you use.

```
caller speaks → STT → Damga ITN → written text → LLM / CRM / display
LLM / database → written text → Damga TN → spoken text → TTS → caller hears
```

Two rules cover every integration:

1. **ITN goes right after the recognizer.**  Everything that reads the text
   (an LLM, a CRM, a screen, a database) gets the digits ready-made:
   `0532 123 45 67` instead of `sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi`.
2. **TN goes right before the voice.**  The LLM writes `2.500,40 TL`, the voice
   reads "iki bin beş yüz lira kırk kuruş"; amounts, dates and phone numbers are
   read the same way every time.

For streaming recognizers there is one more rule: send Damga **the latest full
hypothesis of the current utterance**, never only the new piece, and call it
with `is_final=True` when the recognizer closes the utterance.

## Live call / voice agent

The most common use: captions build up on screen while the caller speaks, the
LLM gets written text when they finish, and the reply is spoken sentence by
sentence.  One turn of a call:

1. The microphone, WebRTC or the phone line sends an audio chunk every 20–100 ms.
2. The recognizer returns a growing hypothesis per chunk: `Mer` → `Merhaba` → `Merhaba otuz` → …
3. `StreamingNormalizer` renders it in written form.  The part that stayed the
   same over a few updates is **committed** and never changes on screen again;
   the last few words may still move.
4. When the caller stops, the recognizer returns `is_final=True`.  The whole
   utterance is normalized once more, and the result is exactly what batch
   normalization of the same transcript gives.
5. That written text goes to the LLM.
6. The LLM's reply streams token by token.  `split_sentences` cuts it only at
   complete sentence boundaries, so `25.600` or `15.10.2026` arriving in pieces
   stays whole.
7. Each sentence goes through `TextNormalizer` to the voice.  Speech starts as
   soon as the first sentence is ready, not after the whole reply.

What the screen shows for a real recording, from Mihu STT's partial hypotheses
(committed · may still change):

| Recognizer hypothesis | On screen |
| --- | --- |
| Merhaba otuz dört | Merhaba 34 |
| Merhaba otuz dört de bence bin y | Merhaba 34 de · bence 1.000 y |
| Merhaba otuz dört de bence bin yirmi üç plakalı | Merhaba 34 de · bence 1.023 plakalı |
| (utterance closed) | **Merhaba 34 de bence 1.023 plakalı aracınız hazır.** |

The speaker said "34 ABC 1023"; the recognizer heard "a be ce" as "de bence".
Damga normalizes what it is given and does not invent the plate.

A phone number grows the same way: digits appear in the groups the caller
speaks, and regroup into the phone format once eleven digits make a number.

| Recognizer hypothesis | On screen |
| --- | --- |
| telefon numaram sıfır beş | telefon numaram 0 5 |
| telefon numaram sıfır beş otuz iki yüz yirmi üç | telefon numaram 0 5 32 123 |
| telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi | telefon numaram 0532 123 45 67 |

The call loop in code:

```python
import mihu_stt
from damga import TextNormalizer
from damga.streaming import StreamingNormalizer, split_sentences

stt = mihu_stt.StreamingSTT()          # loaded once when the server starts
tn = TextNormalizer()                  # once, shared by every call

def call(audio_chunks, llm, voice):
    sn = StreamingNormalizer(mode="itn")      # one per call: it holds the commit state
    for chunk in audio_chunks:                # 16 kHz PCM16
        text, is_final = stt.accept_pcm16(chunk, 16000)
        if not text.strip():
            continue
        res = sn.update(text, is_final=is_final)
        show_caption(res.committed, res.provisional)
        if is_final:                          # the caller finished; sn resets itself
            for sentence in split_sentences(llm.stream(res.text)):
                voice.speak(tn.normalize(sentence))
```

What reaches each side for one turn:

| Step | Text |
| --- | --- |
| Caller (recognizer, final) | telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi |
| LLM receives | telefon numaram 0532 123 45 67 |
| LLM writes | Kalan borcunuz 25.600 TL. Son ödeme tarihi 15.10.2026 tarihinde. |
| Voice receives, sentence 1 | Kalan borcunuz yirmi beş bin altı yüz Türk lirası. |
| Voice receives, sentence 2 | Son ödeme tarihi on beş ekim iki bin yirmi altı tarihinde. |

## Call recordings (batch)

For call-center recordings, meetings and voicemail no streaming is needed.
Transcribe, then normalize **each segment on its own**:

```python
import mihu_stt
from damga import InverseNormalizer

itn = InverseNormalizer()
for seg in mihu_stt.transcribe_segments("call.wav"):
    crm.save(seg["start"], itn.normalize(seg["text"]))
```

A segment is one utterance.  Normalizing the joined text instead glues numbers
across a pause into a different value:

| Input | Result |
| --- | --- |
| segment 1: `toplantı saat on` | `toplantı saat 10` |
| segment 2: `beş dakika sürecek` | `5 dk sürecek` |
| both joined (wrong) | `toplantı saat 15 dk sürecek` |

## On-prem and cloud

The code barely changes; only where the transcript comes from does.  Damga
always runs on your side, after the text arrives.

| | Where the recognizer runs | How the text arrives | Example |
| --- | --- | --- | --- |
| Mihu STT on-prem | your CPU (`pip install turkish-stt`); audio never leaves the machine | `mihu_stt.transcribe()` / `StreamingSTT.accept_pcm16()` | [`examples/mihu_stt_onprem.py`](../examples/mihu_stt_onprem.py), [`examples/mic_streaming.py`](../examples/mic_streaming.py) |
| Mihu STT cloud | Mihu's API | `POST {base}/audio/transcriptions` for files, WebSocket `{base}/stream` with one `final` per utterance | [`examples/mihu_stt_cloud.py`](../examples/mihu_stt_cloud.py) |
| ElevenLabs | ElevenLabs' API, both directions | Scribe for STT; `text_to_speech.convert` for TTS with its own text normalization off | [`examples/elevenlabs_stt_tts.py`](../examples/elevenlabs_stt_tts.py) |

On the cloud stream every `final` event is passed to `InverseNormalizer` as it
arrives.  With ElevenLabs (or any voice that normalizes text itself) turn that
off — `apply_text_normalization="off"` — since Damga already sends the spoken
form.  Whisper, Ollama and other engines are in [integrations.md](integrations.md).

## What the tests verify

[`tests/integration/test_voice_pipeline.py`](../tests/integration/test_voice_pipeline.py)
replays this pipeline without network, models or API keys.  The recognizer,
LLM and voice are stand-ins with the same call shapes as the real ones; the
plate hypotheses are the ones Mihu STT emitted for a real recording.

| Test | What it checks |
| --- | --- |
| `test_live_caption_committed_part_never_changes` | Committed caption text only grows; the final caption equals batch ITN of the final transcript |
| `test_live_caption_shows_digits_while_caller_is_still_talking` | The caption at every step while a phone number is dictated |
| `test_real_recording_hypotheses` | Real Mihu STT partials; a misheard plate is not invented back |
| `test_voice_agent_turn_itn_into_llm_tn_into_voice` | Written form into the LLM, whole sentences with no digits into the voice, speech starting before the reply ends |
| `test_two_turns_in_one_call_start_clean` | Nothing from one turn leaks into the next |
| `test_silence_between_turns_is_ignored` | Empty hypotheses during silence do no harm |
| `test_recording_is_normalized_per_segment` | Batch ITN per segment, and why joining is wrong |
| `test_concurrent_calls_share_normalizers_but_not_streaming_state` | Interleaved calls do not mix; shared normalizers are safe across threads |

Run them with `pytest tests/integration`.

## Things to watch

- **One `StreamingNormalizer` per call.**  It holds what has been committed;
  shared between two calls, their captions mix.  `InverseNormalizer` and
  `TextNormalizer` are loaded once and shared: concurrent `normalize()` calls
  are safe (the native runtime releases the GIL).
- **Telephone audio.**  Phone lines usually deliver 8 kHz.  Pass the real rate
  (`accept_pcm16(chunk, 8000)`) and the recognizer resamples, but recognition
  is weaker on narrow-band audio, and Damga cannot fix words the recognizer
  misheard.
- **Latency.**  Damga takes milliseconds per sentence.  The delay a caller
  feels comes from the recognizer and from the trailing silence it waits for
  before closing a turn; tune that in the recognizer, not in Damga.
- **Do not let the LLM repair entities Damga left as words.**  A phone number
  with a missing digit stays as words on purpose; ask the caller to repeat
  instead of letting a model guess the digit.

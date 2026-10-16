# Examples

Damga itself connects to nothing: `pip install damga` has no dependencies and no
recognizer, LLM or voice code inside.  These scripts show how to put it next to
the engine you already use.  Each one is standalone; install what its first
lines say and run it.

**Start here — live microphone, on-prem:**

```bash
pip install damga turkish-stt sounddevice     # Linux: sudo apt install libportaudio2 first
python examples/mic_streaming.py              # --list / --device N to pick the microphone
```

Mihu Turkish STT runs on your CPU, Damga normalizes while you speak; on macOS
allow microphone access for your terminal.  All examples:

| Script | Connects to | Direction | Install |
| --- | --- | --- | --- |
| [`basic_itn.py`](basic_itn.py) | nothing | ITN + TN on a few sentences | `damga` |
| [`try_it.py`](try_it.py) | nothing | type sentences in any of the 7 languages: TN, its other readings, ITN, matching | `damga` |
| [`mihu_stt_onprem.py`](mihu_stt_onprem.py) | Mihu Turkish STT on your CPU | STT → ITN, batch + simulated stream | `damga turkish-stt soundfile` |
| [`mic_streaming.py`](mic_streaming.py) | Mihu Turkish STT + your microphone | live STT → streaming ITN | `damga turkish-stt sounddevice` |
| [`mihu_stt_cloud.py`](mihu_stt_cloud.py) | Mihu Turkish STT cloud API | STT → ITN, file upload + WebSocket stream | `damga` (`websockets` for `--stream`) |
| [`elevenlabs_stt_tts.py`](elevenlabs_stt_tts.py) | ElevenLabs Scribe + voices | STT → ITN and TN → TTS | `damga elevenlabs` |
| [`whisper_itn.py`](whisper_itn.py) | Whisper or faster-whisper | STT → ITN per segment | `damga openai-whisper` or `damga faster-whisper` |
| [`streaming_asr.py`](streaming_asr.py) | any streaming recognizer (simulated) | partial hypotheses → streaming ITN | `damga` |
| [`ollama_tn_tts.py`](ollama_tn_tts.py) | Ollama (any LLM) + any TTS command | LLM → TN → TTS, sentence by sentence | `damga` |
| [`tn_variants_asr.py`](tn_variants_asr.py) | Mihu Turkish STT on your CPU | TN variants: the reading the speaker said, for training text | `damga turkish-stt soundfile` |
| [`tn_variants_lm.py`](tn_variants_lm.py) | a Turkish language model (Hugging Face) on your CPU | TN variants without a recording: the most natural reading | `damga torch transformers` |

```bash
python examples/mihu_stt_onprem.py call.wav
MIHU_STT_BASE_URL=https://<endpoint>/v1 MIHU_STT_API_KEY=... python examples/mihu_stt_cloud.py call.wav --stream
ELEVENLABS_API_KEY=... python examples/elevenlabs_stt_tts.py roundtrip "Borcunuz 2.500,40 TL."
python examples/whisper_itn.py call.wav --engine faster
```

Keys and endpoints come from environment variables; none are stored in the
repository.  Every script follows the same two lines, whatever the engine:

```python
written = InverseNormalizer().normalize(recognizer_text)   # after STT
spoken  = TextNormalizer().normalize(sentence)             # before TTS
```

Step by step, with a live call and a batch transcription:
[docs/voice-pipeline.md](../docs/voice-pipeline.md).  More engines (Vosk,
sherpa-onnx, voice-agent frameworks): [docs/integrations.md](../docs/integrations.md).

---

## Türkçe

Damga'nın kendisi hiçbir yere bağlanmaz: `pip install damga` bağımlılık
getirmez, içinde tanıyıcı, LLM ya da ses kodu yoktur. Bu betikler Damga'yı
zaten kullandığınız motorun yanına nasıl koyacağınızı gösterir. Her biri tek
başına çalışır; ilk satırlarında yazanı kurun ve çalıştırın.

**Buradan başlayın — canlı mikrofon, on-prem:**

```bash
pip install damga turkish-stt sounddevice     # Linux: önce sudo apt install libportaudio2
python examples/mic_streaming.py              # mikrofonu seçmek için --list / --device N
```

Mihu Türkçe STT sizin CPU'nuzda çalışır, siz konuşurken Damga normalize eder;
macOS'ta terminaliniz için mikrofon izni verin. Tüm örnekler:

| Betik | Neye bağlanır | Yön |
| --- | --- | --- |
| `basic_itn.py` | hiçbir şeye | birkaç cümlede ITN + TN |
| `mihu_stt_onprem.py` | kendi CPU'nuzdaki Mihu Türkçe STT | STT → ITN, toplu + canlı akış benzetimi |
| `mic_streaming.py` | Mihu Türkçe STT + mikrofonunuz | canlı STT → akış halinde ITN |
| `mihu_stt_cloud.py` | Mihu Türkçe STT bulut API'si | STT → ITN, dosya yükleme + WebSocket akışı |
| `elevenlabs_stt_tts.py` | ElevenLabs Scribe + sesleri | STT → ITN ve TN → TTS |
| `whisper_itn.py` | Whisper ya da faster-whisper | segment bazlı STT → ITN |
| `streaming_asr.py` | herhangi bir akış tanıyıcı (benzetim) | ara tahminler → akış halinde ITN |
| `ollama_tn_tts.py` | Ollama (herhangi bir LLM) + herhangi bir TTS komutu | LLM → TN → TTS, cümle cümle |
| `tn_variants_asr.py` | kendi CPU'nuzdaki Mihu Türkçe STT | TN varyantları: eğitim metni için konuşmacının söylediği okunuş |
| `tn_variants_lm.py` | CPU'nuzda Türkçe bir dil modeli (Hugging Face) | kayıt olmadan TN varyantları: en doğal okunuş |

Anahtarlar ve adresler ortam değişkenlerinden okunur; repoda hiçbiri yoktur.
Adım adım anlatım: [docs/voice-pipeline.tr.md](../docs/voice-pipeline.tr.md).

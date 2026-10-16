# Damga bir ses akışında nasıl çalışır

*English: [voice-pipeline.md](voice-pipeline.md)*

Damga, ses akışının iki ucunda duran normalizasyon katmanıdır: tanıyıcının
konuşma dilindeki çıktısını yazı diline (ITN), LLM'in yazdığı metni de sesin
okuyacağı biçime (TN) çevirir. Damga'nın içinde tanıyıcı, LLM ya da ses motoru
yoktur; hangisini kullanırsanız kullanın aynı şekilde çalışır.

```
müşteri konuşur → STT → Damga ITN → yazılı metin → LLM / CRM / ekran
LLM / veritabanı → yazılı metin → Damga TN → sözlü metin → TTS → müşteri duyar
```

İki kural her entegrasyonu kapsar:

1. **ITN tanıyıcının hemen arkasına gelir.** Metni okuyan her şey (LLM, CRM,
   ekran, veritabanı) rakamları hazır görür:
   `sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi` yerine `0532 123 45 67`.
2. **TN sesin hemen önüne gelir.** LLM `2.500,40 TL` yazar, ses "iki bin beş
   yüz lira kırk kuruş" okur; tutar, tarih ve telefon her seferinde aynı şekilde
   okunur.

Akış halinde çalışan tanıyıcılar için bir kural daha: Damga'ya her seferinde
**o anki cümlenin en son tam tahmini** gönderilir, yalnızca yeni gelen parça
değil. Tanıyıcı cümleyi kapatınca `is_final=True` ile çağrılır.

## Canlı görüşme / sesli asistan

En yaygın kullanım budur: müşteri konuşurken ekranda canlı altyazı oluşur,
cümlesini bitirince LLM yazılı metni alır ve cevap cümle cümle seslendirilir.
Bir görüşme turu şöyle ilerler:

1. Mikrofon, WebRTC ya da telefon hattı her 20–100 ms'de bir ses parçası gönderir.
2. Tanıyıcı her parçada büyüyen bir tahmin döner: `Mer` → `Merhaba` → `Merhaba otuz` → …
3. `StreamingNormalizer` bu tahmini yazılı biçime çevirir. Birkaç güncelleme
   boyunca değişmeyen kısım **kesinleşir** ve ekranda bir daha değişmez; sondaki
   birkaç kelime hâlâ oynayabilir.
4. Müşteri susunca tanıyıcı `is_final=True` döner. Cümlenin tamamı bir kez daha
   normalize edilir; sonuç, aynı metni toplu normalize etmekle birebir aynıdır.
5. Bu yazılı metin LLM'e gider.
6. LLM'in cevabı token token gelir. `split_sentences` metni yalnızca tamamlanmış
   cümle sınırlarında keser; `25.600` ya da `15.10.2026` parça parça gelse de
   bölünmez.
7. Her cümle `TextNormalizer`'dan geçip sese gider. İlk cümle hazır olunca
   konuşma başlar; LLM'in tüm cevabı beklenmez.

Gerçek bir kayıtta Mihu STT'nin ara tahminleri ve ekranda görünenler
(kesinleşen · hâlâ değişebilen):

| Tanıyıcının tahmini | Ekranda |
| --- | --- |
| Merhaba otuz dört | Merhaba 34 |
| Merhaba otuz dört de bence bin y | Merhaba 34 de · bence 1.000 y |
| Merhaba otuz dört de bence bin yirmi üç plakalı | Merhaba 34 de · bence 1.023 plakalı |
| (cümle kapandı) | **Merhaba 34 de bence 1.023 plakalı aracınız hazır.** |

Konuşmacı "34 ABC 1023" dedi; tanıyıcı "a be ce"yi "de bence" diye duydu.
Damga kendisine verileni normalize eder, plakayı uydurmaz.

Telefon numarası da aynı şekilde büyür: rakamlar müşterinin söylediği gruplar
halinde görünür, on bir hane bir numara oluşturunca telefon biçimine oturur.

| Tanıyıcının tahmini | Ekranda |
| --- | --- |
| telefon numaram sıfır beş | telefon numaram 0 5 |
| telefon numaram sıfır beş otuz iki yüz yirmi üç | telefon numaram 0 5 32 123 |
| telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi | telefon numaram 0532 123 45 67 |

Görüşme döngüsü kod olarak:

```python
import mihu_stt
from damga import TextNormalizer
from damga.streaming import StreamingNormalizer, split_sentences

stt = mihu_stt.StreamingSTT()          # sunucu açılırken bir kez yüklenir
tn = TextNormalizer()                  # bir kez, tüm görüşmeler paylaşır

def gorusme(ses_parcalari, llm, ses):
    sn = StreamingNormalizer(mode="itn")      # her görüşmeye ayrı: kesinleşen kısmı tutar
    for parca in ses_parcalari:               # 16 kHz PCM16
        metin, bitti = stt.accept_pcm16(parca, 16000)
        if not metin.strip():
            continue
        sonuc = sn.update(metin, is_final=bitti)
        altyazi_goster(sonuc.committed, sonuc.provisional)
        if bitti:                             # müşteri sözünü bitirdi; sn kendini sıfırlar
            for cumle in split_sentences(llm.stream(sonuc.text)):
                ses.konus(tn.normalize(cumle))
```

Bir turda her tarafa ulaşan metin:

| Adım | Metin |
| --- | --- |
| Müşteri (tanıyıcı, son hali) | telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi |
| LLM'e giden | telefon numaram 0532 123 45 67 |
| LLM'in yazdığı | Kalan borcunuz 25.600 TL. Son ödeme tarihi 15.10.2026 tarihinde. |
| Sese giden, 1. cümle | Kalan borcunuz yirmi beş bin altı yüz Türk lirası. |
| Sese giden, 2. cümle | Son ödeme tarihi on beş ekim iki bin yirmi altı tarihinde. |

## Kayıt dökümü (toplu)

Çağrı merkezi kayıtları, toplantılar ve sesli mesajlar için akış gerekmez.
Döküm alınır, sonra **her segment ayrı ayrı** normalize edilir:

```python
import mihu_stt
from damga import InverseNormalizer

itn = InverseNormalizer()
for seg in mihu_stt.transcribe_segments("gorusme.wav"):
    crm.kaydet(seg["start"], itn.normalize(seg["text"]))
```

Bir segment bir konuşma parçasıdır. Metni birleştirip normalize etmek, bir
duraklamanın iki yanındaki sayıları yapıştırıp başka bir değer üretir:

| Girdi | Sonuç |
| --- | --- |
| 1. segment: `toplantı saat on` | `toplantı saat 10` |
| 2. segment: `beş dakika sürecek` | `5 dk sürecek` |
| ikisi birleşik (yanlış) | `toplantı saat 15 dk sürecek` |

## On-prem ve bulut

Kod neredeyse hiç değişmez; değişen yalnızca metnin nereden geldiğidir. Damga
her zaman sizin tarafınızda, metin geldikten sonra çalışır.

| | Tanıyıcı nerede çalışır | Metin nasıl gelir | Örnek |
| --- | --- | --- | --- |
| Mihu STT on-prem | sizin CPU'nuzda (`pip install turkish-stt`); ses makineden çıkmaz | `mihu_stt.transcribe()` / `StreamingSTT.accept_pcm16()` | [`examples/mihu_stt_onprem.py`](../examples/mihu_stt_onprem.py), [`examples/mic_streaming.py`](../examples/mic_streaming.py) |
| Mihu STT bulut | Mihu'nun API'sinde | dosya için `POST {base}/audio/transcriptions`, canlı ses için WebSocket `{base}/stream`, her konuşma parçası için bir `final` | [`examples/mihu_stt_cloud.py`](../examples/mihu_stt_cloud.py) |
| ElevenLabs | ElevenLabs'in API'sinde, iki yönde de | STT için Scribe; TTS için kendi metin normalizasyonu kapalı `text_to_speech.convert` | [`examples/elevenlabs_stt_tts.py`](../examples/elevenlabs_stt_tts.py) |

Bulut akışında her `final` olayı geldiği anda `InverseNormalizer`'a verilir.
ElevenLabs'te (ya da metni kendisi normalize eden her seste) bunu kapatın —
`apply_text_normalization="off"` — çünkü Damga zaten okunuş biçimini gönderir.
Whisper, Ollama ve diğer motorlar [integrations.md](integrations.md) içinde.

## Testler neyi doğruluyor

[`tests/integration/test_voice_pipeline.py`](../tests/integration/test_voice_pipeline.py)
bu akışı ağ, model ya da API anahtarı olmadan baştan sona oynatır. Tanıyıcı,
LLM ve ses, gerçeklerle aynı çağrı biçimine sahip sahte nesnelerdir; plaka
tahminleri Mihu STT'nin gerçek bir kayıtta ürettikleridir.

| Test | Neyi kontrol eder |
| --- | --- |
| `test_live_caption_committed_part_never_changes` | Kesinleşen altyazı yalnızca uzar; son altyazı, son dökümün toplu ITN'i ile aynıdır |
| `test_live_caption_shows_digits_while_caller_is_still_talking` | Telefon numarası söylenirken her adımdaki altyazı |
| `test_real_recording_hypotheses` | Gerçek Mihu STT ara tahminleri; yanlış duyulmuş plaka uydurulmaz |
| `test_voice_agent_turn_itn_into_llm_tn_into_voice` | LLM'e yazılı biçim, sese rakamsız tam cümleler, cevap bitmeden başlayan konuşma |
| `test_two_turns_in_one_call_start_clean` | Bir turdan sonrakine bir şey taşmaz |
| `test_silence_between_turns_is_ignored` | Sessizlikteki boş tahminler sorun çıkarmaz |
| `test_recording_is_normalized_per_segment` | Segment bazlı toplu ITN ve birleştirmenin neden yanlış olduğu |
| `test_concurrent_calls_share_normalizers_but_not_streaming_state` | İç içe ilerleyen görüşmeler karışmaz; paylaşılan normalizer'lar iş parçacıkları arasında güvenlidir |

Çalıştırmak için: `pytest tests/integration`.

## Dikkat edilmesi gerekenler

- **Her görüşmeye bir `StreamingNormalizer`.** Neyin kesinleştiğini tutar; iki
  görüşme aynısını paylaşırsa altyazılar karışır. `InverseNormalizer` ve
  `TextNormalizer` ise bir kez yüklenip paylaşılır: aynı anda yapılan
  `normalize()` çağrıları güvenlidir (native runtime GIL'i bırakır).
- **Telefon sesi.** Telefon hatları genelde 8 kHz verir. Gerçek örnekleme
  hızını verin (`accept_pcm16(parca, 8000)`), tanıyıcı yeniden örnekler; ama
  dar bantlı seste tanıma daha zayıftır ve Damga tanıyıcının yanlış duyduğu
  kelimeleri düzeltemez.
- **Gecikme.** Damga bir cümleyi milisaniyeler içinde işler. Müşterinin
  hissettiği gecikme tanıyıcıdan ve tanıyıcının cümleyi kapatmadan önce
  beklediği sessizlikten gelir; bunu Damga'da değil tanıyıcıda ayarlayın.
- **LLM'in, Damga'nın kelime olarak bıraktığı şeyleri "düzeltmesine" izin
  vermeyin.** Bir hanesi eksik telefon numarası bilerek kelime olarak kalır;
  modelin eksik haneyi tahmin etmesi yerine müşteriden tekrar etmesini isteyin.

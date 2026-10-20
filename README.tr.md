# Damga — Metin Normalizasyonu (TN) ve Ters Metin Normalizasyonu (ITN)

[English README](README.md)

**Damga** (PyPI adı: `damga`), ağırlıklı sonlu durum dönüştürücüleri
üzerine kurulu, açık kaynak, tamamen çevrimdışı ve
deterministik bir metin normalizasyon motorudur; varsayılan dili Türkçedir
([diller](#diller)). Konuşma tanıyıcının
*duyduğunu* insanların *yazdığı* biçime çevirir (ITN); bir dil modelinin ya da
veritabanının *yazdığını* TTS sesinin *söyleyeceği* biçime çevirir (TN):

| Yön | Girdi | Çıktı |
|---|---|---|
| ITN (sözlü → yazılı) | `yirmi beş bin altı yüz` | `25.600` |
| ITN | `yüz elli türk lirası` | `150 TL` |
| ITN | `saat dokuz otuzda` | `saat 09:30'da` |
| ITN | `sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi` | `0532 123 45 67` |
| ITN | `derya nokta öztürk et gmail nokta com` | `derya.ozturk@gmail.com` |
| ITN | `otuz dört a b c sekiz yüz kırk iki` | `34 ABC 842` |
| TN (yazılı → sözlü) | `25.600` | `yirmi beş bin altı yüz` |
| TN | `2,50 TL` | `iki lira elli kuruş` |
| TN | `15.10.2026 saat 09:30` | `on beş ekim iki bin yirmi altı saat dokuz otuz` |

Neden model değil de gramer motoru:

* **Deterministik.** Aynı girdi her zaman aynı çıktıyı verir; her davranış
  okuyup değiştirebileceğiniz bir altın test satırıdır.
* **Hassas varlıklarda güvenli.** Telefon, IBAN ve plaka asla tamamlanmaz ya da
  "onarılmaz": hane sayısı tutmuyorsa kelimeler kelime kalır.
* **Hızlı ve küçük.** Tek CPU çekirdeğinde cümle başına milisaniyenin altı; GPU,
  ağ ve LLM yok; wheel sıfır bağımlılıkla kurulur.
* **Gerçek tanıyıcılar için.** Gramerler ASR'nin gerçekten ürettiği karışık
  biçimleri kabul eder: sözlü sayı içinde yazılı rakam, telefon numarasının
  ortasında noktalama, yapışık ayırıcılar, yanlış duyulan e-posta domainleri.
* **İki yön, tek gramer seti.** TN sayı okunuşu ITN sayı gramerinin tam
  tersidir; iki yön hiçbir sayıda birbirinden ayrılamaz.

## Kurulum

```bash
pip install damga                 # Linux, macOS, Windows — başka bağımlılık yok
pip install "damga[build]"        # + pynini, yalnız gramer yazan/değiştirenler için
```

Wheel, yedi dilin önceden derlenmiş gramerlerini ve küçük bir yerel çalışma zamanını
(`damga._fstrt`, statik bağlanmış OpenFst) içerir; kullanıcı makinesinde hiçbir
şey derlenmez, çalışma anında pynini gerekmez. Gramer yazanlar `build` extra'sını
kurar (pynini'nin PyPI'da Linux wheel'ı vardır; macOS'ta
`conda install -c conda-forge pynini`) ve bir grameri değiştirince
`python -m damga.build` çalıştırır. pynini kuruluysa `backend="pynini"` (ya da
`DAMGA_BACKEND=pynini`) gramerleri canlı çalıştırır; özel kategori seçimleri
otomatik olarak onu kullanır.

## Hızlı başlangıç: mikrofonunuz, kendi makinenizde

Damga'yı görmenin en hızlı yolu canlı konuşma. Mihu Türkçe STT sizin
CPU'nuzda çalışır (GPU, bulut ya da API anahtarı yok); siz konuşurken Damga
duyulanı yazılı metne çevirir:

```bash
git clone https://github.com/mihu-ai/damga && cd damga
pip install damga turkish-stt sounddevice     # Linux: önce sudo apt install libportaudio2
python examples/mic_streaming.py              # --list giriş cihazlarını gösterir, --device N seçer
```

*"telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi"* deyin:

```
 … telefon numaram 0 5 32 123
[01] STT : telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi
     ITN : telefon numaram 0532 123 45 67
```

Siz konuşurken satır güncellenir; durduğunuzda son hali yazılır. Tanıyıcı
modeli (yaklaşık 70 MB) ilk çalıştırmada bir kez iner. macOS'ta terminaliniz
için mikrofon izni verin (Sistem Ayarları → Gizlilik ve Güvenlik → Mikrofon).
Diğer motorlar (Mihu STT bulut, ElevenLabs, Whisper, Ollama):
[`examples/`](examples/README.md).

## Kullanım

```python
from damga import InverseNormalizer, TextNormalizer, Normalizer

itn = InverseNormalizer()
itn.normalize("yüz elli lira")                    # '150 TL'
itn.normalize_batch(["on beş ekim", "yüzde on"])  # ['15 Ekim', '%10']

tn = TextNormalizer()
tn.normalize("Toplam 25.600 adet, %12,5 indirim.")
# 'Toplam yirmi beş bin altı yüz adet, yüzde on iki virgül beş indirim.'
```

Seçenekler (hepsi anahtar kelime argümanı, hepsi isteğe bağlı):

| seçenek | anlamı |
|---|---|
| `categories=[...]` | `cardinal ordinal decimal money percent measure time date telephone iban plate email address spelling lexicon_entry` sınıflarının alt kümesi (pynini gerekir) |
| `strict=True` | temkinli ITN: çıplak sayılar kelime kalır, yalnız anahtar kelime/yapı güdümlü sınıflar çalışır (pynini gerekir) |
| `custom_vocab={"e te es tur": "ETS Tur"}` | kendi sözlü → yazılı terimleriniz (her tablodan önce gelir) |
| `cache_dir=...` / `use_cache=False` | derlenmiş gramer (FAR) önbelleği; varsayılan `~/.cache/damga`, `DAMGA_CACHE_DIR` ile değişir |
| `group_thousands=False` | `25.600` yerine `25600` |
| `group_four_digits=False` | ITN: dört basamaklı sayılarda binlik noktası yok (`2024 seçimleri`, `1500 kişi`); beş ve daha fazla basamak noktalı kalır (pynini gerekir) |
| `scale_words=True` | ITN: yuvarlak milyon ve üstü ölçek kelimesiyle yazılır (`beş milyon` → `5 milyon`, `elli altı milyar` → `56 milyar`), `5.000.000` yerine (pynini gerekir) |
| `preserve_case=False` | dokunulmayan kelimelerin tanıyıcı büyük/küçük harfini korumak yerine her şeyi küçült |
| `diagnostics=True` | `normalize_with_details()` ara kaydı (record) saklar |
| `repair_spelling=True` | aksansız (`yuz elli`) ve bitişik (`onbeş`) sayı sözcüklerini gramerlerden önce düzeltir; `False` metni olduğu gibi verir |
| `backend="auto" \| "native" \| "pynini"` | çalışma zamanı seçimi (aşağıya bakın) |
| `variants=True` | yalnız TN: `normalize_variants()` bir biçimin diğer okunuşlarını da listeler (aşağıya bakın) |

Diğer diller için yazım tarzı seçenekleri (varsayılan kapalı; çıktı üzerinde çalışan basit bir son adım olduğu için pynini gerekmez):

| dil / mod | seçenek | etkisi |
|---|---|---|
| `en` ITN | `unit_symbols=True` | sayıdan sonraki birim sembolle yazılır: `two hundred kilometers per hour` → `200 km/h`, `twenty five square meters` → `25 m²`, `minus five degrees celsius` → `-5 °C` |
| `es` TN | `formal_ordinals=True` | 11–100 arası sıra sayıları sayma sayısı yerine sıra sözcüğüyle okunur: `el 80.º aniversario` → *el octogésimo aniversario*, `la 11.ª edición` → *la undécima edición* |
| `ru` ITN | `ordinal_digits=True` | 1–9 sıra sayıları rakam ve kısa ekle yazılır: `восьмого` → `8-го`, `на пятом этаже` → `на 5-м этаже` (10 ve üstü zaten rakamla yazılır) |
| `de` ITN | `fraction_digits=True` | kesirler eğik çizgiyle yazılır: `drei viertel` → `3/4`, `zweieinhalb Stunden` → `2 1/2 Stunden`; `die Hälfte`, `ein Viertel der Stadt` kelime kalır |

```python
from damga import InverseNormalizer
InverseNormalizer(lang="en", unit_symbols=True).normalize("two hundred kilometers per hour")   # "200 km/h"
```

### Tek okunuş (varsayılan) ya da varyantlar

Damga varsayılan olarak **tek okunuş** verir: bir yazılı biçim, her seferinde
tek bir okunuş. Sesli asistanın ihtiyacı budur ve `normalize()` her zaman böyle
çalışır: tek CPU çekirdeğinde cümle başına yaklaşık 1 ms, her görüşmede aynı
okunuş. Okunuşu bir dil modeliyle seçmek TTS başlamadan önce cümle başına
0,3–2 saniye ekler; bu yüzden sesli yapay zekâda varsayılanı
kullanın.

Bazı biçimleri Türkçe konuşanlar birden fazla şekilde okur (`09:30` *dokuz
otuz* da olur *dokuz buçuk* da). `variants=True` ile TN bu okunuşları da,
varsayılan önce gelecek şekilde listeler. Konuşmacının gerçekten söylediğiyle
eşleşen **TTS ya da ASR eğitim metni** hazırlamak için kullanılır:

```python
tn = TextNormalizer(variants=True)
tn.normalize("Saat 09:30'da")             # 'Saat dokuz otuzda'  (değişmez)
tn.normalize_variants("Saat 09:30'da")    # ['Saat dokuz otuzda', 'Saat dokuz buçukta']
tn.normalize_variants("2,50 TL")          # ['iki lira elli kuruş', 'iki Türk lirası elli kuruş', 'iki buçuk lira']
tn.normalize_matching("Saat 09:30'da", heard="saat dokuz buçukta")   # 'Saat dokuz buçukta'
```

ITN'de varyant yoktur: bir telefon numarasının ya da tutarın tek yazılı
biçimi vardır ve birkaçı arasında tahmin yürütmek ITN'in tam da yapmaması
gereken şeydir. 1.0'da bu seçeneğin adı `deterministic` idi
(`deterministic=False`); eski ad hâlâ `DeprecationWarning` ile çalışır.
Ayrıntı: [docs/variants.tr.md](docs/variants.tr.md).

### Canlı ASR için akış (streaming) ITN

```python
from damga.streaming import StreamingNormalizer

sn = StreamingNormalizer(mode="itn")
sn.update("yirmi beş", is_final=False).text              # '25'      (geçici)
sn.update("yirmi beş bin", is_final=False).text          # '25.000'  (hâlâ geçici, hiçbir şey sabitlenmedi)
sn.update("yirmi beş bin altı yüz", is_final=True).text  # '25.600'  (kesin, durum sıfırlanır)
```

`update()` her zaman o anki cümlenin **en son tam hipotezini** alır. Bir önek
yalnızca `stable_after` güncelleme boyunca değişmediyse *ve* bir gramerin hâlâ
uzatabileceği bir dizinin ortasında bitmiyorsa sabitlenir; dolayısıyla sayı
erken dondurulmaz. Kesin sonuç her zaman cümlenin bütününün toplu
normalizasyonuna eşittir. Ayrıntı: [docs/streaming.md](docs/streaming.md).

## Nasıl çalışır: token tabanlı, iki geçişli WFST boru hattı

Damga **token tabanlı** bir normalizer'dır. Normalizasyon tek büyük bir
sözlü → yazılı yeniden yazım değildir; arasında yapılı ve okunabilir bir token
dizisi bulunan iki dönüştürücüdür:

```
"toplam yirmi beş bin altı yüz lira kırk kuruş ödedim"
        │
        │  1. geçiş — reader FST (tüm okuyucuların ağırlıklı birleşimi)
        ▼
word="toplam" money(integer="25600" fractional="40" currency="TL") word="ödedim"
        │
        │  2. geçiş — writer FST (tüm yazıcıların birleşimi)
        ▼
"toplam 25.600,40 TL ödedim"
```

* **1. geçiş, okuma.** Her anlam sınıfı (`cardinal`, `money`, `time`,
  `telephone`, `email`, …) sözlü bir parçayı `sınıf(alan="değer" …)`
  tokenına çeviren küçük bir gramerdir. Hiçbir sınıfın almadığı kelimeler
  `word="…"` olarak geçer. Cümle okuyucusu tüm sınıf okuyucularının ağırlıklı
  birleşimidir; en iyi çözümleme kafesteki **en kısa yol**dur. Bir anlam sınıfı
  yaklaşık 1, kelime geçişi token başına 100 maliyetlidir; dolayısıyla eşleşen
  her gramer kelimeleri olduğu gibi bırakmaya üstün gelir, gramerler arasında
  da daha özgül olan kazanır (`iban` < `email` < `telephone` < `money` < `cardinal`).
* **2. geçiş, yazıya dökme.** Her sınıfın tokenını yazan bir yazıcısı
  vardır: `money` para birimi simgesini tutarın arkasına koyar, `time`
  sıfırla doldurup hâl ekini geri takar (`saat 09:30'da`), `telephone` rakamları
  Türkiye'deki gibi gruplar. Alanlar okuyucu tarafından sabit sırada üretilir,
  bu yüzden iki geçiş arasında **Python yeniden sıralama katmanı yoktur**:
  boru hattının tamamı iki birleştirme ve iki en kısa yol aramasıdır.

Metni doğrudan yeniden yazan tek geçişli ("tokensiz") bir dönüştürücü yerine
neden token tabanlı?

| | token tabanlı (Damga) | tek geçişli yeniden yazım |
|---|---|---|
| sınıf ekleme | diğerlerinden bağımsız bir okuyucu + bir yazıcı | her yeni kural tek gramerdeki her eski kuralla etkileşir |
| öncelik | sınıf başına tek ağırlık, tek tabloda | kural sırası ve bağlamda örtük |
| hata ayıklama | `diagnostics=True` ara kaydı gösterir; *nasıl* yazıldığından önce *neyin* tanındığı görülür | yalnız girdi ve çıktı |
| TN ↔ ITN | iki yönde aynı token protokolü; TN sayı yazıcıları ITN sayı gramerinin tersi | iki ilgisiz gramer |
| biçim değişikliği | yalnız yazıcı değişir, okuyuculara dokunulmaz (`100 $` / `$100`, `25600` / `25.600`) | tanıma kurallarına dokunulur |
| maliyet | cümle başına iki birleştirme | bir |

İkinci birleştirme ucuzdur (yazıcı birkaç yüz durumludur); token katmanı
milisaniyenin çok altına mal olur ve karşılığında birleşebilirlik, okunabilir
bir ara biçim ve etiket düzeyinde altın testler sağlar. Sayı grameri temeldir:
sabit genişlikli, sıfırla doldurulmuş alt graflar (iki hane, üç hane, binler,
milyonlar …) baştaki sıfırları atan bir dönüştürücüyle birleştirilir ve sayı
içeren her sınıf tarafından yeniden kullanılır. Belirsizlik kodla değil yol
ağırlıklarıyla çözülür: standart dışı `bir yüz` ceza taşır; yuvarlak kelimeyle
biten bir telefon grubu (`otuz`, `iki yüz`) cezalandırılır ki
`beş yüz otuz iki yüz yirmi üç` → `532 | 123` okunsun. Ayrıntı:
[docs/architecture.md](docs/architecture.md).

### Çalışma zamanı

Gramerler Pynini ile yazılır ve dil + yön başına iki OpenFst dosyasına bir kez
derlenir (`damga/<dil>/<yön>/compiled/`). Çalışma anında yerel uzantı
`damga._fstrt` (statik bağlı OpenFst, ~2 MB) bunları yükler ve
*girdi zinciri ∘ FST → en kısa yol* işlemini C++'ta yapar; arama sırasında GIL
serbest bırakılır. pynini kuruluysa gramerler canlı da çalıştırılabilir
(`backend="pynini"`); gramer yazarları ve özel kategori seçimleri bunu kullanır.
İki backend aynı dönüştürücüleri çalıştırır ve aynı çıktıyı verdikleri test edilir.

## Konuşma tanıyıcılar ve dil modelleriyle kullanım

Damga, tanıyıcı ile metni tüketen şey arasında; metin üreten şey ile TTS sesi
arasında durur:

```
mikrofon → ASR (Mihu STT, Whisper, …) → Damga ITN → yazılı metin → LLM / CRM / ekran
LLM (Ollama, …) / veritabanı → yazılı metin → Damga TN → sözlü metin → TTS
```

### Mihu Türkçe STT

[`turkish-stt`](https://github.com/mihu-ai/turkish-stt) (model:
[`mihuai/turkish-stt-66m-v2`](https://huggingface.co/mihuai/turkish-stt-66m-v2)), konuşma sonu
algılamalı, yalnız CPU ile çalışan gerçek zamanlı bir Türkçe tanıyıcıdır.
Sayıları kelimeyle yazar; Damga onları yazılı biçime çevirir. Damga ona bağımlı
değildir. turkish-stt 2.0'dan itibaren `mihu_stt.transcribe(..., itn=True)`
(`pip install "turkish-stt[itn]"`) Damga'yı sizin yerinize çalıştırır; aşağıdaki açık
kullanım ise streaming üzerinde tam kontrol verir:

```python
import mihu_stt                                # pip install turkish-stt (on-prem, CPU)
from damga import InverseNormalizer
from damga.streaming import StreamingNormalizer

itn = InverseNormalizer()
print(itn.normalize(mihu_stt.transcribe("ses.wav")))     # "… sıfır beş otuz iki …" → "… 0532 …"

stt, sn = mihu_stt.StreamingSTT(), StreamingNormalizer(mode="itn")
for pcm16_chunk in audio_frames():             # 16 kHz int16 byte'lar, geldikleri gibi
    text, is_final = stt.accept_pcm16(pcm16_chunk, 16000)
    if text.strip():
        res = sn.update(text, is_final=is_final)
        show(res.text)                         # o anki en iyi görünüm, sonu hâlâ değişebilir
        if is_final:                           # tanıyıcı konuşma sonunu algıladı
            handle(res.text)                   # == itn.normalize(text)
```

Aynı tanıyıcı bulut API'si olarak da kullanılabilir; dökümleri aynı şekilde
`itn.normalize`'dan geçer. `examples/mihu_stt_onprem.py`,
`examples/mihu_stt_cloud.py` ve `examples/elevenlabs_stt_tts.py` (ElevenLabs
STT + TTS) tam çalışan betiklerdir; [docs/voice-pipeline.tr.md](docs/voice-pipeline.tr.md)
canlı bir görüşmeyi ve toplu dökümü adım adım anlatır.

### Whisper, Ollama ve diğer boru hatları

[docs/integrations.md](docs/integrations.md) ve [`examples/`](examples/README.md) klasörü Damga'yı
**Whisper / faster-whisper** arkasına (toplu ve segment bazlı ITN; Whisper'ın
karışık `40 bir` çıktısının neden ITN'e ihtiyaç duyduğu), **Ollama** ya da başka
bir LLM'in beslediği TTS sesinin önüne (akan yanıtta cümle bazlı TN) ve genel
bir akış tanıyıcı döngüsüne (Vosk, sherpa-onnx, bulut ASR partial'ları) nasıl
koyacağınızı gösterir. Her akış kaynağı için temel kural: Damga'ya tanıyıcının
*en son tam hipotezini* gönderin, farkı değil.

## NLP ve veri işleri için kullanım

Damga yalnızca ses ürünleri için değildir. Konuşulmuş ya da döküme çevrilmiş
Türkçe (veya İngilizce, Almanca, …) metinle çalışan her iş, sayıları, tarihleri,
tutarları ve tanımlayıcıları tek bir yazılı biçimde alır; NER modellerinin,
düzenli ifadelerin, veritabanlarının ve dil modellerinin en iyi işlediği biçim:

```python
from damga import InverseNormalizer, TextNormalizer
itn = InverseNormalizer()

itn.normalize("müşteri yirmi beş bin lira iade istiyor")
# müşteri 25.000 TL iade istiyor
itn.normalize("on dört haziranda saat dokuz buçukta arayın, numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi")
# 14 Haziran'da saat 09:30'ta arayın, numaram 0532 123 45 67
itn.normalize("plakam otuz dört a b c yüz yirmi üç, e posta adresim ali nokta yılmaz et gmail nokta com")
# plakam 34 ABC 123, e posta adresim ali.yilmaz@gmail.com
```

* **Çağrı merkezi ve toplantı analitiği:** tutarlar toplanıp filtrelenebilen
  sayılara dönüşür (5.000 TL üstü şikâyetler), tarih ve saatler kıyaslanabilir.
* **Bilgi çıkarma:** telefon, IBAN, plaka, e-posta, tarih ve tutarlar NER
  modelinizin ya da düzenli ifadenizin beklediği biçimde gelir.
* **Arama:** *on dört haziran* denen bir görüşme `14 Haziran` aramasıyla bulunur.
* **Dil modeli girdisi:** tutarlı yazılmış sayılar, daha az token, daha doğru
  hesap.
* **Adil ASR değerlendirmesi:** referans ve hipotez aynı biçime getirilir;
  *yirmi beş kişi* ile `25 kişi` iki hata sayılmaz.
* **TTS ve ASR eğitim verisi:** `normalize_matching` her cümleyi kaydında
  gerçekte nasıl söylendiyse öyle yazar:

```python
tn = TextNormalizer(variants=True)
tn.normalize_matching("Saat 09:30'da 250 TL ödendi.", "saat dokuz buçukta iki yüz elli lira ödendi")
# Saat dokuz buçukta iki yüz elli lira ödendi.
```

Damga, söylenişinden farklı yazılan biçimleri normalleştirir (sayı, tarih,
saat, para, ölçü, telefon, IBAN, plaka, e-posta ve web adresi). Genel bir metin
temizleyici değildir: argo, yazım hataları ve kök bulma, yanında rahatça
çalışan Zemberek gibi araçlara bırakılır.

## Kapsam

ITN: sayılar (yapışık hâl ekiyle: `yirmi altıda` → `26'da`), sıra sayıları, negatifler, ondalıklar, para (TL/$/€/£ + kuruş/sent),
yüzde/binde, ölçü birimleri, saat (`saat dokuz otuz`, `dokuzu çeyrek geçe`,
`dokuza on kala`, hâl ekleri), tarih (`on beş ekim iki bin yirmi altı`, `ekimde`,
`yılında`, `iki bin yirmi altıda` → `2026'da`), Türk telefon numaraları (her gruplama, `+90`), IBAN, plaka (harf,
harf adı veya fonetik alfabe), e-posta ve web adresleri, adres
(`numara on iki daire yedi` → `No: 12 Daire: 7`), Türkçe harf kodlama alışkanlığı
(`Diyarbakır'ın D'si Edirne'nin E'si …` → `De…`), kısaltmalar, markalar ve özel
sözlük. TN aynı sınıfları yazılı → sözlü yönde kapsar; kesme işaretli ekler
(`2026'da`, `25'te`, `3'üncüsü`) dâhil.

Bilinen sınırlar [docs/grammars.md](docs/grammars.md) dosyasında (ör. tek
başına `bir` belirsiz tanımlık sayılır, çıplak dört haneli sayılar yıl olarak
okunmaz, ITN'de `üçüncüsü` gibi çekimli sıra sayıları çevrilmez).

## Markalar, domainler ve özel terimler

Üç veri katmanı, hepsi `damga/tr/itn/data/` altında düz TSV (kaynak ve
lisanslar için oradaki README'ye bakın):

* `brands.tsv` — resmî yazımıyla ve Türkçe yanlış duyuluşlarıyla elle yazılmış
  marka/ürün adları (`vatsap` → WhatsApp, `peypal` → PayPal, `a ve es` → AWS);
* `brands_extra.tsv` — ~700 tanınmış işletme, marka ve Türk kurumu; yaygın
  Türkçe kelimeler elenmiş;
* `domains.tsv` + `email_providers.tsv` — yanlış duyulan posta domainleri
  (`cimil` → gmail, `yahu` → yahoo) ve `free-email-domains` (MIT) kaynaklı
  ~7 800 ücretsiz posta sağlayıcı etiketi; bilinen bir sağlayıcıdan önce düşen
  "et"i kurtarmak için kullanılır.  Tablo dışındaki yazımlar (`giymiel` gibi)
  duyulduğu gibi bırakılır: bu bir tanıyıcı hatasıdır ve çözümü normalizer'da
  tahmin değil, aynı listelerle tanıyıcıda bağlamsal yönlendirmedir (hotword).

Kendi terimleriniz `custom_vocab={...}` ile girilir (her tablodan önce gelir).
Bunların hiçbiri tanıyıcıyı yeniden eğitmeyi gerektirmez; tanıyıcı düzeyinde
kapsam için aynı listelerle bağlamsal yönlendirme (hotword) kullanın.

## Gerçek tanıyıcı çıktısı

Tanıyıcılar temiz sözlü biçim üretmez. Mihu STT örneğin
`Sabit hattımız sıfır 5, 3-74, bir dokuz, sekiz yedi bir sekiz` ya da
`Burak Nokta Koçet örnek banka nokta kom nokta Tier` verir. Bu yüzden ITN
gramerleri sözlü dizi içindeki yazılı rakamları, sayı içindeki noktalamayı,
yapışık ayırıcıları (`koçet`, `noktaçelik`, `etörnek`), yanlış duyulan
TLD'leri (`kom`, `tier`, `ay`) ve yanlış duyulan domain tablosunu
(`damga/tr/itn/data/domains.tsv`) kabul eder.

575 gerçek Mihu-STT transkripti üzerinde ölçüm (sentetik telefon/e-posta
cümleleri; 84 tanesi `tests/golden/itn_asr.tsv` içinde): telefon 256/256
birebir, e-posta 274/319 birebir (kalanlar "et" düşmesi, tanınmayan domain gibi
tanıyıcı hataları — Damga bunları tahmin etmek yerine kelime olarak bırakır).
Ayrılmış KPI setinde (300 telefon + 300 e-posta klibi, 8 görülmemiş ses, Mihu
STT v1.2 + hotword) birebir eşleşme telefon %84, e-posta %97; kaçanlar
tanıyıcının düşürdüğü rakamlar, normalizasyon hatası değil.

Uçtan uca (TTS → Mihu STT v1.2 → Damga), 8 görülmemiş sesle
1 200 sentetik cümlede: para %100, yüzde %100, tarih %100, saat %100, marka
%97, e-posta %92, telefon %83, adres %63, harf harf kodlama %52 — toplam
%79,0 birebir (eski regex normalizer: %52; para, adres ve kodlamada %0).
Ayrı 100 kliplik plaka seti: %74. Hataların %86'sı tanıyıcı kaynaklı (düşen
rakam, yanlış duyulan harf adı); kalanı `tests/golden/itn_asr.tsv` içinde
izlenen normalizasyon açıkları.

Sıradan konuşmada güvenlik ters yönden ölçülür: düz Türkçe cümleler
sayı/sıra/tarih/para/birim dönüşümleri dışında değişmeden geçer — telefon, e-posta, plaka ve kodlama
gramerleri düz metinde hiç tetiklenmez, dokunulmayan kelimeler büyük/küçük
harfini korur ve `normalize(normalize(x)) == normalize(x)` sağlanır. Tanıyıcı
sık sık *yazılı* sayı üretir ("99 lira", "saat 13.30", "40 bir" = 41); bağlam
gramerleri bu karışık biçimleri kabul eder, çıplak sayılara dokunulmaz ki
kimlik numaraları asla yeniden gruplanmasın.

## Test ve ölçüm

```bash
pytest
python benchmarks/latency.py    # yüklü çalışma zamanında hızlı cümle başı gecikme (pynini gerekmez)
python benchmarks/bench.py --out benchmarks/results/makinem.md   # tam rapor, pynini gerekir
```

Altın test setleri `tests/golden/*.tsv` dosyalarındadır (`girdi<TAB>beklenen`);
yeni vaka eklemek tek satırdır. Ölçülen değerler `benchmarks/results/` altında:
2026 MacBook, Rosetta altında x86_64 conda Python, tek iş parçacığı — ITN
derleme bir kez 6,4 s / önbellekten yükleme 26 ms (5,3 MB FAR), p50 gecikme
1,1 ms (kısa cümle), 4,9 ms (telefon + e-posta içeren iki cümle), 86 ms (200
kelime); TN p50 2,2 ms; akış güncellemesi p50 1,2 ms; soğuk derleme sonrası
≈490 MB RSS (önbellekten yüklenince daha az). Yerel arm64 veya Linux
derlemeleri daha hızlıdır.

## Diller

Varsayılan dil Türkçedir (`tr`). Gramerler
`damga/<dil>/{itn,tn}/` altında; motor, önbellek, akış sarmalayıcısı ve API
dilden bağımsızdır. Yeni dil = yeni klasör + `damga/api.py` içinde tek satır
kayıt; sonra `Normalizer(mode="itn", lang="en")`, `InverseNormalizer(lang="en")`
ve `available_languages()` çalışır — bkz.
[docs/adding-a-language.md](docs/adding-a-language.md).

Bu sürümde Türkçe (`tr`), İngilizce (`en`), Almanca (`de`), Fransızca (`fr`),
İspanyolca (`es`), İtalyanca (`it`) ve Rusça (`ru`) yer alır; her biri için TN
ve ITN:

```python
from damga import TextNormalizer, InverseNormalizer
TextNormalizer(lang="en").normalize("EUR 10 million on 6 December 2012")
# ten million euros on the sixth of December two thousand twelve
InverseNormalizer(lang="de").normalize("fünfundzwanzig Prozent")   # 25 Prozent
```

Okunuşlar konuşanların gerçekte söylediğine göre seçildi. Türkçe dışındaki
dillerin test satırlarını henüz anadili konuşanlar gözden geçirmedi.

## Katkı

Gramerler `damga/tr/itn/readers`, `damga/tr/itn/writers`,
`damga/tr/tn/...` altında düz Python dosyaları; veri tabloları `.../data/`
altında TSV. Başarısız altın satırlar en iyi hata raporudur. Bkz.
[CONTRIBUTING.md](CONTRIBUTING.md) ve [docs/architecture.md](docs/architecture.md).

## Lisans

Apache License 2.0 — bkz. [LICENSE](LICENSE). Pynini ve OpenFst de Apache 2.0'dır.

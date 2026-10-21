# Tek okunuş ya da tüm okunuşlar (varyantlar)

*English: [variants.md](variants.md)*

Damga'da iki TN modu vardır.

- **Deterministik (varsayılan):** bir girdi, tek çıktı. `09:30` her zaman
  *dokuz otuz*dur. ITN'in tek modu da budur.
- **Varyantlar, `variants=True` (deterministik olmayan):** bir girdi, birden çok
  geçerli çıktı. `09:30` *dokuz otuz* da olur *dokuz buçuk* da; hangisinin uygun
  olduğuna girdi tek başına değil, duyulan ses (`normalize_matching`) ya da bir
  dil modeli (`normalize_in_context`) karar verir. Okunuş listesi
  tekrarlanabilir (her seferinde aynı okunuşlar, aynı sırada) ve `normalize()`
  yine tek varsayılan okunuşu döndürür.

| | Tek okunuş (varsayılan) | Varyantlar |
| --- | --- | --- |
| Deterministik | **evet**: bir girdi, tek çıktı | **hayır**: bir girdi, birden çok çıktı (listenin kendisi tekrarlanabilir) |
| Nasıl açılır | `TextNormalizer()` | `TextNormalizer(variants=True)` |
| Bir yazılı biçime kaç okunuş | bir | varsayılan + yaygın diğer okunuşlar |
| `normalize()` | o tek okunuş | aynı tek okunuş, değişmez |
| `normalize_variants()` | `[normalize(text)]` | tüm okunuşlar, varsayılan önce |
| `normalize_matching(text, heard)` | varsayılan | `heard`'e en yakın okunuş |
| `normalize_in_context(text, score)` | varsayılan | bir dil modelinin en yüksek puan verdiği okunuş |
| Ne için | sesli asistan, IVR, metin okuma, canlı her şey | TTS ve ASR eğitim verisi, adil ASR değerlendirmesi |
| ITN | her zaman | yok |

## Tek okunuş (varsayılan)

Aynı girdi her zaman aynı çıktıyı verir. `2,5` her zaman *iki virgül beş*,
`09:30` her zaman *dokuz otuz*, `250 TL` her zaman *iki yüz elli Türk lirası*.
Her okunuş `tests/golden/tn.tsv` içinde bir satırdır.

Sesin ihtiyacı budur: müşteri tutarları, saatleri ve telefon numaralarını her
görüşmede aynı şekilde duyar; bugün geçen test yarın da geçer.

**Sesli yapay zekâ için (sesli asistan, IVR, canlı görüşme) varsayılan modu
kullanın.** Eşleştirilecek bir kayıt yoktur: konuşan asistanın kendisidir, TN
hangi okunuşu verirse müşteri onu duyar. Önemli olan, okunuşun her seferinde
aynı olması ve hızlı gelmesidir. Okunuşu bir dil modeliyle seçmek, TTS
başlamadan önce her cümleye gecikme ekler:

| | Cümle başına süre | Her görüşmede aynı çıktı |
| --- | ---: | --- |
| Varsayılan TN (`normalize()`) | ~1 ms | evet |
| Okunuşu Türkçe GPT-2 seçer (`normalize_in_context`) | ~0,3 sn | evet, aynı model sürümüyle |
| Okunuşu küçük bir yerel LLM seçer (Gemma sınıfı, 2B) | ~1,5–2 sn | garanti değil |

Tek bir CPU'da ölçüldü (Apple M2, 4 iş parçacığı, native motor, kısa çağrı
merkezi cümleleri). Görüşmelerde farklı bir okunuş istiyorsanız (*Türk lirası*
yerine *lira*), varsayılan okunuşu değiştirin: o zaman her görüşmede ek
maliyet olmadan uygulanır. Varyantlar, eğitim verisini
çevrimdışı hazırlamak içindir.

```python
from damga import TextNormalizer

tn = TextNormalizer()
tn.normalize("Saat 09:30'da, 2,5 kg, 250 TL.")
# 'Saat dokuz otuzda, iki virgül beş kilogram, iki yüz elli Türk lirası.'
```

## Varyantlar

İnsanlar yazılı biçimleri tek bir şekilde okumaz. TTS veri seti kaydeden bir
seslendirmen `09:30` için *dokuz buçuk* der; bir ASR test setinde metin
`2,50 TL` iken kayıtta *iki buçuk lira* geçer. Eğitim ya da referans metni
varsayılan okunuşta kalırsa metin ile ses uyuşmaz: TTS modeli yanlış
kelimeleri öğrenir, ASR modeli doğruyu duyduğu halde hatalı sayılır.

`variants=True` ile TN okunuşları listeler ve sesle eşleşeni seçer:

```python
tn = TextNormalizer(variants=True)

tn.normalize_variants("Saat 21:45")
# ['Saat yirmi bir kırk beş', 'Saat dokuz kırk beş', 'Saat ona çeyrek var']

tn.normalize_matching("Saat 21:45", heard="saat ona çeyrek var")
# 'Saat ona çeyrek var'
```

`heard` kaydın dökümüdür, genelde bir tanıyıcıdan gelir. Seçim rastgele
değildir, her seferinde aynı sonucu verir:

1. **Kelimeler.** Her okunuş dökümle kelime kelime karşılaştırılır: kaç
   kelimenin eklenmesi, silinmesi ya da değiştirilmesi gerektiği sayılır;
   büyük/küçük harf ve noktalama yok sayılır. Tanıyıcının yazdığı rakamlar
   (`3`, `16-45`, `730'da`) herhangi bir sayı kelimesi dizisini karşılar, yani
   yalnızca diğer kelimeler sayılır: `Toplam 3 bin lira` için `üç bin Türk
   lirası` 2 kelime uzakta, `üç bin lira` 0. *buçuk* / *otuz*, *çeyrek geçe*,
   *lira* / *Türk lirası*, *yarım* bununla ayrılır.
2. **Değer.** Okunuşun yazılı biçiminin (Damga ITN'i) rakamları dökümün
   rakamlarıyla karşılaştırılır. `16-45` *on altı kırk beş*'i destekler, *dört
   kırk beş*'i değil; `730'da` *yedi otuzda*'yı destekler, *on dokuz
   otuzda*'yı değil. Tanıyıcının yazdığı baştaki `0` *sıfır* kelimesi sayılır,
   böylece `532 944 …` sıfırsız okunan telefonu destekler.
3. İki mesafe toplanır, en küçük toplam kazanır. Eşitlikte önceki okunuş kalır;
   döküm okunuşları ayırt ettirmiyorsa varsayılan seçilir.

Tanıyıcı yalnızca okunuşlar arasında karar verir; kelimeler her zaman yazılı
metinden gelir. Kayıtlarda ([`examples/tn_variants_asr.py`](../examples/tn_variants_asr.py),
CPU'da Mihu Türkçe STT):

| Yazılı | Tanıyıcının duyduğu | Seçilen |
| --- | --- | --- |
| Toplam 3.000 TL tutuyor. | Toplam 3 bin lira tutuyor | Toplam üç bin lira tutuyor. |
| … %20 indirimle 4.200 TL ödeyeceksiniz. | … yüzde yirmi indirimle 420 lira ödeyeceksiniz | … dört bin iki yüz lira ödeyeceksiniz. |
| … saat 09:30'a aldım. | … saat 930'a aldım | … saat dokuz otuza aldım. (varsayılan) |

İkinci satırda tanıyıcı tutarı yanlış duydu ama tutar yine doğru: tutar
metinden gelir, tanıyıcı yalnızca *lira* ile *Türk lirası* arasında seçim
yaptırdı.

### 1000 kayıtta ölçüm

1000 cümle, her biri okunuşlarından rastgele seçilen biriyle (yani yaklaşık
yarısı varsayılan dışında) bir TTS sesiyle seslendirildi ve CPU'da Mihu Türkçe
STT ile yazıya döküldü (%39 kelime hata oranı, sayıların çoğu rakamla). Daha
önce bakılmamış sette `normalize_matching` seslendirilen okunuşu **%92,2**
oranında buldu, yalnız varsayılan okunuş %49,6'da kaldı: saat %97,1, tutar %96,8,
ondalık %98,3, telefon %78,2. Kaçanların çoğu rakam rakam okunup tanıyıcının
düz rakam olarak yazdığı telefon numaraları; bu yazımda gruplamanın izi kalmaz.
Yöntem, tüm sayılar ve kaçanlar:
[benchmarks/results/tn-variants-20261012.md](../benchmarks/results/tn-variants-20261012.md);
herhangi bir TTS ve tanıyıcıyla `benchmarks/tn_variants.py` ile tekrarlanabilir.

### Döküm hiçbir okunuşa uymuyorsa

`normalize_matching` her zaman en yakın okunuşu döndürür; döküm başka bir
cümleye ait olsa ya da tanıyıcı çoğunu yanlış duymuş olsa bile.
`rank_matching` her okunuşun ne kadar yakın olduğunu gösterir, `max_distance`
ise en iyisi bile çok uzaksa varsayılana döner:

```python
tn.rank_matching("Saat 09:30'da geldi.", "saat dokuz buçukta geldi")
# [('Saat dokuz buçukta geldi.', 0.0), ('Saat dokuz otuzda geldi.', 0.25)]

tn.normalize_matching("Toplam 3.000 TL tutuyor.", "bambaşka bir cümle bu", max_distance=0.5)
# 'Toplam üç bin Türk lirası tutuyor.'   (en iyi mesafe 2,25: varsayılan)
```

Mesafe, duyulan kelime başına yaklaşık fark sayısıdır; 0 birebir eşleşme
demektir. Onu varsayılana dönmek için değil, kayıtları sıralamak ya da elemek
için kullanın: aşağıdaki 1000 kayıtta mesafe 0,3'ün üstünde olsa bile en yakın
okunuş %80 oranında doğru, yani yalnızca varsayılandan iyi. `max_distance`
başka bir cümleye ait olabilecek dökümler (yanlış eşleşmiş dosya) içindir,
sıradan tanıyıcı hataları için değil. Yalnızca mesafesi 0,3'e kadar olanları
tutmak kayıtların %72'sini, okunuşlarının %94,8'i doğru olarak bıraktı
(tümünde %91).

### Kayıt yoksa: bağlama göre seçim

Kayıt yoksa bir dil modeli cümlede en doğal duran okunuşu seçebilir: tarifte
*iki buçuk su bardağı*. `normalize_in_context`
herhangi bir puanlayıcı alır (okunuşları alıp her birine bir sayı döndüren,
yüksek olanın daha iyi olduğu bir fonksiyon) ve başka bir okunuş `margin`'den
fazla yüksek puan almadıkça varsayılanı korur:

```python
tn.normalize_in_context("Tarifte 2,5 su bardağı un var.", score)
# 'Tarifte iki buçuk su bardağı un var.'
```

Damga içinde model yoktur ve hiçbir modele bağımlı değildir.
[`examples/tn_variants_lm.py`](../examples/tn_variants_lm.py) Türkçe bir BERT
(ya da herhangi bir soldan sağa model) ile CPU'da puanlar. Çevrimdışı metin
hazırlamak içindir; canlı bir sesli asistan için fazla yavaştır, orada doğru
seçim varsayılan moddur.

Konuşma diline yakın metinle eğitilmiş soldan sağa bir model, yazı diliyle
eğitilmiş bir modelden daha iyi sonuç verir; ikincisi yazı dilindeki okunuşları
tercih etme eğilimindedir. Kayıt varsa daha iyi hakem odur:
`normalize_matching` gerçekten söyleneni seçer.

### Hangi biçimlerin alternatifi var

| Yazılı | Varsayılan | Alternatifler |
| --- | --- | --- |
| `09:30` | dokuz otuz | dokuz buçuk |
| `09:30'da` | dokuz otuzda | dokuz buçukta |
| `21:45` | yirmi bir kırk beş | dokuz kırk beş · ona çeyrek var |
| `09:10` | dokuz on | dokuzu on geçe |
| `13:15` | on üç on beş | bir on beş · biri çeyrek geçe |
| `2,5 kg` | iki virgül beş kilogram | iki buçuk kilogram · iki nokta beş kilogram |
| `0,5 lt` | sıfır virgül beş litre | yarım litre · sıfır nokta beş litre |
| `%2,5'e` | yüzde iki virgül beşe | yüzde iki buçuğa · yüzde iki nokta beşe |
| `93,85` | doksan üç virgül seksen beş | doksan üç nokta seksen beş · doksan üç seksen beş |
| `1.6 milyon` | bir nokta altı milyon | bir virgül altı milyon · bir altı milyon |
| `6.97` | altı doksan yedi | altı nokta doksan yedi · altı virgül doksan yedi |
| `17.30'da` | on yedi otuzda | … nokta otuzda · … virgül otuzda · beş otuzda · on yedi buçukta · beş buçukta |
| `250 TL` | iki yüz elli Türk lirası | iki yüz elli lira |
| `2,50 TL` | iki lira elli kuruş | iki Türk lirası elli kuruş · iki buçuk lira |
| `0532 123 45 67` | sıfır beş yüz otuz iki yüz yirmi üç kırk beş altmış yedi | beş yüz otuz iki … (baştaki 0 olmadan) · sıfır beş üç iki bir iki üç dört beş altı yedi |
| `30.04.2024` | otuz nisan iki bin yirmi dört | otuz sıfır dört … · otuz dört … |
| `toplamı 3. Güzel` | toplamı üç. Güzel | toplamı üçüncü Güzel |

Geri kalan her şeyin (ay adıyla yazılmış tarih, küçük harften önceki sıra
sayısı, düz sayı, IBAN, plaka, e-posta) iki modda da tek okunuşu vardır.

Birden fazla belirsiz biçim içeren bir cümlede kombinasyonlar gelir: önce
varsayılan, sonra soldan sağa her seferinde bir biçim değişmiş haller, sonra
iki biçim, … en çok `n` tane (`normalize_variants(text, n=10)`;
`normalize_matching` 50'ye bakar).

```python
tn.normalize_variants("Saat 09:30, tutar 250 TL.")
# ['Saat dokuz otuz, tutar iki yüz elli Türk lirası.',
#  'Saat dokuz buçuk, tutar iki yüz elli Türk lirası.',
#  'Saat dokuz otuz, tutar iki yüz elli lira.',
#  'Saat dokuz buçuk, tutar iki yüz elli lira.']
```

### Nasıl çalışır

Okuyucu varsayılan moddakiyle birebir aynı çalışır, yani her biçim
aynı şekilde tanınır. Sonra her token varsayılan gramerle tek başına
okunur (ilk okunuş budur) ve yukarıdaki biçimler alternatiflerini
`damga/tr/tn/variants.py` içinden ekler. Hal eki okunuşla birlikte taşınır
(`09:30'da` → *dokuz buçukta*, `%2,5'e` → *yüzde iki buçuğa*); eki
taşıyamayan bir saat deyimi (*dokuzu on geçe* + *de*) önerilmez.

Testler `tests/golden/tn.tsv` içindeki her satır için ilk okunuşun
`normalize()` ile aynı olduğunu ve native ile pynini motorlarının aynı
okunuşları verdiğini kontrol eder.

### Diğer diller

İngilizce, Almanca, Fransızca, İspanyolca, İtalyanca ve Rusça aynı API'ye
sahiptir (`TextNormalizer(lang="en", variants=True)` vb.). Okunuşları,
varsayılan gramerin yanında derlenen ikinci bir gramerden gelir
(`compiled/variants.fst`): varsayılan okunuşu ve onun arkasında ağırlıklı
olarak konuşanların aynı biçimi okuduğu diğer yolları içerir. Cümlenin
okunuşları bu gramerin en iyi n yoludur; İtalyanca ve Almanca'nın bir kısmı
gramerleri küçük kalsın diye varsayılan okunuşu Python'da kelime kelime
değiştirir. Her alternatif, konuşanların o biçimi gerçekte söyleme
yollarından biridir, örneğin:

| Dil | Yazılı | Varsayılan | Diğer okunuşlar |
| --- | --- | --- | --- |
| en | `in 2013` | *two thousand thirteen* | *twenty thirteen*, *two thousand and thirteen* |
| en | `1.5%` | *one point five percent* | *one and a half percent* |
| de | `2012` | *zweitausendzwölf* | *zwanzig zwölf* |
| fr | `2,5 millions` | *deux virgule cinq millions* | *deux millions et demi* |
| es | `2,5 millones` | *dos coma cinco millones* | *dos millones y medio* |
| it | `2016` | *duemilasedici* | *duemila e sedici* |
| ru | `составляет 1000` | *составляет тысячу* | *составляет одну тысячу*, *составляет тысяча* |

## ITN'de neden varyant yok

ITN tanıyıcının duyduğunu insanların ve sistemlerin kullandığı tek yazılı
biçime çevirir. `sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi`
ifadesinin tek doğru biçimi vardır: `0532 123 45 67`. İkinci bir seçenek
sunmak tahmin etmek demektir; yanlış bir telefon numarası ya da tutar, kelime
olarak bırakılmış kelimelerden kötüdür. `InverseNormalizer(variants=True)`
`ValueError` verir.

## Alternatif eklemek

Türkçe: `damga/tr/tn/variants.py` içine ilgili token sınıfı için bir dal
ekleyin (ayrıştırılmış token'ı, varsayılan okunuşunu ve sayıyı okuyan bir
fonksiyonu alır) ve `tests/unit/test_variants.py` içine bir örnek ekleyin.
Diğer diller: okunuşu dilin varsayılanın arkasında kalacak bir ağırlıkla
varyant gramerine ekleyin (kelime değişimi için dilin
`tn/readers/sentence.py` dosyasındaki `rewrites()`, sıra değişimi
için ilgili okuyucu) ve `tests/golden/test_golden_<dil>.py` içine bir örnek
ekleyin. Yalnızca konuşmacının söylediği kelimeleri değiştiren okunuşları
listeleyin, üslup farklarını değil; ve yalnızca konuşanların gerçekten
kullandığı okunuşları.

## Eski ad (1.0)

1.0'da bu seçeneğin adı `deterministic` idi: `deterministic=False`, `variants=True` demektir.
Eski ad hâlâ çalışır ve `DeprecationWarning` verir; 2.0'da kaldırılacak.

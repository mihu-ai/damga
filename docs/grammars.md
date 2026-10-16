# Grammar reference and known limitations

Weights (lower wins) and typical examples per class.  Golden files in
`tests/golden/` are the executable specification.

| class | ITN example | TN example | notes / limitations |
|---|---|---|---|
| cardinal | `yirmi beş bin altı yüz` → `25.600` | `25.600` → `yirmi beş bin altı yüz` | up to trillions; a lone `bir` is **not** converted as a cardinal (`bir şey` stays), but inside a context class it is the number (`bir kilo` → `1 kg`, `bir lira` → `1 TL`, `bir ocak` → `1 Ocak`); `bir milyon` and bare `milyon` both accepted; 4-digit numbers get a dot (`2.026`) unless read as a date; a case suffix glued to the last number word is kept after an apostrophe (`yirmi altıda` → `26'da`, `otuz dördü` → `34'ü`, `yüzde on beşe` → `%15'e`); a *single* `bir`/`on`/`yüz`/`bin`/`sıfır` with a suffix is never converted (`ona`, `birden`, `yüzden`, `sıfırdan` are ordinary words) |
| ordinal | `yirmi beşinci` → `25.` | `3. kat` → `üçüncü kat`, `3'üncüsü` → `üçüncüsü` | ITN: bare ordinals only (`üçüncüsü`, `beşinciye` stay words); TN: `N.` is an ordinal only when a lower-case word follows |
| negative | `eksi on iki` → `-12` | `-12` → `eksi on iki` | |
| decimal | `üç virgül on dört` → `3,14`, `iki buçuk` → `2,5`, `bir nokta dokuz` → `1,9`, `üç nokta iki nokta bir` → `3.2.1` | `0,05` → `sıfır virgül sıfır beş`, `1.50 m` → `bir elli metre`, `192.168.1.1` → `yüz doksan iki nokta …` | three or more numbers joined by `nokta` are an IP address or a version and keep their points |
| money | `iki lira elli kuruş` → `2,50 TL`, `yüz dolar` → `100 $` | `₺150` → `yüz elli Türk lirası`, `2,50 TL` → `iki lira elli kuruş` | symbols after the amount in ITN output (`100 $`, `20 €`); table: `tr/itn/data/currency.tsv` |
| percent | `yüzde on iki virgül beş` → `%12,5` | `25%` → `yüzde yirmi beş` | `binde` → `‰` |
| measure | `yirmi beş kilometre` → `25 km` | `30°` → `otuz derece`, `120 km/s` → `yüz yirmi kilometre saat` | table: `tr/itn/data/units.tsv` (TN: `tr/tn/data/units.tsv`); a few inflected units (`kilometreye` → `km'ye`) |
| time | `saat dokuz otuzda` → `saat 09:30'da`, `dokuza çeyrek kala` → `08:45` | `09:05` → `dokuz sıfır beş`, `saat 14.45` → `saat on dört kırk beş` | plain `hour minute` needs the keyword `saat`; `saat dokuz` alone stays `saat 9`, `saat ikide` → `saat 2'de`; after `on`/`yirmi` a single digit continues the hour (`saat on beş` → `saat 15`, `saat on beş kırk` → `saat 15:40`, `saat dokuz beş` → `saat 09:05`) |
| date | `on beş ekimde` → `15 Ekim'de`, `iki bin yirmi altı yılında` → `2026 yılında` | `15/10/2026` → `on beş Ekim iki bin yirmi altı`, `14 Haziran'da` → `on dört Haziran'da`, `2026'da` → `iki bin yirmi altıda` | a bare year is recognised only with a year word or a case suffix (`iki bin yirmi altıda` → `2026'da`, `bin dokuz yüz seksen beşte` → `1985'te`); numeric spoken dates (`on beş on iki bin dokuz yüz doksan`) are not supported |
| telephone | `sıfır beş üç iki bir iki üç dört beş altı yedi` → `0532 123 45 67`, `artı doksan …` → `+90 532 …` | `0 (532) 123 45 67` → `sıfır beş yüz otuz iki …` | exactly 11 digits starting with 0 (or 10 after +90, or 10 starting with 5); the `0…`/`+90…` forms tolerate written digits, commas and fillers inside the number, the unanchored `5…` form either clean space-separated spoken digits in any grouping or the Turkish mobile layout 3-3-2-2 (`beş yüz kırk üç, beş yüz elli, altmış altı, yetmiş yedi` → `0543 550 66 77`, commas at the speaker's pauses allowed, at most one round group such as `beş yüz elli`), so a comma-separated list of ordinary numbers (`beş yüz, üç yüz, kırk, elli`) is never glued into a phone number; extensions (`dahili`) stay words |
| iban | `te re doksan altı …` (24 digits) → `TR96 0006 2000 …` | `TR96 0006 …` → `te re dokuz altı, sıfır sıfır sıfır altı, …` | ITN: digit groups up to 4 (`iki bin` = 2000); exactly 24 digits. TN: digit by digit, a pause (comma) between the written groups |
| plate | `otuz dört a b c sekiz yüz kırk iki` → `34 ABC 842`, `plakam altı fe he …` → `plakam 06 FH …` | `34 ABC 842` → `otuz dört a be ce sekiz yüz kırk iki` | without a `plaka…` keyword two or more unambiguous letters are required |
| email/web | `derya nokta öztürk et gmail nokta com` → `derya.ozturk@gmail.com`, `www nokta örnek tur nokta com` | inverse | `nokta`/`alt çizgi`/`tire`/`artı`/`et` separators; Turkish letters folded to ASCII; local part: at most two bare words glued |
| address | `atatürk caddesi numara on iki daire yedi` → `atatürk caddesi No: 12 Daire: 7`, `no beş kat üç daire on` → `No: 5 Kat: 3 Daire: 10` | — | keywords `no`/`numara`, `kat`, `daire`; street names are left as words (ITN only) |
| spelling | `diyarbakır'ın de'si edirne'nin e'si rize'nin re'si yozgat'ın ye'si adana'nın a'sı` → `Derya`, `bursa'nın besi uşak usu rize nin resi aydın ası karsın kesin` → `Burak` | — | the Turkish "X'in Y'si" letter-coding habit. **The mnemonic's first letter decides**; the letter token after it is only consumed and may be mangled by the recognizer (`desi`, `ağası`, `üyesi`, `nisi`, `NS'i`, `H S`, `es`, glued `niğde'ninesi`) or a bare letter name (`konya'nın ke`). Without a mnemonic the letter name decides (`a sı`, `yumuşak ge'si`). At least two units; a bare province name is accepted only after a real unit. ITN only |
| lexicon_entry | `ka de ve` → `KDV`, `mercedes'iniz` → `Mercedes'iniz` | `Dr.` → `doktor` | `tr/itn/data/lexicon_entries.tsv` + `brands.tsv` + `brands_extra.tsv`, `tr/tn/data/lexicon_entries.tsv`, plus `custom_vocab`; inflected brands keep their suffix; short ALL-CAPS recognizer tokens (`ETS`, `AWS`) are matched case-insensitively |

## Deliberately unsupported (yet)

* Roman numerals; in ITN fractions (`üçte bir` is read as a suffixed number, `3'te bir`) and ranges (`on–on beş`).
  TN reads them: `3/4` → `dörtte üç` (proper fractions up to /100; `7/24` → `yedi yirmi dört`), `3-5` → `üç beş`,
  and a range of numbers with three or more digits takes *ile* (`1914-1918` → `bin dokuz yüz on dört ile …`).
* Spoken punctuation ("nokta" as a full stop, "virgül" as a comma).
* Inflected ordinals in ITN, inflected units beyond the few listed.
* Numeric spoken dates and bare years without a year word or case suffix.
* Non-Turkish currencies beyond the table, cryptocurrency.

Contributions welcome — each item is a reader/writer pair plus golden lines.

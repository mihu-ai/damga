from damga import InverseNormalizer, TextNormalizer

itn = InverseNormalizer()
for s in [
    "yüz elli lira",
    "telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi",
    "e-posta adresim derya nokta öztürk et gmail nokta com",
    "randevunuz on beş ekim iki bin yirmi altı saat on dört otuzda",
    "indirim yüzde on iki virgül beş, toplam iki bin beş yüz lira kırk kuruş",
    "plakam otuz dört a b c sekiz yüz kırk iki",
]:
    print(f"{s}\n  → {itn.normalize(s)}")

tn = TextNormalizer()
for s in ["Toplam 25.600 adet, %12,5 indirim, 2,50 TL.", "15.10.2026 saat 09:30, 0532 123 45 67", "3. kat, 2026'da"]:
    print(f"{s}\n  → {tn.normalize(s)}")

from damga.streaming import StreamingNormalizer

hyps = ["telefon", "telefon numaram", "telefon numaram sıfır beş", "telefon numaram sıfır beş otuz iki",
        "telefon numaram sıfır beş otuz iki yüz yirmi üç", "telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş",
        "telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi"]
sn = StreamingNormalizer(mode="itn", stable_after=2)
for i, h in enumerate(hyps):
    r = sn.update(h, is_final=(i == len(hyps) - 1))
    flag = "FINAL" if r.is_final else "partial"
    print(f"[{flag:7}] committed={r.committed!r:32} provisional={r.provisional!r:28} → {r.text}")

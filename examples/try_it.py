"""Try Damga by hand: type a sentence, see what TN and ITN make of it.

    python examples/try_it.py              # Turkish
    python examples/try_it.py --lang en    # tr, en, de, fr, es, it, ru

A line with digits is read out (TN): the default reading and the other readings speakers use.  A line in words is
written down (ITN).  A line ``written | heard`` picks the reading of ``written`` closest to ``heard``, the way TTS
training text is matched to a recording.  An empty line quits.
"""
from __future__ import annotations

import argparse
import re
import time

from damga import InverseNormalizer, TextNormalizer, available_languages


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", default="tr", choices=available_languages())
    lang = ap.parse_args().lang
    tn = TextNormalizer(lang=lang)
    variants = TextNormalizer(lang=lang, variants=True)
    itn = InverseNormalizer(lang=lang)
    print(f"Damga ({lang}). Type a sentence; empty line quits.")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        t0 = time.perf_counter()
        if "|" in line:
            written, heard = (part.strip() for part in line.split("|", 1))
            print("  closest to what was heard:", variants.normalize_matching(written, heard))
        elif re.search(r"\d", line):
            print("  TN :", tn.normalize(line))
            for other in variants.normalize_variants(line, n=6)[1:]:
                print("   or:", other)
        else:
            print("  ITN:", itn.normalize(line))
        print(f"  ({(time.perf_counter() - t0) * 1000:.1f} ms)")


if __name__ == "__main__":
    main()

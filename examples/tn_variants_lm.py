"""Pick the TN reading a Turkish language model finds most natural, when there is no recording to listen to.

    pip install damga torch transformers
    python examples/tn_variants_lm.py "Tarifte 2,5 su bardağı un var." "Toplantı saat 15:30'da."
    python examples/tn_variants_lm.py --file sentences.txt --out spoken.tsv
    python examples/tn_variants_lm.py --kind mlm --model dbmdz/bert-base-turkish-cased "Saat 09:30'da geldi."

A written sentence has one default reading ("2,5 su bardağı" → "iki virgül beş su bardağı"), but a
speaker would say "iki buçuk su bardağı".  TextNormalizer(variants=True) lists the readings and
normalize_in_context() keeps the one the model scores highest; the default stays unless another reading wins by
more than --margin.  Use it to prepare TTS text offline (it is too slow for a live voice agent, where the
deterministic default is the right choice).  When you have the recording, examples/tn_variants_asr.py chooses by
what was actually said, which is more reliable.

Scoring: --kind causal (default, a Turkish GPT-2) adds up the log-probabilities of the sentence left to right;
--kind mlm masks each token in turn (pseudo-log-likelihood).  Both run on the CPU.
A left-to-right model trained on text close to speech works better than one trained on written text, which tends
to prefer written-style readings.
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoModelForMaskedLM, AutoTokenizer
except ImportError as e:
    sys.exit(f"{e}\ninstall: pip install torch transformers")

from damga import TextNormalizer


class LMScorer:
    """Callable for ``TextNormalizer.normalize_in_context``: one log-likelihood per sentence, higher is better."""

    def __init__(self, model: str, kind: str = "causal", device: str = "cpu"):
        self.kind, self.device = kind, device
        self.tok = AutoTokenizer.from_pretrained(model)
        cls = AutoModelForMaskedLM if kind == "mlm" else AutoModelForCausalLM
        self.model = cls.from_pretrained(model).to(device).eval()

    @torch.no_grad()
    def __call__(self, sentences: Sequence[str]) -> list[float]:
        return [self._mlm(s) if self.kind == "mlm" else self._causal(s) for s in sentences]

    def _mlm(self, sentence: str) -> float:
        ids = self.tok(sentence, return_tensors="pt")["input_ids"][0].to(self.device)
        positions = list(range(1, len(ids) - 1))           # skip [CLS] and [SEP]
        batch = ids.repeat(len(positions), 1)
        for row, pos in enumerate(positions):
            batch[row, pos] = self.tok.mask_token_id
        logits = self.model(batch).logits
        logp = torch.log_softmax(logits[range(len(positions)), positions], dim=-1)
        return float(logp[range(len(positions)), ids[positions]].sum())

    def _causal(self, sentence: str) -> float:
        bos = self.tok.bos_token or self.tok.eos_token or ""
        ids = self.tok(bos + sentence, return_tensors="pt")["input_ids"].to(self.device)
        logp = torch.log_softmax(self.model(ids).logits[0, :-1], dim=-1)
        return float(logp[range(ids.shape[1] - 1), ids[0, 1:]].sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sentences", nargs="*")
    ap.add_argument("--file", help="one written sentence per line")
    ap.add_argument("--out", help="write written<TAB>chosen reading to this TSV")
    ap.add_argument("--model", default="ytu-ce-cosmos/turkish-gpt2")
    ap.add_argument("--kind", choices=["causal", "mlm"], default="causal")
    ap.add_argument("--margin", type=float, default=20.0,
                    help="how much higher (log-likelihood) another reading must score than the default")
    args = ap.parse_args()

    texts = list(args.sentences)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            texts += [line.strip() for line in f if line.strip()]
    if not texts:
        sys.exit("give sentences or --file")

    tn = TextNormalizer(variants=True)
    score = LMScorer(args.model, args.kind)
    rows = []
    for text in texts:
        variants = tn.normalize_variants(text)
        chosen = tn.normalize_in_context(text, score, margin=args.margin)
        rows.append((text, chosen))
        print(f"{text}\n  default : {variants[0]}\n  chosen  : {chosen}"
              f"{'' if chosen == variants[0] else '   ← not the default'}\n")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.writelines(f"{t}\t{c}\n" for t, c in rows)
        print(f"→ {args.out}")


if __name__ == "__main__":
    main()

# Streaming normalization

Live recognizers emit partial hypotheses that can change until the utterance
ends; `StreamingNormalizer` makes ITN safe in that setting.

## Contract

```python
sn = StreamingNormalizer(mode="itn", stable_after=2, max_pending_words=200)
res = sn.update(latest_full_hypothesis, is_final=False)
res.text         # committed + provisional – best current rendering
res.committed    # will not change any more
res.provisional  # may still change
res.revisions    # how often the provisional tail changed since the last commit
sn.flush()       # finalize without a final event
sn.reset()       # drop everything
```

* `update()` takes the **whole** current hypothesis, never a delta; sending the
  same words twice does not duplicate them.
* `is_final=True` normalizes the full utterance, returns it as `committed`,
  and resets the state for the next utterance.

## Commit policy

1. Take the longest word prefix shared by the last `stable_after` hypotheses.
2. Keep the last 3 words uncommitted (lag): a span is often recognisable only
   from what follows it (`pınar | nokta yılmaz et …`).
3. Move the cut point left while the preceding word could still be part of a
   semantic span (number words, `virgül`, `nokta`, `et`, `lira`, `saat`,
   month names, spelled letters, `X'in` possessives …) **or** the next word
   attaches to the previous one (`nokta`, `et`, `lira`, `buçuk`, `yılında` …).
   The word lists live in `damga/<lang>/lexicon.py` (`STREAMING_CONTINUATION`,
   `STREAMING_ATTACH_NEXT`) and are shared with the grammars, deliberately
   simple and conservative.
4. Normalize the newly stable chunk once and append it to `committed`.
5. Normalize the remaining tail on every update → `provisional`.
6. On `is_final=True` the **whole utterance is normalized again** and that
   result is returned.  Committed text is a display convenience; the final
   output is therefore always identical to batch `normalize()` on the same
   words (verified on 1 200 simulated utterances: 1 200/1 200 identical).

If the tail grows beyond `max_pending_words` the oldest words are committed at
the nearest safe boundary, so per-update cost stays bounded on very long
utterances.

If the recognizer revises words that were already committed (rare, but
possible with aggressive beam re-scoring), the normalizer notices that the
committed prefix no longer matches, notes it in `res.notes`, and re-normalizes
from scratch — it never silently keeps stale text.

## Cost

Each update normalizes only the uncommitted tail: typically < 1 ms.  The
first release recomputes the tail on every update; incremental lattice reuse
is possible later behind the same interface.

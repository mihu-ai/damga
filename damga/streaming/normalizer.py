from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..api import DEFAULT_LANG, Normalizer, language_lexicon
from ..core.unicode import TURKISH, preprocess

_SPELL_UNIT = re.compile(r"^[a-zçğıöşü]{1,3}'?(s[iıuü]|harfi)[.,?!]*$")
_POSS = re.compile(r"[a-zçğıöşü]+'?(n?[ıiuü]n)[.,?!]*$")

@dataclass
class StreamingResult:
    text: str
    committed: str
    provisional: str
    is_final: bool
    original: str
    revisions: int = 0
    notes: list[str] = field(default_factory=list)

class StreamingNormalizer:
    def __init__(self, mode: str = "itn", stable_after: int = 2, max_pending_words: int = 200, lang: str = DEFAULT_LANG,
                 **normalizer_kwargs):
        if stable_after < 1:
            raise ValueError("stable_after must be >= 1")
        self.normalizer = Normalizer(mode=mode, lang=lang, **normalizer_kwargs)
        lexicon = language_lexicon(lang)
        self._continuation: frozenset[str] = lexicon.STREAMING_CONTINUATION
        self._attach_next: frozenset[str] = lexicon.STREAMING_ATTACH_NEXT
        self._casing = getattr(lexicon, "CASING", TURKISH)
        # Words that hold a cut before or after them in Turkish (a spelled letter ``a'sı``, a genitive); a language
        # without such patterns sets ``STREAMING_TURKISH_SUFFIXES = False``.
        self._suffix_rules = getattr(lexicon, "STREAMING_TURKISH_SUFFIXES", True)
        self.stable_after = stable_after
        self.max_pending_words = max_pending_words
        self.reset()

    def reset(self) -> None:
        self._history: list[list[str]] = []
        self._committed_words: list[str] = []
        self._committed_text: str = ""
        self._revisions = 0
        self._last_provisional: str | None = None

    @property
    def committed(self) -> str:
        return self._committed_text

    @staticmethod
    def _words(text: str) -> list[str]:
        return preprocess(text, lowercase=False).split()

    def _stable_prefix_len(self, words: list[str]) -> int:
        if len(self._history) < self.stable_after:
            return 0
        n = len(words)
        for h in self._history[-self.stable_after:]:
            n = min(n, len(h))
            i = 0
            while i < n and h[i] == words[i]:
                i += 1
            n = i
        return n

    def _safe_cut(self, words: list[str], n: int, lag: int = 3) -> int:
        n = min(n, max(0, len(words) - lag))
        changed = True
        while changed and n > 0:
            changed = False
            prev = preprocess(words[n - 1], casing=self._casing)
            nxt = preprocess(words[n], casing=self._casing) if n < len(words) else ""
            suffix = self._suffix_rules and bool(_SPELL_UNIT.match(prev) or _POSS.match(prev) or _SPELL_UNIT.match(nxt))
            if prev in self._continuation or nxt in self._attach_next or suffix:
                n -= 1
                changed = True
        return n

    def _join(self, a: str, b: str) -> str:
        return (a + " " + b).strip() if a and b else (a or b)

    def update(self, hypothesis: str, is_final: bool = False) -> StreamingResult:
        words = self._words(hypothesis)
        committed_n = len(self._committed_words)
        if words[:committed_n] != self._committed_words:

            notes = ["hypothesis revised committed prefix; re-normalizing from scratch"]
            self._committed_words, self._committed_text = [], ""
            committed_n = 0
        else:
            notes = []
        pending = words[committed_n:]

        if is_final:

            text = self.normalizer.normalize(" ".join(words)) if words else ""
            res = StreamingResult(text=text, committed=text, provisional="", is_final=True, original=hypothesis,
                                  revisions=self._revisions, notes=notes)
            self.reset()
            return res

        self._history.append(words)
        if len(self._history) > self.stable_after:
            self._history = self._history[-self.stable_after:]

        stable = self._stable_prefix_len(words)
        cut = self._safe_cut(words, stable)
        if len(pending) > self.max_pending_words:
            cut = max(cut, self._safe_cut(words, committed_n + len(pending) - self.max_pending_words))
        if cut > committed_n:
            chunk = words[committed_n:cut]
            self._committed_text = self._join(self._committed_text, self.normalizer.normalize(" ".join(chunk)))
            self._committed_words = words[:cut]
            self._revisions = 0
            pending = words[cut:]

        provisional = self.normalizer.normalize(" ".join(pending)) if pending else ""
        if self._last_provisional is not None and provisional != self._last_provisional:
            self._revisions += 1
        self._last_provisional = provisional
        return StreamingResult(text=self._join(self._committed_text, provisional), committed=self._committed_text,
                               provisional=provisional, is_final=False, original=hypothesis,
                               revisions=self._revisions, notes=notes)

    def flush(self) -> StreamingResult:
        last = " ".join(self._history[-1]) if self._history else " ".join(self._committed_words)
        return self.update(last, is_final=True)

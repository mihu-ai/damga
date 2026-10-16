"""Sentence splitting for streamed text, so TN sees whole sentences.

An LLM streams ``25.600``, ``15.10.2026`` or ``2,50 TL`` as several tokens; normalizing token chunks
reads them wrong.  ``split_sentences`` yields a sentence only once it is complete:

    from damga import TextNormalizer
    from damga.streaming import split_sentences

    tn = TextNormalizer()
    for sentence in split_sentences(llm_tokens):
        speak(tn.normalize(sentence))
"""
from __future__ import annotations

import re
from typing import Iterable, Iterator

# A sentence ends at . ! ? … or a newline, but only once the next character has arrived and is whitespace:
# ``25.600`` / ``15.10.2026`` / ``2,50`` arrive token by token and must not be cut.
_END = re.compile(r"[.!?…]+[\"'”’)\]]*(?=\s)|\n")
# Words after which a period is not a sentence end: ordinals (``1. sırada``) and common abbreviations.
_NO_CUT_BEFORE = re.compile(r"(?:^|\s)(?:\d+|[A-ZÇĞİÖŞÜa-zçğıöşü]|Dr|Prof|Doç|Av|Sn|Bkz|vb|vs|No|Tel|Yrd|Op|Uzm|St|Cad|Sok|Mah|Apt)\.$")


class SentenceSplitter:
    """Incremental sentence splitter for streamed text.

    ``feed(piece)`` returns the sentences completed by ``piece``; ``flush()`` returns what is left.
    Sentences shorter than ``min_chars`` are joined with the next one (fewer, longer TTS requests).
    """

    def __init__(self, min_chars: int = 1):
        self.min_chars = min_chars
        self.buffer = ""

    def feed(self, piece: str) -> list[str]:
        self.buffer += piece
        out: list[str] = []
        start = 0
        for m in _END.finditer(self.buffer):
            end = m.end()
            sentence = self.buffer[start:end].strip()
            if m.group() != "\n" and _NO_CUT_BEFORE.search(self.buffer[:m.start() + 1]):
                continue
            if len(sentence) < self.min_chars and m.group() != "\n":
                continue
            if sentence:
                out.append(sentence)
            start = end
        self.buffer = self.buffer[start:].lstrip() if start else self.buffer
        return out

    def flush(self) -> list[str]:
        rest, self.buffer = self.buffer.strip(), ""
        return [rest] if rest else []


def split_sentences(chunks: Iterable[str], min_chars: int = 1) -> Iterator[str]:
    """Sentences from a stream of text pieces (LLM tokens, lines, …)."""
    splitter = SentenceSplitter(min_chars=min_chars)
    for piece in chunks:
        yield from splitter.feed(piece)
    yield from splitter.flush()

"""Text preparation: clean the chatbot's answer and cut it into natural phrases.

The team blueprint asks for the LLM text to be streamed "into TTS in natural
phrase chunks". This module does that in two steps:

1. ``normalize_text`` removes things that should never be read aloud:
   Markdown symbols, citation markers such as [2] or [source: interview 3],
   and raw URLs.
2. ``PhraseChunker`` receives text in any pieces (whole answers or LLM tokens)
   and releases complete phrases as soon as it is safe to do so. The first
   phrase is released as early as possible to cut first-audio latency; later
   phrases are kept to whole sentences so the voice sounds natural.
"""

from __future__ import annotations

import re

# Words that end with a full stop but do not end a sentence.
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "mt", "ave", "rd", "blvd",
    "vs", "etc", "e.g", "i.e", "approx", "inc", "ltd", "co", "no", "dept", "fig",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}

_CODE_FENCE = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|www\.)[^)]*\)")
_CITATION = re.compile(
    r"\[(?:\d+(?:\s*[,–-]\s*\d+)*|(?:source|src|ref|doc|page|p\.)[^\]]*)\]"
    r"|【[^】]*】"
    r"|\((?:source|src|ref)\s*:[^)]*\)",
    re.I,
)
_URL = re.compile(r"(?:https?://|www\.)\S*[^\s.,;:!?)\]]")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.M)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.M)
_EMPHASIS = re.compile(r"(\*\*|__|\*|~~)(?=\S)(.+?)(?<=\S)\1")
_SPACES = re.compile(r"[ \t\r\f\v]+")

SENTENCE_END = re.compile(r"[.!?…]+[\"'”’)\]*_]*(?=\s)")
CLAUSE_END = re.compile(r"[,;:—–][\"'”’)]*(?=\s)|\s[—–-]\s")


def normalize_text(text: str) -> str:
    """Return text that is safe and pleasant to read aloud."""
    if not text:
        return ""
    t = _CODE_FENCE.sub(" ", text)
    t = _INLINE_CODE.sub(r"\1", t)
    t = _MD_LINK.sub(r"\1", t)
    t = _CITATION.sub("", t)
    t = _URL.sub("a link", t)
    # A heading or bullet line without its own punctuation becomes a sentence.
    lines = []
    for line in t.split("\n"):
        stripped = _BULLET.sub("", _HEADING.sub("", line)).strip()
        if stripped and line.strip() != stripped and stripped[-1] not in ".!?:;,":
            stripped += "."
        lines.append(stripped)
    t = " ".join(x for x in lines if x)
    for _ in range(2):  # nested emphasis such as ***word***
        t = _EMPHASIS.sub(r"\2", t)
    t = t.replace("&", " and ").replace("*", "").replace("#", "")
    t = _SPACES.sub(" ", t)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    return t.strip()


def has_speakable(text: str) -> bool:
    return any(ch.isalnum() for ch in text)


def _unbalanced(s: str) -> bool:
    """True while a bracket or quote is still open, e.g. a citation split across LLM tokens."""
    return (s.count("[") > s.count("]") or s.count("(") > s.count(")")
            or s.count("【") > s.count("】") or s.count("`") % 2 == 1)


def _is_abbreviation(buf: str, dot_pos: int) -> bool:
    if buf[dot_pos] != ".":
        return False
    m = re.search(r"([A-Za-z.]+)$", buf[:dot_pos])
    if not m:
        return False
    word = m.group(1).lower().strip(".")
    if word in ABBREVIATIONS:
        return True
    return len(word) == 1 and buf[dot_pos - 1].isupper()   # an initial, e.g. "J. Smith"


class PhraseChunker:
    """Incrementally turns a stream of text into speakable phrases.

    Rules (all lengths in characters):
      * First phrase: released at the first sentence end, or at the first
        clause break (comma, semicolon, dash) once ``first_min_chars`` is reached.
      * Later phrases: released at a sentence end once ``min_chars`` is reached
        (short sentences are merged), at a clause break once ``soft_max_chars``
        is reached, and forcibly at a word boundary at ``hard_max_chars``.
      * Nothing is released while a bracket is open, so a citation that arrives
        split across tokens is removed whole by ``normalize_text``.
    """

    def __init__(self, first_min_chars: int = 30, min_chars: int = 40,
                 soft_max_chars: int = 160, hard_max_chars: int = 260):
        if not (0 < first_min_chars and 0 < min_chars <= soft_max_chars < hard_max_chars):
            raise ValueError("chunking limits must satisfy 0 < min <= soft_max < hard_max")
        self.first_min_chars = first_min_chars
        self.min_chars = min_chars
        self.soft_max_chars = soft_max_chars
        self.hard_max_chars = hard_max_chars
        self._buf = ""
        self.emitted = 0

    def feed(self, text: str) -> list[str]:
        if text:
            self._buf += text
        return self._drain(final=False)

    def flush(self) -> list[str]:
        self._buf += " "      # lets trailing punctuation count as a sentence end
        out = self._drain(final=True)
        rest = self._buf.strip()
        self._buf = ""
        if rest:
            out += self._emit(rest)
        return out

    # -- internals -------------------------------------------------------
    def _emit(self, raw: str) -> list[str]:
        phrase = normalize_text(raw)
        if phrase and has_speakable(phrase):
            self.emitted += 1
            return [phrase]
        return []

    def _drain(self, final: bool) -> list[str]:
        out: list[str] = []
        while True:
            cut = self._find_cut(final)
            if cut is None:
                return out
            raw, self._buf = self._buf[:cut], self._buf[cut:].lstrip()
            out += self._emit(raw)

    def _find_cut(self, final: bool):
        buf = self._buf
        if not buf.strip():
            return None
        first = self.emitted == 0
        min_sentence = 1 if first else self.min_chars

        # 1. Sentence end.
        for m in SENTENCE_END.finditer(buf):
            end = m.end()
            if _is_abbreviation(buf, m.start()):
                continue
            prefix = buf[:end]
            if _unbalanced(prefix):
                continue
            if len(prefix.strip()) >= min_sentence:
                return end
            if len(prefix) > self.hard_max_chars:
                break

        # 2. Clause break (comma, semicolon, dash).
        threshold = self.first_min_chars if first else self.soft_max_chars
        if len(buf) >= threshold:
            cands = [m.end() for m in CLAUSE_END.finditer(buf[: self.hard_max_chars])
                     if not _unbalanced(buf[: m.end()])]
            if first:
                cands = [c for c in cands if c >= self.first_min_chars]
                if cands:
                    return cands[0]
            else:
                cands = [c for c in cands if c >= self.min_chars]
                if cands:
                    return cands[-1]

        # 3. Hard limit: cut at the last space before hard_max_chars.
        if len(buf) >= self.hard_max_chars:
            space = buf.rfind(" ", 0, self.hard_max_chars)
            return space if space > 0 else self.hard_max_chars
        return None


def split_text(text: str, **limits) -> list[str]:
    """Convenience: chunk a complete answer in one call."""
    c = PhraseChunker(**limits)
    return c.feed(text) + c.flush()

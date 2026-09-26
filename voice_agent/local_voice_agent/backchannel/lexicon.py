"""English backchannel / barge-in lexicon shared by both interruption options.

The single-token list starts from AssemblyAI's ``BACKCHANNELS`` set in
https://github.com/AssemblyAI-Solutions/livekit-interruption-filters
(``filters/backchannel_stt.py``, MIT, Copyright (c) 2026 David Lange) and adds
multi-word acknowledgements, "keep going" continuers and an explicit barge-in list.

Continuer phrases are matched before barge-in words, so "do not stop" is a
continuer even though it contains "stop". The policy only consults this lexicon
while the agent speaks (or just stopped without asking a question), so "yes" is
treated as an acknowledgement there; an answer to a question is never filtered.
Edit for your domain.
"""

from __future__ import annotations

import enum
import string
from dataclasses import dataclass, field

BACKCHANNEL_TOKENS = frozenset({
    # AssemblyAI's set
    "mhm", "mm", "mmhm", "mmhmm",
    "uh", "uhhuh", "huh",
    "um", "umm", "uhm",
    "er", "erm",
    "hmm", "hm",
    "ah", "oh",
    "yeah", "yep", "yup",
    "okay", "ok",
    "right", "alright", "gotcha",
    # additions
    "yes", "mmm", "hmmm", "mhmm", "aha", "ahh", "ohh", "ooh", "wow",
    "sure", "cool", "nice", "great", "true", "exactly", "totally", "indeed",
})

# Normalised (lowercase, punctuation stripped) multi-word phrases.
BACKCHANNEL_PHRASES = frozenset({
    ("i", "see"),
    ("got", "it"),
    ("makes", "sense"),
    ("that", "makes", "sense"),
    ("of", "course"),
    ("fair", "enough"),
    ("sounds", "good"),
    ("thats", "right"),
    ("for", "sure"),
    ("uh", "huh"),
    ("mm", "hmm"),
})
CONTINUER_PHRASES = frozenset({
    ("i", "am", "with", "you"),
    ("im", "with", "you"),
    ("with", "you"),
    ("i", "hear", "you"),
    ("i", "am", "listening"),
    ("im", "listening"),
    ("go", "on"),
    ("go", "ahead"),
    ("keep", "going"),
    ("carry", "on"),
    ("continue",),
    ("please", "continue"),
    ("proceed",),
    ("please", "proceed"),
    ("do", "not", "stop"),
    ("dont", "stop"),
    ("please", "dont", "stop"),
    ("please", "do", "not", "stop"),
    ("no", "go", "on"),
})
_PHRASES = BACKCHANNEL_PHRASES | CONTINUER_PHRASES
_MAX_PHRASE_LEN = max(len(p) for p in _PHRASES)
# Proper prefixes ("do not", "i am", "please"): a streaming partial may still become a phrase.
_PREFIXES = frozenset(p[:k] for p in _PHRASES for k in range(1, len(p)))

# Words that signal a deliberate barge-in even in a one- or two-word utterance.
INTERRUPT_TOKENS = frozenset({
    "stop", "wait", "hold", "hang", "no", "nope", "sorry", "excuse", "pardon",
    "actually", "cancel", "question", "what", "repeat",
})

_PUNCT_STRIP = str.maketrans("", "", string.punctuation)


class Verdict(str, enum.Enum):
    EMPTY = "empty"
    BACKCHANNEL = "backchannel"
    INTERRUPT = "interrupt"
    CONTENT = "content"


@dataclass(frozen=True)
class Analysis:
    verdict: Verdict
    tokens: tuple[str, ...]
    phrases: tuple[str, ...] = ()
    """Backchannel / continuer phrases that were matched and removed."""
    interrupt_tokens: tuple[str, ...] = ()
    content_words: int = 0
    kind: str = field(default="")
    """For BACKCHANNEL: "continuer_phrase", "backchannel_phrase" or "backchannel_tokens"."""
    prefix_pending: bool = False
    """CONTENT whose only content words end the text and start a known phrase
    ("do not" -> "do not stop"); a partial transcript may still turn into it."""


def normalize(text: str) -> list[str]:
    return text.lower().translate(_PUNCT_STRIP).split()


def _strip_phrases(tokens: list[str]) -> tuple[list[str], list[tuple[str, ...]]]:
    """Remove known phrases (longest first); return the rest and what matched."""
    rest: list[str] = []
    matched: list[tuple[str, ...]] = []
    i = 0
    while i < len(tokens):
        for n in range(_MAX_PHRASE_LEN, 0, -1):
            cand = tuple(tokens[i : i + n])
            if len(cand) == n and cand in _PHRASES:
                matched.append(cand)
                i += n
                break
        else:
            rest.append(tokens[i])
            i += 1
    return rest, matched


def analyze(text: str) -> Analysis:
    tokens = normalize(text)
    if not tokens:
        return Analysis(Verdict.EMPTY, ())
    rest, matched = _strip_phrases(tokens)
    phrases = tuple(" ".join(p) for p in matched)
    content = sum(1 for tok in rest if tok not in BACKCHANNEL_TOKENS)
    interrupts = tuple(tok for tok in rest if tok in INTERRUPT_TOKENS)
    if interrupts:
        return Analysis(Verdict.INTERRUPT, tuple(tokens), phrases, interrupts, content)
    # One non-filler token anywhere flips the result, so "yeah I want the suite"
    # is never treated as a backchannel.
    if content == 0:
        if any(p in CONTINUER_PHRASES for p in matched):
            kind = "continuer_phrase"
        elif matched:
            kind = "backchannel_phrase"
        else:
            kind = "backchannel_tokens"
        return Analysis(Verdict.BACKCHANNEL, tuple(tokens), phrases, (), 0, kind)
    content_tokens = tuple(tok for tok in rest if tok not in BACKCHANNEL_TOKENS)
    pending = content_tokens in _PREFIXES and tuple(tokens[-len(content_tokens) :]) == content_tokens
    return Analysis(Verdict.CONTENT, tuple(tokens), phrases, (), content, prefix_pending=pending)


def classify(text: str) -> Verdict:
    return analyze(text).verdict


def content_words(text: str) -> int:
    """Number of tokens that are not backchannel tokens or phrases."""
    return analyze(text).content_words

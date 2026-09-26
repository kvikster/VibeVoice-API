"""English backchannel / barge-in lexicon shared by both interruption options.

The single-token list starts from AssemblyAI's ``BACKCHANNELS`` set in
https://github.com/AssemblyAI-Solutions/livekit-interruption-filters
(``filters/backchannel_stt.py``, MIT, Copyright (c) 2026 David Lange) and adds
multi-word acknowledgements plus an explicit barge-in list.

"yes" / "no" stay out of the backchannel set on purpose: a bare "yes" is often
a real answer. "no" is treated as a barge-in word instead. Edit for your domain.
"""

from __future__ import annotations

import enum
import string

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
    "mmm", "hmmm", "mhmm", "aha", "ahh", "ohh", "ooh", "wow",
    "sure", "cool", "nice", "great", "true", "exactly", "totally", "indeed",
})

# Normalised (lowercase, punctuation stripped) multi-word acknowledgements.
BACKCHANNEL_PHRASES = frozenset({
    ("i", "see"),
    ("got", "it"),
    ("makes", "sense"),
    ("of", "course"),
    ("fair", "enough"),
    ("sounds", "good"),
    ("thats", "right"),
    ("for", "sure"),
    ("uh", "huh"),
    ("mm", "hmm"),
})
_MAX_PHRASE_LEN = max(len(p) for p in BACKCHANNEL_PHRASES)

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


def normalize(text: str) -> list[str]:
    return text.lower().translate(_PUNCT_STRIP).split()


def _strip_phrases(tokens: list[str]) -> list[str]:
    """Drop every known backchannel phrase; return the remaining tokens."""
    rest: list[str] = []
    i = 0
    while i < len(tokens):
        for n in range(_MAX_PHRASE_LEN, 1, -1):
            if tuple(tokens[i : i + n]) in BACKCHANNEL_PHRASES:
                i += n
                break
        else:
            rest.append(tokens[i])
            i += 1
    return rest


def content_words(text: str) -> int:
    """Number of tokens that are not backchannel tokens or phrases."""
    return sum(1 for tok in _strip_phrases(normalize(text)) if tok not in BACKCHANNEL_TOKENS)


def classify(text: str) -> Verdict:
    tokens = normalize(text)
    if not tokens:
        return Verdict.EMPTY
    if any(tok in INTERRUPT_TOKENS for tok in tokens):
        return Verdict.INTERRUPT
    # One non-filler token anywhere flips the result, so "yeah I want the suite"
    # is never treated as a backchannel.
    if all(tok in BACKCHANNEL_TOKENS for tok in _strip_phrases(tokens)):
        return Verdict.BACKCHANNEL
    return Verdict.CONTENT

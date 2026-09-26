"""Barge-in vs backchannel decision for one overlap (user speech over agent speech).

LiveKit sends, every ~100 ms of new audio, the whole analysis window: up to 3 s
of 16 kHz mono user audio (1 s prefix + the overlapping speech so far). It never
says where an overlap starts, so we infer that from gaps between requests.

Signals, all optional except the elapsed time:

* transcript of the overlap part (NeMo-Speech.cpp offline Recognize) classified
  with the shared lexicon. Runs in the background; a decision never waits for it.
* MaAI ``bc_det_mono`` backchannel probability of the user channel.

Decision rules, in order:

1. overlap shorter than ``min_overlap_s``           -> not yet
2. transcript has a barge-in word ("stop", "wait")   -> interruption
3. transcript is only backchannel words              -> backchannel
4. transcript has >= ``min_content_words`` words      -> interruption
5. one content word and MaAI says backchannel        -> backchannel
6. one content word, overlap >= ``single_word_s``    -> interruption
7. no transcript engine: MaAI low and overlap >= ``no_asr_min_s``, or
   overlap >= ``long_overlap_s``                     -> interruption

Everything else (noise, coughs, laughter: no words) stays "not an interruption".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..backchannel.lexicon import Verdict, classify, content_words

SAMPLE_RATE = 16000
_FRAME = 400  # 25 ms, the granularity LiveKit assumes for returned probabilities
_TAIL_STEP = 160  # 10 ms, LiveKit's audio frame granularity


@dataclass
class ClassifierConfig:
    min_overlap_s: float = 0.25
    min_content_words: int = 2
    single_word_s: float = 0.6
    maai_threshold: float = 0.45
    no_asr_min_s: float = 0.6
    long_overlap_s: float = 2.0
    new_overlap_gap_s: float = 0.35
    """A gap this long between two requests starts a new overlap."""
    transcribe_every_s: float = 0.2
    """Re-transcribe once the overlap has grown by this much."""


@dataclass
class OverlapState:
    first_created_at: int | None = None
    last_created_at: int | None = None
    prev_window: np.ndarray | None = None
    transcript: str | None = None
    transcript_len_s: float = 0.0
    transcribing: bool = False
    extra: dict = field(default_factory=dict)

    def elapsed_s(self, created_at: int) -> float:
        if self.first_created_at is None:
            return 0.0
        # +0.1 s: the first request already carries one detection interval of speech
        return (created_at - self.first_created_at) / 1e9 + 0.1


@dataclass
class Decision:
    is_interruption: bool
    probability: float
    reason: str


def new_tail(prev: np.ndarray | None, cur: np.ndarray) -> tuple[np.ndarray, bool]:
    """Audio in ``cur`` that was not in ``prev``; ``True`` if ``cur`` continues ``prev``.

    The client's buffer is a rolling window, so ``cur`` is ``(prev + new)[-N:]``.
    """
    if prev is None or len(prev) == 0:
        return cur, False
    if len(cur) >= len(prev) and np.array_equal(cur[: len(prev)], prev):
        return cur[len(prev) :], True
    for added in range(_TAIL_STEP, len(cur), _TAIL_STEP):  # keep >= 1 overlapping sample
        kept = len(cur) - added
        if kept <= len(prev) and np.array_equal(cur[:kept], prev[len(prev) - kept :]):
            return cur[kept:], True
    return cur, False


def probabilities(p: float, n_samples: int) -> list[float]:
    return [round(p, 3)] * max(2, n_samples // _FRAME)


class BargeinClassifier:
    def __init__(self, config: ClassifierConfig | None = None, *, has_asr: bool, has_maai: bool) -> None:
        self.config = config or ClassifierConfig()
        self.has_asr = has_asr
        self.has_maai = has_maai

    def is_new_overlap(self, state: OverlapState, created_at: int) -> bool:
        return (
            state.last_created_at is None
            or (created_at - state.last_created_at) / 1e9 > self.config.new_overlap_gap_s
        )

    def wants_transcript(self, state: OverlapState, created_at: int) -> bool:
        return (
            self.has_asr
            and not state.transcribing
            and state.elapsed_s(created_at) - state.transcript_len_s >= self.config.transcribe_every_s
        )

    def decide(self, state: OverlapState, created_at: int, p_bc: float | None) -> Decision:
        cfg = self.config
        elapsed = state.elapsed_s(created_at)
        maai_backchannel = p_bc is not None and p_bc >= cfg.maai_threshold

        if elapsed < cfg.min_overlap_s:
            return Decision(False, 0.0, "too short")

        text = state.transcript
        if text:
            verdict = classify(text)
            if verdict is Verdict.INTERRUPT:
                return Decision(True, 0.95, f"barge-in word: {text!r}")
            if verdict is Verdict.BACKCHANNEL:
                return Decision(False, 0.05, f"backchannel: {text!r}")
            words = content_words(text)
            if words >= cfg.min_content_words:
                return Decision(True, 0.9, f"{words} content words: {text!r}")
            if maai_backchannel:
                return Decision(False, 0.2, f"MaAI p_bc={p_bc:.2f}: {text!r}")
            if elapsed >= cfg.single_word_s:
                return Decision(True, 0.7, f"single word held {elapsed:.2f}s: {text!r}")
            return Decision(False, 0.4, f"single word, waiting: {text!r}")

        if not self.has_asr:
            if self.has_maai and p_bc is not None and not maai_backchannel and elapsed >= cfg.no_asr_min_s:
                return Decision(True, 0.7, f"no ASR, MaAI p_bc={p_bc:.2f}, {elapsed:.2f}s")
            if elapsed >= cfg.long_overlap_s:
                return Decision(True, 0.6, f"no ASR, long overlap {elapsed:.2f}s")
        return Decision(False, 0.1, "no words")

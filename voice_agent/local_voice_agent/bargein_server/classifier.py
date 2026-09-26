"""Barge-in vs backchannel decision for one overlap (user speech over agent speech).

LiveKit sends, every ~100 ms of new audio, the whole analysis window: up to 3 s
of 16 kHz mono user audio (1 s prefix + the overlapping speech so far). It never
says where an overlap starts, so we infer that from gaps between requests.

Signals, all optional except the elapsed time:

* ai-coustics Voice Focus VAD probability from the full caller audio stream.
  When its gate is configured and a fresh score is low, background speech
  cannot interrupt even if overlap ASR recognizes words.
* transcript of the overlap part (NeMo-Speech.cpp offline Recognize) classified
  with the shared lexicon. Runs in the background; a decision never waits for it.
  ``OverlapState.asr_status`` tells whether text is pending, empty or failed.
* MaAI ``bc_det_mono`` backchannel probability of the user channel.

Decision rules, in order (``Decision.code`` in brackets):

1. overlap shorter than ``min_overlap_s``           -> wait        [overlap_too_short]
2. fresh Voice Focus VAD is below the foreground gate -> no         [voice_focus_vad_veto]
3. transcript has a barge-in word ("stop", "wait")   -> interrupt   [interrupt_token]
4. transcript is only backchannel/continuer words    -> no          [backchannel_*, continuer_phrase]
   transcript is the start of a known phrase ("do not", "i am"), overlap < ``single_word_s``
                                                     -> wait        [phrase_prefix_waiting]
5. transcript has >= ``min_content_words`` words      -> interrupt   [content_words]
6. one content word and MaAI says backchannel        -> no          [maai_backchannel]
7. one content word, overlap >= ``single_word_s``    -> interrupt   [single_word_held]
   otherwise                                         -> wait        [single_word_waiting]
8. no transcript engine: MaAI low and overlap >= ``no_asr_min_s``, or
   overlap >= ``long_overlap_s``                     -> interrupt   [no_asr_maai_low, no_asr_long_overlap]

Everything else (noise, coughs, laughter: no words) is not an interruption
[asr_pending, asr_empty, asr_error, asr_timeout, no_words].
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np

from ..backchannel.lexicon import Verdict, analyze
from ..backchannel.policy import MaaiReading

SAMPLE_RATE = 16000
_FRAME = 400  # 25 ms, the granularity LiveKit assumes for returned probabilities
_TAIL_STEP = 160  # 10 ms, LiveKit's audio frame granularity

AsrStatus = Literal["not_requested", "pending", "received", "empty", "error", "timeout"]
_WAIT_CODES = {"overlap_too_short", "single_word_waiting", "phrase_prefix_waiting", "asr_pending"}


@dataclass(frozen=True)
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
    vf_vad_gate_threshold: float | None = None
    """Optional Voice Focus veto; leave unset until calibrated against caller speech."""


@dataclass
class OverlapState:
    first_created_at: int | None = None
    last_created_at: int | None = None
    prev_window: np.ndarray | None = None
    transcript: str | None = None
    transcript_len_s: float = 0.0
    transcribing: bool = False
    asr_status: AsrStatus = "not_requested"
    asr_error: str | None = None
    lead_s: float = 0.1
    """Speech already contained in the first request (one LiveKit detection interval)."""
    extra: dict = field(default_factory=dict)

    def elapsed_s(self, created_at: int) -> float:
        if self.first_created_at is None:
            return 0.0
        return (created_at - self.first_created_at) / 1e9 + self.lead_s


@dataclass
class Decision:
    is_interruption: bool
    probability: float
    reason: str
    code: str = ""
    signals: dict[str, Any] = field(default_factory=dict)

    @property
    def outcome(self) -> str:
        if self.is_interruption:
            return "interrupt"
        return "wait" if self.code in _WAIT_CODES else "no_interrupt"


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

    def decide(
        self,
        state: OverlapState,
        created_at: int,
        p_bc: float | None,
        *,
        maai_reading: MaaiReading | None = None,
        vf_vad_p: float | None = None,
        vf_vad_delay_samples: int | None = None,
        vf_vad_age_s: float | None = None,
    ) -> Decision:
        cfg = self.config
        elapsed = state.elapsed_s(created_at)
        maai_backchannel = p_bc is not None and p_bc >= cfg.maai_threshold
        signals: dict[str, Any] = {
            "elapsed_overlap_s": round(elapsed, 3),
            "asr": {"status": state.asr_status}
            | ({"text": state.transcript} if state.transcript is not None else {})
            | ({"error": state.asr_error} if state.asr_error else {}),
            "maai": (maai_reading or MaaiReading(
                status="available" if p_bc is not None else "unavailable", p_bc=p_bc
            )).as_dict(),
            "voice_focus_vad": {
                "status": "available" if vf_vad_p is not None else "unavailable",
                "probability": vf_vad_p,
                "prediction_delay_samples": vf_vad_delay_samples,
                "age_s": round(vf_vad_age_s, 3) if vf_vad_age_s is not None else None,
            },
        }

        def d(interrupt: bool, p: float, code: str, reason: str) -> Decision:
            return Decision(interrupt, p, reason, code, signals)

        if elapsed < cfg.min_overlap_s:
            return d(False, 0.0, "overlap_too_short", "too short")

        if (
            cfg.vf_vad_gate_threshold is not None
            and vf_vad_p is not None
            and vf_vad_p < cfg.vf_vad_gate_threshold
        ):
            return d(False, 0.02, "voice_focus_vad_veto", "Voice Focus VAD below gate threshold")

        text = state.transcript
        if text:
            a = analyze(text)
            signals["content_words"] = a.content_words
            if a.verdict is Verdict.INTERRUPT:
                signals["interrupt_tokens"] = list(a.interrupt_tokens)
                return d(True, 0.95, "interrupt_token", f"barge-in word: {text!r}")
            if a.verdict is Verdict.BACKCHANNEL:
                if a.phrases:
                    signals["phrases"] = list(a.phrases)
                return d(False, 0.05, a.kind, f"backchannel: {text!r}")
            words = a.content_words
            if a.prefix_pending and elapsed < cfg.single_word_s:
                return d(False, 0.4, "phrase_prefix_waiting", f"may become a continuer: {text!r}")
            if words >= cfg.min_content_words:
                return d(True, 0.9, "content_words", f"{words} content words: {text!r}")
            if maai_backchannel:
                return d(False, 0.2, "maai_backchannel", f"MaAI p_bc={p_bc:.2f}: {text!r}")
            if elapsed >= cfg.single_word_s:
                return d(True, 0.7, "single_word_held", f"single word held {elapsed:.2f}s: {text!r}")
            return d(False, 0.4, "single_word_waiting", f"single word, waiting: {text!r}")

        if not self.has_asr:
            if self.has_maai and p_bc is not None and not maai_backchannel and elapsed >= cfg.no_asr_min_s:
                return d(True, 0.7, "no_asr_maai_low", f"no ASR, MaAI p_bc={p_bc:.2f}, {elapsed:.2f}s")
            if elapsed >= cfg.long_overlap_s:
                return d(True, 0.6, "no_asr_long_overlap", f"no ASR, long overlap {elapsed:.2f}s")
        code = {
            "pending": "asr_pending",
            "empty": "asr_empty",
            "error": "asr_error",
            "timeout": "asr_timeout",
        }.get(state.asr_status, "no_words")
        return d(False, 0.1, code, "no words")

    def thresholds(self) -> dict[str, Any]:
        return asdict(self.config)

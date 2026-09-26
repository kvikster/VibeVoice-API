"""Runs both interruption policies over a time-ordered stream of inputs.

Inputs are agent-state changes, optional MaAI frames and STT events. For every
STT event it returns two decision records:

* ``policy: "text_filter"``            - option 1: pass / hold / drop, plus the
  interruption the event would cause with LiveKit ``min_words``;
* ``policy: "interruption_classifier"`` - option 2's rules applied to the STT
  transcript of the current overlap: interrupt / wait / no_interrupt / not_applicable.

The runner is used live (``InterruptionFilterMixin`` in enforce and shadow mode)
and offline (``tools.replay_policy``). It never reads a clock and rejects inputs
that go back in time, so a log replays to the same decisions and no decision can
depend on a later event.

For the classifier the overlap starts at the first transcript of a user
utterance while the agent speaks (or when the agent starts speaking over an
open utterance). STT latency makes that later than the true speech onset, so
``elapsed_overlap_s`` here is an underestimate of what the audio-based server sees.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .backchannel.policy import (
    TRANSCRIPT_TYPES,
    UNAVAILABLE,
    AgentContext,
    FilterConfig,
    MaaiReading,
    decide_text,
)
from .bargein_server.classifier import BargeinClassifier, ClassifierConfig, OverlapState

REPLAY_CLOCK = "event_time_s"


def _ns(t: float) -> int:
    return round(t * 1e9)


class PolicyRunner:
    def __init__(
        self,
        filter_cfg: FilterConfig | None = None,
        classifier_cfg: ClassifierConfig | None = None,
        *,
        mode: str = "shadow",
    ) -> None:
        self.filter_cfg = filter_cfg or FilterConfig()
        self.classifier = BargeinClassifier(classifier_cfg, has_asr=True, has_maai=False)
        self.mode = mode
        self._last_t = float("-inf")
        # agent
        self._agent_state = "listening"
        self._speaking_since: float | None = None
        self._last_speaking_t: float | None = None
        self._agent_text = ""
        self._awaiting_answer = False
        # MaAI frames (offline source); live callers pass a reading per event instead
        self._maai: list[tuple[float, float]] = []
        # user utterance / overlap for the classifier
        self._utt_open = False
        self._utt_start: float | None = None
        self._utt_text: str | None = None
        self._asr_status = "not_requested"
        self._overlap: OverlapState | None = None

    # -- inputs -------------------------------------------------------------
    def agent(self, t: float, state: str, text: str | None = None) -> None:
        self._advance(t)
        if text is not None:
            self._agent_text = text
        was_speaking = self._agent_state == "speaking"
        if state == "speaking" and not was_speaking:
            self._speaking_since = t
            self._awaiting_answer = False
        if was_speaking and state != "speaking":
            self._last_speaking_t = t
            self._awaiting_answer = self._agent_text.rstrip().endswith("?")
            self._overlap = None
        if state == "speaking":
            self._last_speaking_t = t
        self._agent_state = state

    def maai(self, t: float, p_bc: float) -> None:
        self._advance(t)
        self._maai.append((t, p_bc))

    def stt(
        self,
        t: float,
        ev_type: str,
        text: str | None,
        *,
        seq: int | None = None,
        maai: MaaiReading | None = None,
        speech_duration_s: float | None = None,
    ) -> list[dict[str, Any]]:
        """``speech_duration_s`` (end - start of the event's words, when the STT gives
        them) back-dates the overlap start when an utterance arrives as a lone final."""
        self._advance(t)
        ctx = self.context(t)
        reading = maai if maai is not None else self._maai_reading(t)
        event = {"t": t, "type": ev_type, "text": text} | ({"event_seq": seq} if seq is not None else {})
        agent = {
            "state": ctx.state,
            "since_speaking_s": None if ctx.since_speaking_s is None else round(ctx.since_speaking_s, 4),
            "awaiting_answer": ctx.awaiting_answer,
        }

        fd = decide_text(ev_type, text, ctx, reading, self.filter_cfg)
        text_filter = {
            "kind": "decision",
            "policy": "text_filter",
            "mode": self.mode,
            **event,
            "agent": agent,
            "action": fd.action,
            "reason": fd.reason,
            "interruption": fd.interruption,
            "signals": fd.signals,
            "thresholds": asdict(self.filter_cfg),
        }
        classifier = {
            "kind": "decision",
            "policy": "interruption_classifier",
            "mode": self.mode,
            **event,
            "agent": agent,
            **self._classify(t, ev_type, text, reading, speech_duration_s),
            "thresholds": self.classifier.thresholds(),
        }
        return [text_filter, classifier]

    # -- state --------------------------------------------------------------
    @property
    def agent_state(self) -> str:
        return self._agent_state

    def context(self, t: float) -> AgentContext:
        if self._agent_state == "speaking":
            since: float | None = 0.0
        elif self._last_speaking_t is None:
            since = None
        else:
            since = t - self._last_speaking_t
        return AgentContext(self._agent_state, since, self._awaiting_answer)

    def _advance(self, t: float) -> None:
        if t < self._last_t:
            raise ValueError(f"input at t={t} arrived after t={self._last_t}; inputs must be time-ordered")
        self._last_t = t

    def _maai_reading(self, t: float) -> MaaiReading:
        if not self._maai:
            return UNAVAILABLE
        window = self.filter_cfg.maai_window_s
        recent = [(ti, p) for ti, p in self._maai if t - window <= ti <= t]
        if not recent:
            return MaaiReading(status="unavailable", window_s=window, clock=REPLAY_CLOCK, note="no frame in window")
        return MaaiReading(
            status="available",
            p_bc=max(p for _, p in recent),
            evaluated_at=recent[-1][0],
            window_s=window,
            clock=REPLAY_CLOCK,
        )

    def _classify(
        self, t: float, ev_type: str, text: str | None, reading: MaaiReading, speech_duration_s: float | None
    ) -> dict[str, Any]:
        if ev_type == "start_of_speech" or (ev_type in TRANSCRIPT_TYPES and not self._utt_open):
            self._utt_open, self._utt_text = True, None
            self._utt_start = t - max(speech_duration_s or 0.0, 0.0)
            self._asr_status = "pending"
            self._overlap = None
        if ev_type in TRANSCRIPT_TYPES:
            self._utt_text = text or ""
            self._asr_status = "received" if (text or "").strip() else "empty"
        elif ev_type == "error":
            self._asr_status = "error"

        result: dict[str, Any]
        if self._agent_state != "speaking":
            result = {"decision": "not_applicable", "reason": "agent_not_speaking"}
        elif not self._utt_open:
            result = {"decision": "not_applicable", "reason": "no_user_utterance"}
        elif ev_type not in (*TRANSCRIPT_TYPES, "start_of_speech", "error"):
            result = {"decision": "not_applicable", "reason": "non_transcript"}
        else:
            if self._overlap is None:
                utt_start = t if self._utt_start is None else self._utt_start
                start = utt_start if self._speaking_since is None else max(utt_start, self._speaking_since)
                self._overlap = OverlapState(first_created_at=_ns(start), lead_s=0.0)
            ov = self._overlap
            ov.last_created_at = _ns(t)
            ov.transcript = self._utt_text or None
            ov.asr_status = self._asr_status  # type: ignore[assignment]
            d = self.classifier.decide(ov, _ns(t), reading.p_bc, maai_reading=reading)
            result = {
                "decision": d.outcome,
                "reason": d.code,
                "detail": d.reason,
                "probability": d.probability,
                "signals": d.signals,
            }

        if ev_type == "final":
            self._utt_open = False
            self._overlap = None
        return result

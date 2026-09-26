"""Option 1: in-process interruption filter for LiveKit Agents 1.8.3.

Port of AssemblyAI's ``BackchannelSTTFilterMixin``
(https://github.com/AssemblyAI-Solutions/livekit-interruption-filters,
``filters/backchannel_stt.py``, MIT, Copyright (c) 2026 David Lange), adapted
to NeMo-Speech.cpp behind ``livekit-plugins-nvidia``:

* Gate 1 - only while the agent speaks, plus a grace window after it stops.
* Gate 2 - only transcript events. START/END_OF_SPEECH always pass, and so do
  empty finals, which ``MultiSpeakerAdapter`` emits to clear the interim text
  of a suppressed background speaker.
* Gate 3 - drop transcripts made only of backchannel tokens/phrases.
* Gate 4 (new) - hold short interims. Sortformer speaker tags only exist on
  finals, so an interim cannot yet be attributed to the primary speaker; an
  interim shorter than ``interim_min_words`` content words waits for its final.
  Barge-in words ("stop", "wait", ...) are never held.
* Gate 5 (new, optional) - MaAI ``bc_det``: a short utterance the lexicon does
  not know ("aha", or an ASR mishearing such as "but high") is dropped when
  MaAI says the user is backchanneling right now.

Nothing here touches LiveKit private attributes; ``stt_node`` and ``tts_node``
are public override points.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterable
from dataclasses import dataclass

from livekit import rtc
from livekit.agents import Agent, stt
from livekit.agents.voice import ModelSettings

from .lexicon import Verdict, classify, content_words
from .maai_detector import MaaiBackchannelDetector

log = logging.getLogger("local_voice_agent.filter")

_TRANSCRIPT_TYPES = {
    stt.SpeechEventType.INTERIM_TRANSCRIPT,
    stt.SpeechEventType.PREFLIGHT_TRANSCRIPT,
    stt.SpeechEventType.FINAL_TRANSCRIPT,
}


@dataclass
class FilterConfig:
    grace_s: float = 1.0
    """Keep filtering this long after the agent stops speaking."""
    interim_min_words: int = 3
    """While the agent speaks, interims with fewer content words wait for the final."""
    maai_threshold: float = 0.45
    """MaAI event-level operating point suggested by its authors."""
    maai_max_words: int = 2
    """MaAI may only veto utterances up to this many content words."""
    maai_window_s: float = 1.5
    """How far back to look for a MaAI backchannel peak."""


class InterruptionFilterMixin:
    """Put ahead of ``Agent`` in the MRO: ``class MyAgent(InterruptionFilterMixin, Agent)``."""

    filter_config: FilterConfig = FilterConfig()
    maai: MaaiBackchannelDetector | None = None

    _last_speaking_at: float = 0.0

    async def stt_node(
        self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings
    ) -> AsyncIterable[stt.SpeechEvent]:
        async def tee() -> AsyncIterable[rtc.AudioFrame]:
            async for frame in audio:
                if self.maai is not None:
                    self.maai.push_user(frame)
                yield frame

        async for ev in Agent.default.stt_node(self, tee(), model_settings):  # type: ignore[arg-type]
            if self._should_drop(ev):
                log.info(
                    "event_filtered text=%r type=%s agent_state=%s",
                    ev.alternatives[0].text if ev.alternatives else "",
                    ev.type,
                    self.session.agent_state,  # type: ignore[attr-defined]
                )
                continue
            yield ev

    async def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        async for frame in Agent.default.tts_node(self, text, model_settings):  # type: ignore[arg-type]
            if self.maai is not None:
                self.maai.push_agent(frame)
            yield frame

    def _should_drop(self, ev: stt.SpeechEvent) -> bool:
        cfg = self.filter_config
        now = time.monotonic()
        if self.session.agent_state == "speaking":  # type: ignore[attr-defined]
            self._last_speaking_at = now
        elif now - self._last_speaking_at > cfg.grace_s:
            if self.maai is not None:
                self.maai.clear_agent()
            return False

        if ev.type not in _TRANSCRIPT_TYPES or not ev.alternatives:
            return False

        text = ev.alternatives[0].text
        verdict = classify(text)
        if verdict in (Verdict.EMPTY, Verdict.INTERRUPT):
            return False
        if verdict is Verdict.BACKCHANNEL:
            return True

        words = content_words(text)
        if (
            self.maai is not None
            and words <= cfg.maai_max_words
            and self.maai.recent_max(cfg.maai_window_s) >= cfg.maai_threshold
        ):
            return True
        if ev.type != stt.SpeechEventType.FINAL_TRANSCRIPT and words < cfg.interim_min_words:
            return True
        return False

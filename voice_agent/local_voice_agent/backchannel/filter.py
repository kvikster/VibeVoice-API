"""Option 1: in-process interruption filter for LiveKit Agents 1.8.3.

Port of AssemblyAI's ``BackchannelSTTFilterMixin``
(https://github.com/AssemblyAI-Solutions/livekit-interruption-filters,
``filters/backchannel_stt.py``, MIT, Copyright (c) 2026 David Lange), adapted
to NeMo-Speech.cpp behind ``livekit-plugins-nvidia``. The rules live in
``policy.decide_text``:

* only while the agent speaks, or within ``grace_s`` after it stopped - unless
  its last utterance was a question, so a quick "Yes" answer is never dropped;
* START/END_OF_SPEECH and empty finals (``MultiSpeakerAdapter`` clearing a
  suppressed background final) always pass;
* drop transcripts made only of backchannel tokens, phrases or continuers
  ("I am with you", "do not stop"); barge-in words ("stop", "wait") pass;
* hold interims shorter than ``interim_min_words`` content words: Sortformer
  speaker tags only exist on finals, so they wait for their final;
* optional MaAI ``bc_det`` veto for short utterances the lexicon doesn't know.

``mode="shadow"`` yields every STT event unchanged and immediately, and only
logs what enforce mode would have done. Either mode can log a replayable JSONL
(agent states, STT events, MaAI readings, decisions of both policies); see
``tools.replay_policy``.

``stt_node`` and ``tts_node`` are public override points; nothing here touches
LiveKit private attributes.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterable
from typing import Any, Literal

from livekit import rtc
from livekit.agents import Agent, stt
from livekit.agents.voice import ModelSettings

from ..jsonl import EVENT_TYPE_NAMES, JsonlWriter, event_fields, speech_duration
from ..policy_runner import PolicyRunner
from .maai_detector import MaaiBackchannelDetector
from .policy import FilterConfig

log = logging.getLogger("local_voice_agent.filter")

FilterMode = Literal["enforce", "shadow"]


class InterruptionFilterMixin:
    """Put ahead of ``Agent`` in the MRO: ``class MyAgent(InterruptionFilterMixin, Agent)``."""

    filter_config: FilterConfig = FilterConfig()
    filter_mode: FilterMode = "enforce"
    maai: MaaiBackchannelDetector | None = None
    decision_log: JsonlWriter | None = None

    _runner: PolicyRunner | None = None
    _clock_t0: float | None = None
    _agent_text: str = ""
    _seq: int = 0
    _listening_to_session: bool = False

    # -- LiveKit nodes --------------------------------------------------------
    async def stt_node(
        self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings
    ) -> AsyncIterable[stt.SpeechEvent]:
        self._listen_to_agent_state()

        async def tee() -> AsyncIterable[rtc.AudioFrame]:
            async for frame in audio:
                if self.maai is not None:
                    self.maai.push_user(frame)
                yield frame

        async for ev in Agent.default.stt_node(self, tee(), model_settings):  # type: ignore[arg-type]
            if self._process(ev):
                yield ev

    async def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        self._agent_text = ""

        async def tee_text() -> AsyncIterable[str]:
            async for chunk in text:
                self._agent_text += chunk
                yield chunk

        async for frame in Agent.default.tts_node(self, tee_text(), model_settings):  # type: ignore[arg-type]
            if self.maai is not None:
                self.maai.push_agent(frame)
            yield frame

    # -- policy ---------------------------------------------------------------
    def _now(self) -> float:
        if self._clock_t0 is None:
            self._clock_t0 = time.monotonic()
        return round(time.monotonic() - self._clock_t0, 4)

    def _policy(self) -> PolicyRunner:
        if self._runner is None:
            self._runner = PolicyRunner(self.filter_config, mode=self.filter_mode)
        return self._runner

    def _listen_to_agent_state(self) -> None:
        if self._listening_to_session:
            return
        self._listening_to_session = True
        self.session.on("agent_state_changed", lambda ev: self._on_agent_state(ev.new_state))  # type: ignore[attr-defined]

    def _on_agent_state(self, state: str) -> None:
        t = self._now()
        runner = self._policy()
        runner.agent(t, state, text=self._agent_text)
        self._log({"kind": "agent", "t": t, "state": state, "text": self._agent_text})
        if state != "speaking" and self.maai is not None:
            self.maai.clear_agent()

    def _process(self, ev: stt.SpeechEvent) -> bool:
        """Log the decisions for ``ev``; return whether to forward it."""
        runner = self._policy()
        # the session state is authoritative; catch up if a change was not observed
        if self.session.agent_state != runner.agent_state:  # type: ignore[attr-defined]
            self._on_agent_state(self.session.agent_state)  # type: ignore[attr-defined]

        t = self._now()
        self._seq += 1
        ev_type = EVENT_TYPE_NAMES.get(ev.type, str(ev.type))
        text = ev.alternatives[0].text if ev.alternatives else None
        reading = self.maai.reading(self.filter_config.maai_window_s) if self.maai is not None else None
        stt_record: dict[str, Any] = {"kind": "stt", "t": t, "seq": self._seq} | event_fields(ev)
        if reading is not None:
            stt_record["maai"] = reading.as_dict()
        self._log(stt_record)

        # computed from the logged (rounded) fields so a replay sees exactly the same input
        text_filter, classifier = runner.stt(
            t, ev_type, text, seq=self._seq, maai=reading, speech_duration_s=speech_duration(stt_record)
        )
        self._log(text_filter)
        self._log(classifier)

        if self.filter_mode == "shadow" or text_filter["action"] == "pass":
            return True
        log.info("event_filtered action=%s reason=%s text=%r", text_filter["action"], text_filter["reason"], text)
        return False

    def _log(self, record: dict[str, Any]) -> None:
        if self.decision_log is not None:
            self.decision_log.write(record)

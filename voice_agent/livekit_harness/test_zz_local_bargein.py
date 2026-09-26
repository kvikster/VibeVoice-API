"""Option 2 end to end: AgentSession -> AdaptiveInterruptionDetector -> local /bargein server.

Runs inside a livekit/agents checkout (see run.sh) to reuse its fake session harness.
"""

import asyncio
import os
import sys

import pytest
from aiohttp.test_utils import TestServer

from livekit.agents import Agent
from livekit.agents.utils import http_context

from .fake_session import FakeActions, create_session, run_session

sys.path.insert(0, os.environ["VOICE_AGENT_DIR"])
from local_voice_agent.bargein_server import BargeinServer  # noqa: E402
from local_voice_agent.bargein_server.transcriber import TranscriptResult  # noqa: E402

pytestmark = [pytest.mark.unit]


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self.text, self.calls = text, 0

    async def transcribe(self, pcm16):
        self.calls += 1
        return TranscriptResult("received" if self.text else "empty", self.text)


class Plain(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant.")


def scenario(text: str) -> FakeActions:
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(8.0)  # playout ~3.5s .. 11.5s
    actions.add_user_speech(5.0, 6.2, text, stt_delay=0.2)
    return actions


async def run(asr_text: str, monkeypatch):
    asr = FakeTranscriber(asr_text)
    server = BargeinServer(api_key="k", api_secret="s" * 32, transcriber=asr)
    async with TestServer(server.app()) as ts, http_context.open():
        monkeypatch.setenv("LIVEKIT_INFERENCE_URL", str(ts.make_url("")).rstrip("/"))
        monkeypatch.setenv("LIVEKIT_INFERENCE_API_KEY", "k")
        monkeypatch.setenv("LIVEKIT_INFERENCE_API_SECRET", "s" * 32)
        session = create_session(
            scenario(asr_text or "..."),
            turn_handling={"interruption": {"mode": "adaptive", "resume_false_interruption": False}},
        )
        finished, overlaps, errors = [], [], []
        session.output.audio.on("playback_finished", finished.append)
        session.on("overlapping_speech", overlaps.append)
        session.on("error", errors.append)

        async def pump_audio():  # the fake harness drives VAD/STT only; stream audio as well
            await asyncio.sleep(0.2)
            while True:
                session.input.audio.push(0.02)
                await asyncio.sleep(0.02)

        pump = asyncio.create_task(pump_audio())
        try:
            await asyncio.wait_for(run_session(session, Plain()), timeout=90)
        finally:
            pump.cancel()
    return finished, asr, overlaps, errors


async def test_adaptive_local_backchannel(monkeypatch):
    finished, asr, overlaps, errors = await run("mhm", monkeypatch)
    assert not errors and asr.calls > 0
    assert overlaps and not any(o.is_interruption for o in overlaps)
    assert finished and not finished[0].interrupted


async def test_adaptive_local_barge_in(monkeypatch):
    finished, asr, overlaps, errors = await run("stop please", monkeypatch)
    assert not errors and asr.calls > 0
    assert any(o.is_interruption for o in overlaps)
    assert finished and finished[0].interrupted

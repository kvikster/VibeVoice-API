"""Option 1 inside a real AgentSession (fake STT/VAD/LLM/TTS, virtual time).

Runs inside a livekit/agents checkout (see run.sh) to reuse its fake session harness.
The first test is the control: without the filter, "Mhm." interrupts the agent.
"""

import asyncio
import os
import sys

import pytest

from livekit.agents import Agent

from .fake_session import FakeActions, create_session, run_session

sys.path.insert(0, os.environ["VOICE_AGENT_DIR"])
from local_voice_agent.backchannel.filter import InterruptionFilterMixin  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.virtual_time]


class Plain(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant.")


class Filtered(InterruptionFilterMixin, Plain):
    pass


def scenario(text: str, start: float = 5.0, end: float = 5.4) -> FakeActions:
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)  # playout ~3.5s .. 13.5s
    actions.add_user_speech(start, end, text, stt_delay=0.2)
    return actions


async def run(agent: Agent, actions: FakeActions, min_words: int):
    session = create_session(
        actions,
        turn_handling={"interruption": {"min_words": min_words, "resume_false_interruption": False}},
    )
    finished = []
    user_turns = []
    session.output.audio.on("playback_finished", finished.append)
    session.on("user_input_transcribed", lambda ev: ev.is_final and user_turns.append(ev.transcript))
    await asyncio.wait_for(run_session(session, agent), timeout=60)
    return finished, user_turns


async def test_baseline_backchannel_interrupts_without_filter():
    finished, _ = await run(Plain(), scenario("Mhm."), min_words=1)
    assert finished and finished[0].interrupted


async def test_filter_backchannel_does_not_interrupt():
    finished, turns = await run(Filtered(), scenario("Mhm."), min_words=1)
    assert finished and not finished[0].interrupted
    assert "Mhm." not in turns


async def test_filter_barge_in_still_interrupts():
    finished, _ = await run(Filtered(), scenario("Stop!"), min_words=1)
    assert finished and finished[0].interrupted


async def test_filter_real_sentence_interrupts():
    finished, _ = await run(Filtered(), scenario("Can you tell me something else", 5.0, 6.5), min_words=1)
    assert finished and finished[0].interrupted


async def test_no_words_do_not_interrupt_with_min_words():
    finished, _ = await run(Filtered(), scenario(""), min_words=1)
    assert finished and not finished[0].interrupted

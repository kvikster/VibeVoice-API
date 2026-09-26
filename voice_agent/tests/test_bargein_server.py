"""Drive the real livekit-agents 1.8.3 AdaptiveInterruptionDetector against our server.

This is what guards option 2: if LiveKit changes its private /bargein protocol,
these tests fail when livekit-agents is upgraded.
"""

import asyncio
import time

import aiohttp
import numpy as np
from aiohttp.test_utils import TestServer

from livekit import rtc
from livekit.agents.inference import AdaptiveInterruptionDetector
from livekit.agents.inference.interruption import (
    _AgentSpeechStartedSentinel,
    _OverlapSpeechEndedSentinel,
    _OverlapSpeechStartedSentinel,
)

from local_voice_agent.bargein_server import BargeinServer
from local_voice_agent.bargein_server.transcriber import TranscriptResult

KEY, SECRET = "devkey", "devsecret-devsecret-devsecret-00"


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    async def transcribe(self, pcm16):
        self.calls += 1
        return TranscriptResult("received" if self.text else "empty", self.text)


def frame(seconds: float = 0.01) -> rtc.AudioFrame:
    n = int(16000 * seconds)
    data = (np.random.default_rng(0).normal(0, 3000, n)).astype(np.int16)
    return rtc.AudioFrame(data=data.tobytes(), sample_rate=16000, num_channels=1, samples_per_channel=n)


class ListLog:
    def __init__(self) -> None:
        self.records = []

    def write(self, rec) -> None:
        self.records.append(rec)


async def run_overlap(transcript: str, *, overlap_s: float, api_secret: str = SECRET, log=None):
    transcriber = FakeTranscriber(transcript)
    server = BargeinServer(api_key=KEY, api_secret=SECRET, transcriber=transcriber, decision_log=log)
    async with TestServer(server.app()) as ts, aiohttp.ClientSession() as http:
        detector = AdaptiveInterruptionDetector(
            base_url=str(ts.make_url("")).rstrip("/"),
            api_key=KEY,
            api_secret=api_secret,
            http_session=http,
        )
        errors = []
        detector.on("error", errors.append)
        stream = detector.stream()
        events = []

        async def collect():
            async for ev in stream:
                events.append(ev)

        collector = asyncio.create_task(collect())
        stream.push_frame(_AgentSpeechStartedSentinel())
        for _ in range(50):  # 0.5 s of agent speech before the user starts
            stream.push_frame(frame())
        stream.push_frame(_OverlapSpeechStartedSentinel(speech_duration=0.1, started_at=time.time()))
        for _ in range(int(overlap_s * 100)):
            stream.push_frame(frame())
            await asyncio.sleep(0.01)
            if any(e.is_interruption for e in events):
                break
        stream.push_frame(_OverlapSpeechEndedSentinel(ended_at=time.time()))
        await asyncio.sleep(0.2)
        await stream.aclose()
        collector.cancel()
        return events, errors, transcriber


async def test_barge_in_word_interrupts():
    events, errors, asr = await run_overlap("stop, wait", overlap_s=1.5)
    assert not errors and asr.calls
    hits = [e for e in events if e.is_interruption]
    assert hits and hits[0].probability >= 0.9  # probabilities came from our server
    assert hits[0].detection_delay < 1.0


async def test_backchannel_does_not_interrupt():
    events, errors, asr = await run_overlap("uh-huh", overlap_s=1.2)
    assert not errors and asr.calls >= 2  # re-transcribed as the overlap grew
    assert len(events) == 1 and not events[0].is_interruption
    assert events[0].num_requests >= 5  # answered, not timed out


async def test_noise_without_words_does_not_interrupt():
    events, errors, asr = await run_overlap("", overlap_s=1.2)
    assert not errors and asr.calls
    assert not any(e.is_interruption for e in events)


async def test_bad_token_is_rejected():
    _, errors, asr = await run_overlap("stop", overlap_s=0.3, api_secret="wrong-secret-wrong-secret-000000")
    assert errors and not asr.calls


async def test_decision_log_explains_every_reply():
    log = ListLog()
    events, errors, _ = await run_overlap("uh-huh", overlap_s=1.0, log=log)
    assert not errors and log.records
    reasons = [r["reason"] for r in log.records]
    assert reasons[0] == "overlap_too_short" and "backchannel_tokens" in reasons
    rec = next(r for r in log.records if r["reason"] == "backchannel_tokens")
    assert rec["decision"] == "no_interrupt" and rec["reply"] == "InterruptionWSInferenceDoneMessage"
    assert rec["signals"]["asr"] == {"status": "received", "text": "uh-huh"}
    assert rec["signals"]["maai"] == {"status": "unavailable"}
    assert rec["thresholds"]["min_overlap_s"] == 0.25 and rec["threshold"] == 0.5
    # before the first transcript came back the ASR state is explicit
    assert log.records[0]["signals"]["asr"]["status"] in ("pending", "not_requested", "received")

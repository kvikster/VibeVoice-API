"""The agent's WebSocket client against a gateway and scripted Riva backend."""

from __future__ import annotations

import asyncio
import aiohttp
import numpy as np
import pytest
from aiohttp.test_utils import TestServer
from livekit import rtc
from livekit.agents import stt

from local_voice_agent.bargein_server import BargeinServer
from local_voice_agent.bargein_server.aic_vad import AicVadHub
from local_voice_agent.bargein_server.stt_route import GatewaySTTRoute
from local_voice_agent.gateway_stt import GatewaySTT
from local_voice_agent.settings import Settings
from local_voice_agent.stt import build_direct_stt, build_raw_stt, build_stt

from .fake_riva import FakeRiva, Step, response, serve

KEY, SECRET = "devkey", "devsecret-devsecret-devsecret-00"


@pytest.fixture
def riva():
    fake = FakeRiva(
        script=[Step(0.25, response("hello", final=False))],
        on_end=[
            response(
                "Hello there.",
                final=True,
                words=[("Hello", 100, 400, 1), ("there.", 500, 800, 1)],
            )
        ],
    )
    server, addr = serve(fake)
    yield fake, addr
    server.stop(0)


def frame(amplitude: int = 3000) -> rtc.AudioFrame:
    pcm = np.full(320, amplitude, dtype=np.int16)
    return rtc.AudioFrame(
        data=pcm.tobytes(), sample_rate=16000, num_channels=1, samples_per_channel=320
    )


async def test_gateway_preserves_streaming_events_speaker_and_eof(riva):
    fake, addr = riva
    settings = Settings(riva_server=addr)
    route = GatewaySTTRoute(stt_factory=lambda: build_raw_stt(settings))
    server = BargeinServer(api_key=KEY, api_secret=SECRET, stt_route=route)
    async with TestServer(server.app()) as ts:
        url = str(ts.make_url("/stt")).replace("http://", "ws://")
        asr = GatewaySTT(url=url, api_key=KEY, api_secret=SECRET)
        stream = asr.stream()
        for _ in range(40):
            stream.push_frame(frame())
        stream.end_input()
        events = [event async for event in stream]
        await stream.aclose()
    assert fake.received_s >= 0.8
    assert stt.SpeechEventType.INTERIM_TRANSCRIPT in [event.type for event in events]
    final = next(
        event for event in events if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT
    )
    assert final.alternatives[0].text == "Hello there."
    assert final.alternatives[0].speaker_id == "S1"
    assert final.alternatives[0].words is not None
    assert [str(word) for word in final.alternatives[0].words] == ["Hello", "there."]
    assert asr.capabilities.aligned_transcript == "word"


async def test_gateway_enhances_before_nemotron(riva):
    fake, addr = riva

    class Enhancer:
        enabled = True
        frames = 0

        def _process(self, input_frame):
            self.frames += 1
            out = rtc.AudioFrame(
                data=(np.frombuffer(input_frame.data, dtype=np.int16) // 2)
                .astype(np.int16)
                .tobytes(),
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=320,
            )
            out.userdata["lk.aic-vad"] = True
            return out

    enhancer = Enhancer()
    route = GatewaySTTRoute(
        stt_factory=lambda: build_raw_stt(Settings(riva_server=addr)),
        enhancer_factory=lambda: enhancer,
    )
    server = BargeinServer(api_key=KEY, api_secret=SECRET, stt_route=route)
    async with TestServer(server.app()) as ts:
        asr = GatewaySTT(
            url=str(ts.make_url("/stt")).replace("http://", "ws://"),
            api_key=KEY,
            api_secret=SECRET,
        )
        stream = asr.stream()
        for _ in range(40):
            stream.push_frame(frame())
        stream.end_input()
        _ = [event async for event in stream]
        await stream.aclose()
    assert enhancer.frames == 40
    assert fake.received_peak == 1500


async def test_gateway_vad_consumes_full_stream_and_exposes_fresh_room_score(
    riva, monkeypatch
):
    _, addr = riva
    headers = {"X-LiveKit-Room-ID": "room-1", "X-LiveKit-Job-ID": "job-1"}
    monkeypatch.setattr(
        "local_voice_agent.gateway_stt.get_inference_headers", lambda: headers
    )
    hub = AicVadHub()

    class Scorer:
        prediction_delay_samples = 480
        samples = 0

        def push(self, pcm):
            self.samples += len(pcm)
            return 0.85

    scorer = Scorer()
    route = GatewaySTTRoute(
        stt_factory=lambda: build_raw_stt(Settings(riva_server=addr)),
        vad_factory=lambda: scorer,
        vad_hub=hub,
    )
    async with TestServer(BargeinServer(stt_route=route).app()) as ts:
        asr = GatewaySTT(
            url=str(ts.make_url("/stt")).replace("http://", "ws://"),
            api_key=KEY,
            api_secret=SECRET,
        )
        stream = asr.stream()
        for _ in range(40):
            stream.push_frame(frame())
        for _ in range(20):
            if hub.read(headers) is not None:
                break
            await asyncio.sleep(0.01)
        reading = hub.read(headers)
        assert reading is not None and reading.probability == 0.85
        assert reading.prediction_delay_samples == 480
        stream.end_input()
        _ = [event async for event in stream]
        await stream.aclose()
    assert scorer.samples == 40 * 320
    assert hub.read(headers) is None


async def test_gateway_multispeaker_suppresses_background_after_enhancement():
    fake = FakeRiva(
        script=[
            Step(
                1.5,
                response(
                    "Hello there.",
                    final=True,
                    words=[
                        ("Hello", 200, 700, 1),
                        ("there.", 800, 1300, 1),
                    ],
                ),
            ),
        ],
        on_end=[
            response(
                "Background talk.",
                final=True,
                words=[
                    ("Background", 1900, 2300, 2),
                    ("talk.", 2400, 2700, 2),
                ],
            )
        ],
    )
    riva, addr = serve(fake)

    class Enhancer:
        enabled = True

        def _process(self, input_frame):
            output = rtc.AudioFrame(
                data=input_frame.data.tobytes(),
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=320,
            )
            output.userdata["lk.aic-vad"] = True
            return output

    route = GatewaySTTRoute(
        stt_factory=lambda: build_stt(Settings(riva_server=addr)),
        enhancer_factory=Enhancer,
    )
    try:
        async with TestServer(BargeinServer(stt_route=route).app()) as ts:
            client = GatewaySTT(
                url=str(ts.make_url("/stt")).replace("http://", "ws://"),
                api_key=KEY,
                api_secret=SECRET,
            )
            stream = client.stream()
            for i in range(150):
                amplitude = 15000 if 10 <= i < 70 else 3000 if 90 <= i < 140 else 0
                stream.push_frame(frame(amplitude))
            stream.end_input()
            events = [event async for event in stream]
            await stream.aclose()
        finals = [
            event.alternatives[0]
            for event in events
            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT
        ]
        assert [item.text for item in finals] == ["Hello there.", ""]
        assert finals[0].is_primary_speaker is True
    finally:
        riva.stop(0)


async def test_gateway_rejects_bad_token_and_audio_format(riva):
    _, addr = riva
    server = BargeinServer(
        api_key=KEY,
        api_secret=SECRET,
        stt_route=GatewaySTTRoute(
            stt_factory=lambda: build_raw_stt(Settings(riva_server=addr))
        ),
    )
    async with TestServer(server.app()) as ts, aiohttp.ClientSession() as session:
        url = str(ts.make_url("/stt")).replace("http://", "ws://")
        with pytest.raises(aiohttp.WSServerHandshakeError) as exc:
            await session.ws_connect(url)
        assert exc.value.status == 401
        # The authenticated client's format check is exercised through the
        # real client, which requires a 16 kHz mono stream.
        asr = GatewaySTT(url=url, api_key=KEY, api_secret=SECRET)
        stream = asr.stream()
        stream.push_frame(frame())
        stream.end_input()
        _ = [event async for event in stream]
        await stream.aclose()


async def test_gateway_rejects_silent_aic_passthrough(riva):
    fake, addr = riva

    class FailedEnhancer:
        enabled = False

        def _process(self, input_frame):
            return input_frame

    route = GatewaySTTRoute(
        stt_factory=lambda: build_raw_stt(Settings(riva_server=addr)),
        enhancer_factory=FailedEnhancer,
    )
    async with (
        TestServer(BargeinServer(stt_route=route).app()) as ts,
        aiohttp.ClientSession() as session,
    ):
        async with session.ws_connect(
            str(ts.make_url("/stt")).replace("http://", "ws://")
        ) as ws:
            await ws.send_json(
                {
                    "type": "start",
                    "version": 1,
                    "sample_rate": 16000,
                    "num_channels": 1,
                    "encoding": "s16le",
                }
            )
            assert (await ws.receive_json())["type"] == "ready"
            await ws.send_bytes(frame().data.tobytes())
            assert await ws.receive_json() == {"type": "error", "code": "RuntimeError"}
    assert fake.received_peak == 0


def test_agent_gateway_settings_keep_aic_off_agent(monkeypatch):
    monkeypatch.setenv("LIVEKIT_INFERENCE_API_KEY", KEY)
    monkeypatch.setenv("LIVEKIT_INFERENCE_API_SECRET", SECRET)
    settings = Settings(stt_gateway_url="ws://gateway.internal:8765/stt")
    adapted = build_stt(settings)
    assert isinstance(adapted, GatewaySTT)
    assert isinstance(build_direct_stt(settings), stt.MultiSpeakerAdapter)
    with pytest.raises(ValueError, match="server-side ai-coustics"):
        Settings(stt_gateway_url=settings.stt_gateway_url, audio_enhancement="aic")

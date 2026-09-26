"""LiveKit STT client for the private audio gateway's streaming WebSocket."""

from __future__ import annotations

import asyncio

import aiohttp
from livekit import api, rtc
from livekit.agents import APIConnectOptions, stt
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, NotGivenOr
from livekit.agents.utils import AudioBuffer
from livekit.agents.inference._utils import get_inference_headers

from .gateway_wire import SAMPLE_RATE, WIRE_VERSION, event_from_wire


class GatewaySTT(stt.STT):
    def __init__(self, *, url: str, api_key: str, api_secret: str) -> None:
        if not url.startswith(("ws://", "wss://")):
            raise ValueError("STT_GATEWAY_URL must start with ws:// or wss://")
        if not api_key or not api_secret:
            raise ValueError(
                "gateway STT requires LIVEKIT_INFERENCE_API_KEY and SECRET"
            )
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
                diarization=True,
                aligned_transcript="word",
                offline_recognize=False,
            )
        )
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret

    @property
    def model(self) -> str:
        return "nemotron-speech-en-sortformer"

    @property
    def provider(self) -> str:
        return "nemotron-gateway"

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        raise NotImplementedError("gateway STT supports streaming only")

    def stream(
        self,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.RecognizeStream:
        return GatewaySpeechStream(stt=self, conn_options=conn_options)


class GatewaySpeechStream(stt.RecognizeStream):
    def __init__(self, *, stt: GatewaySTT, conn_options: APIConnectOptions) -> None:
        super().__init__(stt=stt, conn_options=conn_options, sample_rate=SAMPLE_RATE)
        self._gateway = stt

    async def _run(self) -> None:
        token = (
            api.AccessToken(self._gateway._api_key, self._gateway._api_secret)
            .with_identity("agent")
            .to_jwt()
        )
        timeout = aiohttp.ClientTimeout(
            total=None, sock_connect=self._conn_options.timeout
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(
                self._gateway._url,
                headers={**get_inference_headers(), "Authorization": f"Bearer {token}"},
                heartbeat=20,
            ) as ws:
                await ws.send_json(
                    {
                        "type": "start",
                        "version": WIRE_VERSION,
                        "sample_rate": SAMPLE_RATE,
                        "num_channels": 1,
                        "encoding": "s16le",
                    }
                )
                ready = await asyncio.wait_for(
                    ws.receive_json(), self._conn_options.timeout
                )
                if ready != {
                    "type": "ready",
                    "version": WIRE_VERSION,
                    "sample_rate": SAMPLE_RATE,
                }:
                    raise RuntimeError(f"gateway STT start failed: {ready.get('type')}")

                async def send_audio() -> None:
                    async for item in self._input_ch:
                        if isinstance(item, rtc.AudioFrame):
                            await ws.send_bytes(item.data.tobytes())
                        elif isinstance(item, self._FlushSentinel):
                            break
                    await ws.send_json({"type": "end"})

                async def receive_events() -> None:
                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            data = message.json()
                            if data.get("type") == "stt":
                                self._event_ch.send_nowait(event_from_wire(data))
                            elif data.get("type") == "end":
                                return
                            elif data.get("type") == "error":
                                raise RuntimeError(
                                    f"gateway STT error: {data.get('code')}"
                                )
                            else:
                                raise RuntimeError("unexpected gateway STT message")
                        elif message.type == aiohttp.WSMsgType.ERROR:
                            raise RuntimeError("gateway STT WebSocket failed")
                    raise RuntimeError("gateway STT closed before final drain")

                async with asyncio.TaskGroup() as tasks:
                    tasks.create_task(send_audio())
                    tasks.create_task(receive_events())

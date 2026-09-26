"""Gateway audio route: raw PCM -> optional Voice Focus -> streaming Nemotron."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
import logging

import numpy as np

from aiohttp import WSMsgType, web
from livekit import rtc
from livekit.agents import stt

from ..gateway_wire import SAMPLE_RATE, WIRE_VERSION, event_to_wire
from .aic_vad import AicVadHub, AicVadScorer

logger = logging.getLogger("local_voice_agent.gateway_stt")

_FRAME_SAMPLES = 320  # 20 ms at 16 kHz; stable frame size for the enhancer
_MAX_MESSAGE_BYTES = SAMPLE_RATE * 2  # at most one second per WebSocket message


class GatewaySTTRoute:
    def __init__(
        self,
        *,
        stt_factory: Callable[[], stt.STT],
        enhancer_factory: Callable[[], object] | None = None,
        vad_factory: Callable[[], AicVadScorer] | None = None,
        vad_hub: AicVadHub | None = None,
        drain_timeout_s: float = 15.0,
    ) -> None:
        self._stt_factory = stt_factory
        self._enhancer_factory = enhancer_factory
        self._vad_factory = vad_factory
        self._vad_hub = vad_hub
        self._drain_timeout_s = drain_timeout_s

    async def handle(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(max_msg_size=_MAX_MESSAGE_BYTES)
        await ws.prepare(request)
        stream: stt.RecognizeStream | None = None
        backend: stt.STT | None = None
        enhancer = None
        vad_scorer: AicVadScorer | None = None
        vad_lease = None
        output_task: asyncio.Task | None = None
        pending = bytearray()
        ended = False
        try:
            first = await ws.receive_json()
            if first != {
                "type": "start",
                "version": WIRE_VERSION,
                "sample_rate": SAMPLE_RATE,
                "num_channels": 1,
                "encoding": "s16le",
            }:
                await ws.send_json(
                    {"type": "error", "code": "unsupported_audio_format"}
                )
                return ws
            # Factories run on the gateway only. No ai-coustics dependency or key is
            # needed in the LiveKit agent process.
            backend = self._stt_factory()
            enhancer = self._enhancer_factory() if self._enhancer_factory else None
            vad_scorer = self._vad_factory() if self._vad_factory else None
            vad_lease = self._vad_hub.start(request.headers) if self._vad_hub else None
            stream = backend.stream()

            async def forward_events() -> None:
                assert stream is not None
                async for event in stream:
                    await ws.send_json(event_to_wire(event))

            output_task = asyncio.create_task(forward_events())
            await ws.send_json(
                {"type": "ready", "version": WIRE_VERSION, "sample_rate": SAMPLE_RATE}
            )

            async for message in ws:
                if message.type == WSMsgType.BINARY:
                    raw = message.data
                    if not raw or len(raw) > _MAX_MESSAGE_BYTES or len(raw) % 2:
                        raise ValueError("invalid PCM frame")
                    pending.extend(raw)
                    while len(pending) >= _FRAME_SAMPLES * 2:
                        chunk = bytes(pending[: _FRAME_SAMPLES * 2])
                        del pending[: _FRAME_SAMPLES * 2]
                        vad_scorer = self._push(
                            stream, enhancer, chunk, vad_scorer, vad_lease
                        )
                elif message.type == WSMsgType.TEXT:
                    if message.json() != {"type": "end"}:
                        raise ValueError("unexpected control message")
                    if pending:
                        chunk = bytes(pending).ljust(_FRAME_SAMPLES * 2, b"\0")
                        vad_scorer = self._push(
                            stream, enhancer, chunk, vad_scorer, vad_lease
                        )
                        pending.clear()
                    stream.end_input()
                    ended = True
                    await asyncio.wait_for(output_task, self._drain_timeout_s)
                    await ws.send_json({"type": "end"})
                    return ws
                else:
                    break
        except (ValueError, asyncio.TimeoutError, RuntimeError) as exc:
            if not ws.closed:
                await ws.send_json({"type": "error", "code": type(exc).__name__})
        finally:
            if output_task is not None and not output_task.done():
                output_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await output_task
            if stream is not None:
                if not ended:
                    with contextlib.suppress(RuntimeError):
                        stream.end_input()
                await stream.aclose()
            if backend is not None:
                await backend.aclose()
            if enhancer is not None and hasattr(enhancer, "_close"):
                enhancer._close()
            if self._vad_hub is not None:
                self._vad_hub.close(vad_lease)
        return ws

    def _push(
        self,
        stream: stt.RecognizeStream,
        enhancer: object | None,
        chunk: bytes,
        vad_scorer: AicVadScorer | None,
        vad_lease: tuple[tuple[str, str], object] | None,
    ) -> AicVadScorer | None:
        frame = rtc.AudioFrame(
            data=chunk,
            sample_rate=SAMPLE_RATE,
            num_channels=1,
            samples_per_channel=_FRAME_SAMPLES,
        )
        if vad_scorer is not None:
            try:
                probability = vad_scorer.push(np.frombuffer(chunk, dtype=np.int16))
                if self._vad_hub is not None:
                    self._vad_hub.publish(
                        vad_lease,
                        probability,
                        vad_scorer.prediction_delay_samples,
                    )
            except Exception:
                logger.exception(
                    "Voice Focus VAD failed; continuing STT without its score"
                )
                vad_scorer = None
        if enhancer is not None:
            frame = enhancer._process(frame)
            # The ai-coustics LiveKit plugin can silently pass raw audio when
            # authorization or model initialization fails. Never label that as
            # enhanced audio and continue the ASR comparison.
            if not enhancer.enabled or "lk.aic-vad" not in frame.userdata:
                raise RuntimeError("ai-coustics enhancement unavailable")
        stream.push_frame(frame)
        return vad_scorer

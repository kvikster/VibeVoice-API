"""Local stand-in for LiveKit Cloud's adaptive interruption ("bargein") service.

``livekit.agents.inference.AdaptiveInterruptionDetector`` (livekit-agents 1.8.3)
connects to ``{LIVEKIT_INFERENCE_URL}/bargein`` over WebSocket:

    client -> {"type": "session.create", "settings": {sample_rate, num_channels,
               threshold?, min_frames, encoding: "s16le"}}
    server -> {"type": "session.created", "default_threshold": float}
    client -> binary: 8-byte little-endian created_at (perf_counter_ns) + int16 PCM
              (the whole analysis window, re-sent every ~100 ms of new audio)
    server -> {"type": "bargein_detected" | "inference_done", "created_at",
               "prediction_duration", "probabilities": [...per 25 ms frame]}
    client -> {"type": "session.close"}      server -> {"type": "session.closed"}

This protocol is private and undocumented. The message models are imported
from livekit-agents itself, so a protocol change surfaces as an import or
validation error rather than as silent misbehaviour. Pin livekit-agents.

Every request must be answered within the client's ``inference_timeout``
(0.7 s by default). Otherwise the client raises a non-retryable error and the
session falls back to plain VAD interruptions. Hence decisions never wait for
ASR or MaAI; both run in the background and feed later decisions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import time
import uuid
from collections.abc import Callable

import numpy as np
from aiohttp import WSMsgType, web

from livekit import api
from livekit.agents.inference.interruption import (
    InterruptionWSDetectedMessage,
    InterruptionWSErrorMessage,
    InterruptionWSInferenceDoneMessage,
    InterruptionWSSessionClosedMessage,
    InterruptionWSSessionCreatedMessage,
    InterruptionWSSessionCreateMessage,
)

from ..backchannel.maai_detector import MaaiBackchannelDetector
from ..backchannel.policy import MaaiReading
from ..jsonl import JsonlWriter
from .classifier import (
    SAMPLE_RATE,
    BargeinClassifier,
    ClassifierConfig,
    Decision,
    OverlapState,
    new_tail,
    probabilities,
)
from .transcriber import RivaTranscriber
from .stt_route import GatewaySTTRoute
from .aic_vad import AicVadHub

logger = logging.getLogger("local_voice_agent.bargein")

_HEADER = struct.Struct("<Q")


class BargeinServer:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        transcriber: RivaTranscriber | None = None,
        maai_factory: Callable[[], MaaiBackchannelDetector] | None = None,
        classifier_config: ClassifierConfig | None = None,
        default_threshold: float = 0.5,
        decision_log: JsonlWriter | None = None,
        stt_route: GatewaySTTRoute | None = None,
        vad_hub: AicVadHub | None = None,
    ) -> None:
        self._verifier = api.TokenVerifier(api_key, api_secret) if api_key and api_secret else None
        self.transcriber = transcriber
        self.maai_factory = maai_factory
        self.classifier_config = classifier_config or ClassifierConfig()
        self.default_threshold = default_threshold
        self.decision_log = decision_log
        self.stt_route = stt_route
        self.vad_hub = vad_hub
        self._t0 = time.monotonic()

    def log_decision(self, record: dict) -> None:
        if self.decision_log is not None:
            self.decision_log.write({"t": round(time.monotonic() - self._t0, 4)} | record)

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/bargein", self._handle_ws)
        if self.stt_route is not None:
            app.router.add_get("/stt", self._handle_stt)
        app.router.add_get("/health", self._handle_health)
        return app

    async def _handle_health(self, _: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    async def _handle_ws(self, request: web.Request) -> web.StreamResponse:
        self._verify(request)

        ws = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)
        await ws.prepare(request)
        await _Session(self, ws, request.headers).run()
        return ws

    async def _handle_stt(self, request: web.Request) -> web.StreamResponse:
        self._verify(request)
        assert self.stt_route is not None
        return await self.stt_route.handle(request)

    def _verify(self, request: web.Request) -> None:
        if self._verifier is not None:
            token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            try:
                self._verifier.verify(token)
            except Exception:
                raise web.HTTPUnauthorized(text="invalid token") from None


class _Session:
    def __init__(self, server: BargeinServer, ws: web.WebSocketResponse, headers) -> None:
        self._server = server
        self._ws = ws
        self._id = uuid.uuid4().hex[:12]
        self._queue: asyncio.Queue[tuple[int, np.ndarray]] = asyncio.Queue()
        self._state = OverlapState()
        self._threshold = server.default_threshold
        self._maai: MaaiBackchannelDetector | None = None
        self._headers = headers
        self._classifier = BargeinClassifier(
            server.classifier_config,
            has_asr=server.transcriber is not None,
            has_maai=server.maai_factory is not None,
        )
        self._last_p = 0.0
        self._bg_tasks: set[asyncio.Task] = set()

    async def run(self) -> None:
        processor: asyncio.Task | None = None
        try:
            async for msg in self._ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "session.create":
                        if not await self._on_create(data):
                            return
                        processor = asyncio.create_task(self._process())
                    elif data.get("type") == "session.close":
                        await self._send(InterruptionWSSessionClosedMessage())
                        return
                elif msg.type == WSMsgType.BINARY:
                    if processor is None:
                        await self._error("audio before session.create", 400)
                        return
                    created_at = _HEADER.unpack_from(msg.data)[0]
                    pcm = np.frombuffer(msg.data, dtype=np.int16, offset=_HEADER.size)
                    self._queue.put_nowait((created_at, pcm))
                elif msg.type == WSMsgType.ERROR:
                    return
        finally:
            if processor is not None:
                processor.cancel()
            for task in self._bg_tasks:
                task.cancel()
            if self._maai is not None:
                await asyncio.to_thread(self._maai.close)

    async def _on_create(self, data: dict) -> bool:
        try:
            settings = InterruptionWSSessionCreateMessage.model_validate(data).settings
        except Exception as e:
            await self._error(f"invalid session.create: {e}", 400)
            return False
        if settings.sample_rate != SAMPLE_RATE or settings.num_channels != 1 or settings.encoding != "s16le":
            await self._error("only 16 kHz mono s16le audio is supported", 400)
            return False
        if settings.threshold is not None:
            self._threshold = settings.threshold
        await self._send(
            InterruptionWSSessionCreatedMessage(default_threshold=self._server.default_threshold)
        )
        logger.info("session %s created (threshold=%.2f)", self._id, self._threshold)
        if self._server.maai_factory is not None:
            # Loading can take seconds; never hold up replies for it.
            task = asyncio.create_task(self._load_maai())
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
        return True

    async def _load_maai(self) -> None:
        assert self._server.maai_factory is not None
        try:
            self._maai = await asyncio.to_thread(self._server.maai_factory)
        except Exception:
            logger.exception("session %s: MaAI failed to load, continuing without it", self._id)

    async def _process(self) -> None:
        while True:
            created_at, pcm = await self._queue.get()
            # Answer superseded windows right away; only the newest is analysed.
            while not self._queue.empty():
                superseded = Decision(False, self._last_p, "superseded", "superseded")
                await self._reply(created_at, len(pcm), superseded, 0.0)
                created_at, pcm = self._queue.get_nowait()
            t0 = time.perf_counter()
            decision = self._analyse(created_at, pcm)
            await self._reply(created_at, len(pcm), decision, time.perf_counter() - t0)

    def _analyse(self, created_at: int, pcm: np.ndarray) -> Decision:
        state = self._state
        if self._classifier.is_new_overlap(state, created_at):
            state = self._state = OverlapState(first_created_at=created_at)
            if self._maai is not None:
                self._maai.reset()

        tail, _ = new_tail(state.prev_window, pcm)
        state.prev_window = pcm
        state.last_created_at = created_at
        if self._maai is not None and len(tail):
            self._maai.push_user_samples(tail.astype(np.float32) / 32768.0)
        vad_reading = self._server.vad_hub.read(self._headers) if self._server.vad_hub else None

        elapsed = state.elapsed_s(created_at)
        if self._classifier.wants_transcript(state, created_at):
            n = min(len(pcm), int((elapsed + 0.3) * SAMPLE_RATE))
            self._spawn_transcription(state, pcm[-n:].copy(), elapsed)

        if self._maai is not None:
            reading = self._maai.reading(min(elapsed + 0.2, 3.0))
        elif self._server.maai_factory is not None:
            reading = MaaiReading(status="unavailable", note="model still loading")
        else:
            reading = MaaiReading(status="unavailable")
        return self._classifier.decide(
            state, created_at, reading.p_bc, maai_reading=reading,
            vf_vad_p=vad_reading.probability if vad_reading is not None else None,
            vf_vad_delay_samples=(
                vad_reading.prediction_delay_samples if vad_reading is not None else None
            ),
            vf_vad_age_s=vad_reading.age_s if vad_reading is not None else None,
        )

    def _spawn_transcription(self, state: OverlapState, snippet: np.ndarray, elapsed: float) -> None:
        transcriber = self._server.transcriber
        assert transcriber is not None
        state.transcribing = True
        if state.transcript is None:
            state.asr_status = "pending"

        async def run() -> None:
            try:
                result = await transcriber.transcribe(snippet)
                state.asr_status = result.status
                state.asr_error = result.error
                if result.status in ("received", "empty"):
                    state.transcript = result.text or state.transcript
                    state.transcript_len_s = elapsed
            finally:
                state.transcribing = False

        task = asyncio.create_task(run())
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _reply(self, created_at: int, n_samples: int, d: Decision, took: float) -> None:
        is_interruption = d.is_interruption and d.probability >= self._threshold
        self._last_p = d.probability
        cls = InterruptionWSDetectedMessage if is_interruption else InterruptionWSInferenceDoneMessage
        await self._send(
            cls(
                created_at=created_at,
                prediction_duration=took,
                probabilities=probabilities(d.probability, n_samples),
            )
        )
        if d.code != "superseded":
            log = logger.info if is_interruption else logger.debug
            log("session %s: %s (%s)", self._id, "BARGE-IN" if is_interruption else "hold", d.reason)
            self._server.log_decision(
                {
                    "kind": "decision",
                    "policy": "interruption_classifier",
                    "mode": "enforce",
                    "session": self._id,
                    "created_at": created_at,
                    "decision": "interrupt" if is_interruption else d.outcome,
                    "reply": cls.__name__,
                    "reason": d.code,
                    "detail": d.reason,
                    "probability": d.probability,
                    "threshold": self._threshold,
                    "prediction_duration_s": round(took, 6),
                    "signals": d.signals,
                    "thresholds": self._classifier.thresholds(),
                }
            )

    async def _error(self, message: str, code: int) -> None:
        await self._send(InterruptionWSErrorMessage(message=message, code=code, session_id=self._id))
        await self._ws.close()

    async def _send(self, msg) -> None:
        if not self._ws.closed:
            await self._ws.send_str(msg.model_dump_json())

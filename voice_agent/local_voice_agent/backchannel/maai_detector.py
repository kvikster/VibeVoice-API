"""MaAI ``bc_det`` backchannel detector fed from LiveKit audio frames.

MaAI (https://github.com/maai-kyoto/maai, MIT code) detects whether the
utterance a speaker is producing *right now* is a backchannel. The two-channel
model (``bc_det``) looks at the user and the agent together; the mono model
(``bc_det_mono``) only needs the user channel and is less accurate.

MaAI's own worker thread expects two synchronous audio sources. Instead we call
``Maai.process`` from our own thread with aligned 80 ms chunks (one model frame
at 12.5 Hz), clocked by the user's audio. Agent audio from ``tts_node`` is
produced faster than real time, so it is buffered and drained at the same rate,
which approximates what the user hears.

Model weights are downloaded from Hugging Face on first use. Check the model
card's licence before shipping.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from collections.abc import Callable

import numpy as np

from livekit import rtc

from .policy import MaaiReading

logger = logging.getLogger("local_voice_agent.maai")

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80 ms, one bc_det frame at 12.5 Hz
CLOCK = "maai_user_audio_s"  # seconds of user audio fed to MaAI
_MAX_AGENT_BUFFER_S = 30.0


class _Resampler:
    """Mono float32 @16 kHz from arbitrary LiveKit frames."""

    def __init__(self) -> None:
        self._rs: rtc.AudioResampler | None = None
        self._rate: int | None = None

    def __call__(self, frame: rtc.AudioFrame) -> np.ndarray:
        data = np.frombuffer(frame.data, dtype=np.int16)
        if frame.num_channels > 1:
            data = data.reshape(-1, frame.num_channels).mean(axis=1).astype(np.int16)
        if frame.sample_rate == SAMPLE_RATE:
            return data.astype(np.float32) / 32768.0
        if self._rs is None or self._rate != frame.sample_rate:
            self._rs = rtc.AudioResampler(frame.sample_rate, SAMPLE_RATE, num_channels=1)
            self._rate = frame.sample_rate
        mono = rtc.AudioFrame(
            data=data.tobytes(),
            sample_rate=frame.sample_rate,
            num_channels=1,
            samples_per_channel=len(data),
        )
        out = [np.frombuffer(f.data, dtype=np.int16) for f in self._rs.push(mono)]
        if not out:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(out).astype(np.float32) / 32768.0


class MaaiBackchannelDetector:
    """Background MaAI inference with a queryable history of user ``p_bc_det``."""

    def __init__(
        self,
        *,
        two_channel: bool = True,
        device: str = "cpu",
        lang: str = "en",
        history_s: float = 10.0,
        on_frame: Callable[[float, float], None] | None = None,
        realtime: bool = True,
    ) -> None:
        """``on_frame(t, p_bc)`` is called from the inference thread for every frame.
        ``realtime=False`` (offline scoring) makes pushes wait instead of dropping frames."""
        from maai import Maai, MaaiInput  # heavy import, optional dependency

        self._on_frame = on_frame
        self._realtime = realtime
        self._two_channel = two_channel
        self._maai = Maai(
            mode="bc_det" if two_channel else "bc_det_mono",
            lang=lang,
            frame_rate=12.5,
            audio_ch1=MaaiInput.Chunk(),
            audio_ch2=MaaiInput.Chunk(),
            device=device,
            model_type="normal-ver2",
            use_mimi_onnx=True,
        )
        self._user_rs = _Resampler()
        self._agent_rs = _Resampler()
        self._user_buf = np.zeros(0, dtype=np.float32)
        self._agent_buf = np.zeros(0, dtype=np.float32)
        self._lock = threading.Lock()
        self._clock_s = 0.0  # seconds of user audio fed so far
        self._history: deque[tuple[float, float]] = deque(maxlen=int(history_s * 12.5))
        self._gen = 0  # bumped by reset() so in-flight results from before it are discarded
        self._jobs: queue.Queue[tuple[int, float, np.ndarray, np.ndarray] | str | None] = (
            queue.Queue(maxsize=64)
        )
        self._thread = threading.Thread(target=self._worker, name="maai-bc-det", daemon=True)
        self._thread.start()

    # -- audio input -------------------------------------------------------
    def push_user(self, frame: rtc.AudioFrame) -> None:
        self.push_user_samples(self._user_rs(frame))

    def push_user_samples(self, samples: np.ndarray) -> None:
        """Mono float32 user audio at 16 kHz."""
        jobs = []
        with self._lock:
            self._user_buf = np.concatenate([self._user_buf, samples])
            while len(self._user_buf) >= FRAME_SAMPLES:
                user = self._user_buf[:FRAME_SAMPLES]
                self._user_buf = self._user_buf[FRAME_SAMPLES:]
                agent = self._agent_buf[:FRAME_SAMPLES]
                self._agent_buf = self._agent_buf[len(agent) :]
                if len(agent) < FRAME_SAMPLES:
                    agent = np.pad(agent, (0, FRAME_SAMPLES - len(agent)))
                self._clock_s += FRAME_SAMPLES / SAMPLE_RATE
                jobs.append((self._gen, self._clock_s, user, agent))
        for job in jobs:  # outside the lock: the worker takes it too
            if not self._realtime:
                self._jobs.put(job)
                continue
            try:
                self._jobs.put_nowait(job)
            except queue.Full:
                logger.warning("MaAI is falling behind real time; dropping a frame")

    def push_agent(self, frame: rtc.AudioFrame) -> None:
        self.push_agent_samples(self._agent_rs(frame))

    def push_agent_samples(self, samples: np.ndarray) -> None:
        """Mono float32 agent audio at 16 kHz, aligned to the user audio clock."""
        if not self._two_channel:
            return
        with self._lock:
            self._agent_buf = np.concatenate([self._agent_buf, samples])
            max_len = int(_MAX_AGENT_BUFFER_S * SAMPLE_RATE)
            if len(self._agent_buf) > max_len:
                self._agent_buf = self._agent_buf[-max_len:]

    def clear_agent(self) -> None:
        """Drop queued agent audio, e.g. after the agent was interrupted."""
        with self._lock:
            self._agent_buf = np.zeros(0, dtype=np.float32)

    # -- queries -----------------------------------------------------------
    def recent_max(self, window_s: float) -> float:
        """Highest user backchannel probability over the last ``window_s`` seconds."""
        with self._lock:
            since = self._clock_s - window_s
            values = [p for t, p in self._history if t >= since]
        return max(values, default=0.0)

    def reading(self, window_s: float) -> MaaiReading:
        """Peak user backchannel probability over the last ``window_s`` of fed audio."""
        with self._lock:
            since = self._clock_s - window_s
            recent = [(t, p) for t, p in self._history if t >= since]
        if not recent:
            return MaaiReading(status="unavailable", window_s=window_s, clock=CLOCK, note="no frame in window")
        return MaaiReading(
            status="available",
            p_bc=round(max(p for _, p in recent), 4),
            evaluated_at=round(recent[-1][0], 3),
            window_s=window_s,
            clock=CLOCK,
        )

    def reset(self) -> None:
        """Forget all audio and model state, e.g. at the start of a new overlap."""
        with self._lock:
            self._user_buf = np.zeros(0, dtype=np.float32)
            self._agent_buf = np.zeros(0, dtype=np.float32)
            self._history.clear()
            self._gen += 1
        self._jobs.put("reset")

    def latest(self) -> float:
        with self._lock:
            return self._history[-1][1] if self._history else 0.0

    def wait_idle(self) -> None:
        """Block until every pushed frame has been scored."""
        self._jobs.join()

    def close(self) -> None:
        self._jobs.put(None)
        self._thread.join(timeout=2.0)

    # -- inference thread --------------------------------------------------
    def _worker(self) -> None:
        while (job := self._jobs.get()) is not None:
            try:
                self._run_job(job)
            finally:
                self._jobs.task_done()

    def _run_job(self, job: tuple[int, float, np.ndarray, np.ndarray] | str) -> None:
        if isinstance(job, str):  # "reset"
            self._maai.reset_runtime_state()
            return
        gen, t, user, agent = job
        try:
            self._maai.process(user, agent)
        except Exception:
            logger.exception("MaAI inference failed")
            return
        results = self._maai.result_dict_queue
        while True:
            try:
                res = results.get_nowait()
            except queue.Empty:
                break
            p = res.get("p_bc_det")
            if p is None:
                continue
            p_user = float(p[0] if isinstance(p, (list, tuple, np.ndarray)) else p)
            with self._lock:
                if gen != self._gen:
                    continue
                self._history.append((t, p_user))
            if self._on_frame is not None:
                self._on_frame(t, p_user)

"""Bounded speech-onset gate for an opt-in streaming ASR experiment."""

from __future__ import annotations

from collections import deque

import numpy as np
from livekit import rtc


class SpeechOnsetTrim:
    """Drop initial quiet frames, retaining a short lead-in before speech.

    The detector uses the audio that will reach ASR (after optional enhancement).
    It only trims at the start of a WebSocket stream; after onset, every frame
    passes through unchanged. This is deliberately separate from the correlated
    Voice Focus VAD used by the interruption classifier.
    """

    def __init__(
        self,
        *,
        threshold_dbfs: float = -50.0,
        preroll_ms: int = 160,
        frame_ms: int = 20,
    ) -> None:
        if not -90.0 <= threshold_dbfs <= -10.0:
            raise ValueError("speech onset threshold must be between -90 and -10 dBFS")
        if not 0 <= preroll_ms <= 500 or preroll_ms % frame_ms:
            raise ValueError("speech onset pre-roll must be 0-500 ms in whole frames")
        self._threshold_rms = 32768 * 10 ** (threshold_dbfs / 20)
        self._recent: deque[rtc.AudioFrame] = deque(maxlen=preroll_ms // frame_ms + 2)
        self._consecutive = 0
        self.started = False
        self.skipped_frames = 0

    def push(self, frame: rtc.AudioFrame) -> tuple[rtc.AudioFrame, ...]:
        if self.started:
            return (frame,)

        pcm = np.frombuffer(frame.data, dtype=np.int16).astype(np.float64)
        rms = float(np.sqrt(np.mean(pcm * pcm)))
        self._recent.append(frame)
        self.skipped_frames += 1
        self._consecutive = self._consecutive + 1 if rms >= self._threshold_rms else 0
        if self._consecutive < 2:
            return ()

        self.started = True
        buffered = tuple(self._recent)
        self.skipped_frames -= len(buffered)
        self._recent.clear()
        return buffered

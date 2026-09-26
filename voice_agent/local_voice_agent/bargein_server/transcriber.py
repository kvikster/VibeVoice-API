"""Offline transcription of short overlap snippets via NeMo-Speech.cpp riva_server."""

from __future__ import annotations

import asyncio
import logging

import numpy as np
import riva.client

logger = logging.getLogger("local_voice_agent.bargein.asr")


class RivaTranscriber:
    def __init__(self, server: str, *, timeout_s: float = 1.0) -> None:
        self._asr = riva.client.ASRService(riva.client.Auth(uri=server, use_ssl=False))
        self._timeout_s = timeout_s
        self._config = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=16000,
            language_code="en-US",
            max_alternatives=1,
            enable_automatic_punctuation=False,
            audio_channel_count=1,
        )

    def _recognize(self, pcm16: np.ndarray) -> str:
        response = self._asr.offline_recognize(pcm16.astype(np.int16).tobytes(), self._config)
        return " ".join(
            r.alternatives[0].transcript.strip() for r in response.results if r.alternatives
        ).strip()

    async def transcribe(self, pcm16: np.ndarray) -> str | None:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._recognize, pcm16), timeout=self._timeout_s
            )
        except Exception as e:  # timeout, gRPC error, server not up
            logger.warning("overlap transcription failed: %s", e)
            return None

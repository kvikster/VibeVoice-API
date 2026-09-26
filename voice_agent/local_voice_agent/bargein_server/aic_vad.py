"""Per-connection Quail Voice Focus VAD evidence on the gateway."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import time
from collections.abc import Mapping

import numpy as np

from ..aic import AicVadModel, configure_privacy
from ..settings import Settings


class AicVadFactory:
    def __init__(self, settings: Settings) -> None:
        if not settings.aic_license_key:
            raise ValueError(
                "gateway Voice Focus VAD requires AIC_LICENSE_KEY or AIC_SDK_LICENSE"
            )
        configure_privacy(settings.aic_telemetry)
        import aic_sdk as aic

        path = settings.aic_vad_model_path
        if path is None:
            Path(settings.aic_models_dir).mkdir(parents=True, exist_ok=True)
            path = aic.Model.download(settings.aic_vad_model, settings.aic_models_dir)
        self._model = aic.Model.from_file(str(path))
        self._key = settings.aic_license_key
        self._telemetry = settings.aic_telemetry

    def __call__(self) -> AicVadScorer:
        return AicVadScorer(
            AicVadModel(self._model, self._key, telemetry=self._telemetry)
        )


class AicVadScorer:
    def __init__(self, model: AicVadModel) -> None:
        self._model = model
        self._pending = np.empty(0, dtype=np.float32)
        self.probability: float | None = None
        self.prediction_delay_samples = model.prediction_delay_samples

    def reset(self) -> None:
        self._model.reset()
        self._pending = np.empty(0, dtype=np.float32)
        self.probability = None

    def push(self, pcm: np.ndarray) -> float | None:
        if not len(pcm):
            return self.probability
        samples = pcm.astype(np.float32) / 32768.0
        self._pending = np.concatenate((self._pending, samples))
        block = self._model.window_size_samples
        while len(self._pending) >= block:
            self.probability = self._model(self._pending[:block].copy())
            self._pending = self._pending[block:]
        return self.probability


@dataclass(frozen=True)
class VadReading:
    probability: float
    prediction_delay_samples: int
    age_s: float


class AicVadHub:
    """Correlate full-stream VAD with LiveKit's overlap requests by room/job."""

    def __init__(self, *, max_age_s: float = 0.5) -> None:
        self._max_age_s = max_age_s
        self._slots: dict[tuple[str, str], tuple[object, float | None, int, float]] = {}

    @staticmethod
    def _key(headers: Mapping[str, str]) -> tuple[str, str] | None:
        room = headers.get("X-LiveKit-Room-ID", "")
        job = headers.get("X-LiveKit-Job-ID", "")
        return (room, job) if room or job else None

    def start(
        self, headers: Mapping[str, str]
    ) -> tuple[tuple[str, str], object] | None:
        key = self._key(headers)
        if key is None:
            return None
        token = object()
        self._slots[key] = (token, None, 0, 0.0)
        return key, token

    def publish(
        self,
        lease: tuple[tuple[str, str], object] | None,
        probability: float | None,
        prediction_delay_samples: int,
    ) -> None:
        if lease is None or probability is None:
            return
        key, token = lease
        current = self._slots.get(key)
        if current is not None and current[0] is token:
            self._slots[key] = (
                token,
                probability,
                prediction_delay_samples,
                time.monotonic(),
            )

    def read(self, headers: Mapping[str, str]) -> VadReading | None:
        key = self._key(headers)
        current = self._slots.get(key) if key is not None else None
        if current is None or current[1] is None:
            return None
        age = time.monotonic() - current[3]
        if age > self._max_age_s:
            return None
        return VadReading(current[1], current[2], age)

    def close(self, lease: tuple[tuple[str, str], object] | None) -> None:
        if lease is None:
            return
        key, token = lease
        current = self._slots.get(key)
        if current is not None and current[0] is token:
            del self._slots[key]

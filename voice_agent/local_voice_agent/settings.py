"""Runtime configuration from environment variables (see ``.env.example``)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

InterruptionMode = Literal["filters", "shadow", "adaptive_local", "vad"]
_MODES = ("filters", "shadow", "adaptive_local", "vad")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: str | None = None) -> float | None:
    value = os.environ.get(name, default)
    return float(value) if value not in (None, "") else None


@dataclass(frozen=True)
class Settings:
    # NeMo-Speech.cpp riva_server (Riva-compatible gRPC, plaintext)
    riva_server: str = field(default_factory=lambda: _env("RIVA_SERVER", "127.0.0.1:50051"))
    max_speakers: int = field(default_factory=lambda: int(_env("ASR_MAX_SPEAKERS", "4")))
    suppress_background: bool = field(default_factory=lambda: _env_bool("SUPPRESS_BACKGROUND_SPEAKER", True))

    # Any OpenAI-compatible LLM (Ollama, LM Studio, llama.cpp server, vLLM, ...)
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "http://127.0.0.1:11434/v1"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "qwen3:8b"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", "local"))

    # Any OpenAI-compatible TTS; defaults to this repo's VibeVoice API server
    tts_base_url: str = field(default_factory=lambda: _env("TTS_BASE_URL", "http://127.0.0.1:8000/v1"))
    tts_model: str = field(default_factory=lambda: _env("TTS_MODEL", "vibevoice/VibeVoice-1.5B"))
    tts_voice: str = field(default_factory=lambda: _env("TTS_VOICE", "alloy"))
    tts_api_key: str = field(default_factory=lambda: _env("TTS_API_KEY", "local"))

    # Interruption handling: "filters" (option 1), "shadow" (plain LiveKit behaviour, option 1/2
    # decisions only logged), "adaptive_local" (option 2), "vad" (plain LiveKit)
    interruption_mode: InterruptionMode = field(
        default_factory=lambda: _env("INTERRUPTION_MODE", "filters")  # type: ignore[return-value]
    )
    # Replayable JSONL of agent states, STT events and policy decisions ("filters" and "shadow").
    # "{room}" and "{ts}" are substituted.
    decision_log: str | None = field(default_factory=lambda: os.environ.get("DECISION_LOG") or None)
    maai_enabled: bool = field(default_factory=lambda: _env_bool("MAAI_ENABLED", False))
    maai_device: str = field(default_factory=lambda: _env("MAAI_DEVICE", "cpu"))
    maai_threshold: float = field(default_factory=lambda: float(_env("MAAI_THRESHOLD", "0.45")))
    filter_grace_s: float = field(default_factory=lambda: float(_env("FILTER_GRACE_S", "1.0")))
    interim_min_words: int = field(default_factory=lambda: int(_env("INTERIM_MIN_WORDS", "3")))

    # VAD and audio enhancement (see aic.py). Orthogonal to INTERRUPTION_MODE.
    vad_backend: str = field(default_factory=lambda: _env("VAD_BACKEND", "silero"))
    audio_enhancement: str = field(default_factory=lambda: _env("AUDIO_ENHANCEMENT", "none"))
    aic_license_key: str | None = field(
        default_factory=lambda: os.environ.get("AIC_LICENSE_KEY") or os.environ.get("AIC_SDK_LICENSE") or None,
        repr=False,  # never print the key
    )
    aic_enhancer_model: str = field(default_factory=lambda: _env("AIC_ENHANCER_MODEL", "quail_vf_l"))
    aic_enhancement_level: float | None = field(default_factory=lambda: _env_float("AIC_ENHANCEMENT_LEVEL"))
    aic_enhancer_vad_hold_s: float | None = field(default_factory=lambda: _env_float("AIC_ENHANCER_VAD_HOLD_S", "0.55"))
    aic_vad_sensitivity: float | None = field(default_factory=lambda: _env_float("AIC_VAD_SENSITIVITY"))
    aic_vad_model: str = field(default_factory=lambda: _env("AIC_VAD_MODEL", "vad-2.1-xxs-16khz"))
    aic_vad_model_path: str | None = field(default_factory=lambda: os.environ.get("AIC_VAD_MODEL_PATH") or None)
    aic_models_dir: str = field(
        default_factory=lambda: _env("AIC_MODELS_DIR", os.path.expanduser("~/.cache/local-voice-agent/aic-models"))
    )
    aic_vad_threshold: float = field(default_factory=lambda: float(_env("AIC_VAD_THRESHOLD", "0.5")))
    aic_telemetry: bool = field(default_factory=lambda: _env_bool("AIC_TELEMETRY", False))

    def __post_init__(self) -> None:
        if self.interruption_mode not in _MODES:
            raise ValueError(f"INTERRUPTION_MODE must be one of {'|'.join(_MODES)}, got {self.interruption_mode!r}")
        if self.vad_backend not in ("silero", "aic", "aic_enhancer"):
            raise ValueError(f"VAD_BACKEND must be silero|aic|aic_enhancer, got {self.vad_backend!r}")
        if self.audio_enhancement not in ("none", "aic"):
            raise ValueError(f"AUDIO_ENHANCEMENT must be none|aic, got {self.audio_enhancement!r}")
        if self.vad_backend == "aic_enhancer" and self.audio_enhancement != "aic":
            raise ValueError("VAD_BACKEND=aic_enhancer reads the enhancer's VAD flag: set AUDIO_ENHANCEMENT=aic")

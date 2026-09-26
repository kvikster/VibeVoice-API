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

    def __post_init__(self) -> None:
        if self.interruption_mode not in _MODES:
            raise ValueError(f"INTERRUPTION_MODE must be one of {'|'.join(_MODES)}, got {self.interruption_mode!r}")

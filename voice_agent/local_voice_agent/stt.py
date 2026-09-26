"""STT: NeMo-Speech.cpp ``riva_server`` via ``livekit-plugins-nvidia``, plus diarization."""

from __future__ import annotations

from livekit.agents import stt
from livekit.plugins import nvidia
import os

from .settings import Settings


def build_stt(settings: Settings) -> stt.STT:
    if settings.stt_gateway_url:
        from .gateway_stt import GatewaySTT

        return GatewaySTT(
            url=settings.stt_gateway_url,
            api_key=os.environ.get("LIVEKIT_INFERENCE_API_KEY", ""),
            api_secret=os.environ.get("LIVEKIT_INFERENCE_API_SECRET", ""),
        )
    return build_direct_stt(settings)


def build_direct_stt(settings: Settings) -> stt.STT:
    """Gateway-side Riva STT, regardless of the agent's gateway setting."""
    asr = build_raw_stt(settings)
    # Speaker tags arrive on final transcripts only; the adapter keeps the
    # loudest consistent speaker as primary and drops the others' finals.
    return stt.MultiSpeakerAdapter(
        stt=asr,
        detect_primary_speaker=True,
        suppress_background_speaker=settings.suppress_background,
    )


def build_raw_stt(settings: Settings) -> stt.STT:
    return nvidia.STT(
        server=settings.riva_server,
        use_ssl=False,
        # riva_server serves whatever model it was started with and ignores this
        # name; "sortformer" in it only silences the plugin's diarization warning.
        model="nemotron-speech-en-sortformer",
        language_code="en-US",
        punctuate=True,
        enable_diarization=True,
        max_speaker_count=settings.max_speakers,
    )

"""STT: NeMo-Speech.cpp ``riva_server`` via ``livekit-plugins-nvidia``, plus diarization."""

from __future__ import annotations

from livekit.agents import stt
from livekit.plugins import nvidia

from .settings import Settings


def build_stt(settings: Settings) -> stt.STT:
    asr = nvidia.STT(
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
    # Speaker tags arrive on final transcripts only; the adapter keeps the
    # loudest consistent speaker as primary and drops the others' finals.
    return stt.MultiSpeakerAdapter(
        stt=asr,
        detect_primary_speaker=True,
        suppress_background_speaker=settings.suppress_background,
    )

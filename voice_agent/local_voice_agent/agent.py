"""Self-hosted English voice agent.

    STT  NeMo-Speech.cpp riva_server (Nemotron-Speech EN + Sortformer) -> MultiSpeakerAdapter
    LLM  any OpenAI-compatible server (Ollama by default)
    TTS  any OpenAI-compatible server (this repo's VibeVoice API by default)

INTERRUPTION_MODE selects how the agent treats user speech that overlaps its own:

    filters         option 1: lexicon + interim hold (+ optional MaAI) in stt_node
    adaptive_local  option 2: LiveKit's adaptive interruption against the local bargein server
    vad             LiveKit defaults, for A/B comparison

Run:  python -m local_voice_agent.agent console   (local mic/speaker, no LiveKit server)
      python -m local_voice_agent.agent dev       (connects to LIVEKIT_URL)
"""

from __future__ import annotations

import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    TurnHandlingOptions,
    cli,
    inference,
    metrics,
)
from livekit.plugins import openai, silero

from .backchannel.filter import FilterConfig, InterruptionFilterMixin
from .settings import Settings
from .stt import build_stt

logger = logging.getLogger("local_voice_agent")

load_dotenv()

INSTRUCTIONS = (
    "You are a helpful voice assistant. You speak English with the user over voice, "
    "so keep answers short and conversational, and never use emojis, markdown or lists."
)


class VoiceAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=INSTRUCTIONS)

    async def on_enter(self) -> None:
        self.session.generate_reply(instructions="Greet the user briefly.")


class FilteredVoiceAgent(InterruptionFilterMixin, VoiceAgent):
    def __init__(self, settings: Settings, maai=None) -> None:
        super().__init__()
        self.filter_config = FilterConfig(
            grace_s=settings.filter_grace_s,
            interim_min_words=settings.interim_min_words,
            maai_threshold=settings.maai_threshold,
        )
        self.maai = maai


def turn_handling_for(settings: Settings) -> TurnHandlingOptions:
    # The local v1-mini audio end-of-turn model; "v1" would call LiveKit Cloud.
    turn_detection = inference.TurnDetector(version="v1-mini")
    if settings.interruption_mode == "filters":
        interruption = {
            "mode": "vad",
            # With min_words >= 1, VAD alone (noise, coughs, laughter) can't pause
            # the agent: an interruption needs a transcript word, and the filter
            # decides which transcripts get through.
            "min_words": 1,
            "resume_false_interruption": True,
        }
    elif settings.interruption_mode == "adaptive_local":
        # AdaptiveInterruptionDetector reads LIVEKIT_INFERENCE_URL /
        # LIVEKIT_INFERENCE_API_KEY / LIVEKIT_INFERENCE_API_SECRET.
        interruption = {"mode": "adaptive", "resume_false_interruption": True}
    else:
        interruption = {"mode": "vad", "resume_false_interruption": True}
    return TurnHandlingOptions(turn_detection=turn_detection, interruption=interruption)


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    settings = Settings()
    proc.userdata["settings"] = settings
    proc.userdata["vad"] = silero.VAD.load()
    proc.userdata["maai"] = None
    if settings.interruption_mode == "filters" and settings.maai_enabled:
        from .backchannel.maai_detector import MaaiBackchannelDetector

        proc.userdata["maai"] = MaaiBackchannelDetector(device=settings.maai_device)


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    settings: Settings = ctx.proc.userdata["settings"]
    ctx.log_context_fields = {"room": ctx.room.name, "interruption_mode": settings.interruption_mode}

    session = AgentSession(
        stt=build_stt(settings),
        vad=ctx.proc.userdata["vad"],
        llm=openai.LLM(
            base_url=settings.llm_base_url, model=settings.llm_model, api_key=settings.llm_api_key
        ),
        tts=openai.TTS(
            base_url=settings.tts_base_url,
            model=settings.tts_model,
            voice=settings.tts_voice,
            api_key=settings.tts_api_key,
            response_format="pcm",  # 24 kHz s16le, VibeVoice's native rate
        ),
        turn_handling=turn_handling_for(settings),
    )

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent) -> None:
        metrics.log_metrics(ev.metrics)

    if settings.interruption_mode == "filters":
        agent: Agent = FilteredVoiceAgent(settings, maai=ctx.proc.userdata["maai"])
    else:
        agent = VoiceAgent()

    await session.start(agent=agent, room=ctx.room)


def main() -> None:
    cli.run_app(server)


if __name__ == "__main__":
    main()

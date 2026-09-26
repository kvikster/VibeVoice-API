"""Probe the installed gateway and Riva protocol, optionally recognizing a WAV."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.request
import wave

import grpc
from livekit import rtc
from livekit.agents import stt
from local_voice_agent.gateway_stt import GatewaySTT
from riva.client.proto import riva_asr_pb2 as asr
from riva.client.proto import riva_asr_pb2_grpc as asr_grpc
from riva.client.proto import riva_audio_pb2 as audio


async def check_gateway_stt(gateway: str, pcm: bytes) -> list[str]:
    if gateway.startswith("http://"):
        ws_url = "ws://" + gateway.removeprefix("http://")
    elif gateway.startswith("https://"):
        ws_url = "wss://" + gateway.removeprefix("https://")
    else:
        raise SystemExit("--gateway must start with http:// or https://")
    client = GatewaySTT(
        url=f"{ws_url.rstrip('/')}/stt",
        api_key=os.environ.get("LIVEKIT_INFERENCE_API_KEY", "devkey"),
        api_secret=os.environ.get(
            "LIVEKIT_INFERENCE_API_SECRET", "devsecret-devsecret-devsecret-00"
        ),
    )
    stream = client.stream()
    for offset in range(0, len(pcm), 640):
        chunk = pcm[offset : offset + 640].ljust(640, b"\0")
        stream.push_frame(
            rtc.AudioFrame(
                data=chunk,
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=320,
            )
        )
    stream.end_input()
    try:
        events = [event async for event in stream]
    finally:
        await stream.aclose()
    finals = [
        event.alternatives[0]
        for event in events
        if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT
        and event.alternatives
        and event.alternatives[0].text.strip()
    ]
    if not finals:
        raise SystemExit("gateway /stt returned no final transcript")
    return sorted({event.speaker_id for event in finals if event.speaker_id})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--riva", default="127.0.0.1:50051")
    parser.add_argument("--gateway", default="http://127.0.0.1:8765")
    parser.add_argument(
        "--wav", help="16-kHz, 16-bit mono WAV containing audible speech"
    )
    args = parser.parse_args()

    with urllib.request.urlopen(f"{args.gateway}/health", timeout=10) as response:
        health = json.load(response)
    if not health.get("ok"):
        raise SystemExit(f"gateway health failed: {health}")

    with grpc.insecure_channel(args.riva) as channel:
        grpc.channel_ready_future(channel).result(timeout=30)
        stub = asr_grpc.RivaSpeechRecognitionStub(channel)
        config = stub.GetRivaSpeechRecognitionConfig(
            asr.RivaSpeechRecognitionConfigRequest(), timeout=30
        )
        if not config.model_config:
            raise SystemExit("Riva returned no ASR model")

        result: dict[str, object] = {
            "gateway_ok": True,
            "riva_ok": True,
            "models": [model.model_name for model in config.model_config],
        }
        if args.wav:
            with wave.open(args.wav, "rb") as wav:
                if (
                    wav.getnchannels() != 1
                    or wav.getsampwidth() != 2
                    or wav.getframerate() != 16000
                ):
                    raise SystemExit("--wav must be 16-kHz, 16-bit mono PCM")
                rate = wav.getframerate()
                pcm = wav.readframes(wav.getnframes())
            request = asr.RecognizeRequest(
                config=asr.RecognitionConfig(
                    encoding=audio.LINEAR_PCM,
                    sample_rate_hertz=rate,
                    language_code="en-US",
                    enable_word_time_offsets=True,
                    diarization_config=asr.SpeakerDiarizationConfig(
                        enable_speaker_diarization=True,
                        max_speaker_count=4,
                    ),
                ),
                audio=pcm,
            )
            recognition = stub.Recognize(request, timeout=180)
            alternatives = [
                alternative
                for segment in recognition.results
                for alternative in segment.alternatives
            ]
            if not any(alternative.transcript.strip() for alternative in alternatives):
                raise SystemExit("Riva returned no transcript for the supplied speech")
            result["recognize_ok"] = True
            result["word_count"] = sum(len(alt.words) for alt in alternatives)
            result["speaker_ids"] = sorted(
                {word.speaker_tag for alt in alternatives for word in alt.words}
            )

    if args.wav:
        result["gateway_speaker_ids"] = asyncio.run(
            check_gateway_stt(args.gateway, pcm)
        )
        result["gateway_stt_ok"] = True

    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

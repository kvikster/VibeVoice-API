"""A scripted Riva-compatible gRPC ASR server, standing in for NeMo-Speech.cpp riva_server."""

from __future__ import annotations

import wave
from concurrent import futures
from dataclasses import dataclass, field
from pathlib import Path

import grpc
import numpy as np
from riva.client.proto import riva_asr_pb2 as pb
from riva.client.proto import riva_asr_pb2_grpc as pbg


def response(text: str, *, final: bool, words: list[tuple[str, int, int, int]] = ()) -> pb.StreamingRecognizeResponse:
    """words: (word, start_ms, end_ms, speaker_tag); tags only make sense on finals."""
    alt = pb.SpeechRecognitionAlternative(
        transcript=text,
        confidence=1.0,
        words=[pb.WordInfo(word=w, start_time=s, end_time=e, speaker_tag=tag) for w, s, e, tag in words],
    )
    return pb.StreamingRecognizeResponse(
        results=[pb.StreamingRecognitionResult(alternatives=[alt], is_final=final)]
    )


@dataclass
class Step:
    at_s: float  # emit once this much audio has been received
    response: pb.StreamingRecognizeResponse


@dataclass
class FakeRiva(pbg.RivaSpeechRecognitionServicer):
    script: list[Step]
    on_end: list[pb.StreamingRecognizeResponse] = field(default_factory=list)
    model_name: str = "fake-nemotron-en"
    configs: list = field(default_factory=list)
    received_s: float = 0.0
    received_peak: int = 0

    def GetRivaSpeechRecognitionConfig(self, request, context):
        return pb.RivaSpeechRecognitionConfigResponse(
            model_config=[
                pb.RivaSpeechRecognitionConfigResponse.Config(
                    model_name=self.model_name, parameters={"streaming": "true"}
                )
            ]
        )

    def StreamingRecognize(self, request_iterator, context):
        rate, samples = 16000, 0
        steps = list(self.script)
        for req in request_iterator:
            if req.HasField("streaming_config"):
                self.configs.append(req.streaming_config)
                rate = req.streaming_config.config.sample_rate_hertz or rate
                continue
            samples += len(req.audio_content) // 2
            if req.audio_content:
                self.received_peak = max(
                    self.received_peak,
                    int(np.max(np.abs(np.frombuffer(req.audio_content, dtype=np.int16).astype(np.int32)))),
                )
            self.received_s = samples / rate
            while steps and self.received_s >= steps[0].at_s:
                yield steps.pop(0).response
        # client closed its side: flush what is left, like a real server finalizing
        for step in steps:
            yield step.response
        yield from self.on_end


def serve(servicer: FakeRiva) -> tuple[grpc.Server, str]:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    pbg.add_RivaSpeechRecognitionServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    return server, f"127.0.0.1:{port}"


def write_wav(path: Path, segments: list[tuple[float, float, float]], *, duration_s: float, rate: int = 16000) -> Path:
    """segments: (start_s, end_s, amplitude 0..1) of a 220 Hz tone on silence."""
    audio = np.zeros(int(duration_s * rate), dtype=np.float32)
    t = np.arange(len(audio)) / rate
    for start, end, amp in segments:
        mask = (t >= start) & (t < end)
        audio[mask] = amp * np.sin(2 * np.pi * 220 * t[mask])
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())
    return path

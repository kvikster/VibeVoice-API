"""Replay one WAV through the streaming STT and log every event before and after
speaker suppression, from a single recognition pass.

    python -m local_voice_agent.tools.replay_stt caller.wav --out runs/caller.stt.jsonl

The STT is exactly what the agent uses (``stt.build_stt``): livekit-plugins-nvidia
-> NeMo-Speech.cpp riva_server, wrapped in ``MultiSpeakerAdapter``. No LiveKit
room, LLM or TTS is involved. Audio is pushed at real-time pace by default.

Each STT event becomes one JSONL record (``kind: "stt"``):

* ``layer: "raw"``     - event as it reaches MultiSpeakerAdapter, plus the
  adapter's verdict (``adapter_action``: passed / modified / dropped) and the
  primary speaker after the adapter saw it;
* ``layer: "adapter"`` - event as the agent would receive it, linked to its raw
  event by ``source_seq``.

Common fields: ``seq``, ``t`` (monotonic seconds since the run started, at
receipt), ``audio_pos_samples`` / ``audio_pos_s`` (audio pushed so far),
``type`` (interim / final / start_of_speech / end_of_speech), and when the STT
provides them ``text``, ``speaker_id``, ``start_time_s``/``end_time_s``,
``words`` and ``word_speaker_tags``. Missing data is omitted, never faked.

``--enhance aic`` runs the ai-coustics enhancer on each frame before the STT, the
way ``AUDIO_ENHANCEMENT=aic`` does on room input (needs ``AIC_LICENSE_KEY``).

Run metadata (SDK versions, STT options, server model config, ASR config file,
WAV fingerprint, summary) goes to a sidecar ``*.meta.json``.

Note: this hooks two private livekit-agents 1.8.3 internals
(``MultiSpeakerAdapterWrapper._detector`` and the NVIDIA stream's
``_convert_to_speech_data``) to observe, not alter, the data flow.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
import time
import wave
from collections import Counter, deque
from pathlib import Path
from typing import Any

import numpy as np
import riva.client
from riva.client.proto import riva_asr_pb2, riva_asr_pb2_grpc

from livekit import rtc
from livekit.agents import stt

from .. import aic
from ..jsonl import JsonlWriter, event_fields
from ..settings import Settings
from ..stt import build_stt
from . import meta as run_meta


def load_wav(path: str | Path) -> tuple[np.ndarray, int, int]:
    """Mono int16 samples, sample rate, channel count in the file."""
    with wave.open(str(path), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise SystemExit(
                f"{path}: only 16-bit PCM WAV is supported; convert with "
                "`ffmpeg -i in.wav -ac 1 -ar 16000 -sample_fmt s16 out.wav`"
            )
        channels, rate = wf.getnchannels(), wf.getframerate()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1).astype(np.int16)
    return data, rate, channels


def fetch_server_config(server: str, timeout_s: float = 3.0) -> dict[str, Any]:
    """Model config reported by riva_server, or why it is unavailable."""
    try:
        auth = riva.client.Auth(uri=server, use_ssl=False)
        stub = riva_asr_pb2_grpc.RivaSpeechRecognitionStub(auth.channel)
        resp = stub.GetRivaSpeechRecognitionConfig(
            riva_asr_pb2.RivaSpeechRecognitionConfigRequest(), timeout=timeout_s
        )
    except Exception as e:  # grpc.RpcError and friends
        code = e.code() if hasattr(e, "code") else None
        details = e.details() if hasattr(e, "details") else str(e)
        return {"unavailable": f"{getattr(code, 'name', type(e).__name__)}: {details}"}
    return {
        "models": [
            {"model_name": m.model_name, "parameters": dict(m.parameters)} for m in resp.model_config
        ]
    }


def _capture_word_speakers(inner: stt.STT, sink: dict[int, list[int]]) -> None:
    """Keep Riva's per-word speaker tags, which the plugin reduces to one majority label."""
    original_stream = inner.stream

    def stream(*args: Any, **kwargs: Any) -> stt.RecognizeStream:
        s = original_stream(*args, **kwargs)
        convert = s._convert_to_speech_data  # type: ignore[attr-defined]

        def convert_and_keep(alternative: Any, *, is_final: bool) -> stt.SpeechData:
            sd = convert(alternative, is_final=is_final)
            tags = [int(getattr(w, "speaker_tag", 0)) for w in getattr(alternative, "words", [])]
            if any(tags):
                sink[id(sd)] = tags
            return sd

        s._convert_to_speech_data = convert_and_keep  # type: ignore[attr-defined]
        return s

    inner.stream = stream  # type: ignore[method-assign]


@dataclasses.dataclass
class ReplayConfig:
    wav: Path
    out: Path
    settings: Settings
    speed: float = 1.0
    frame_ms: int = 20
    tail_silence_s: float = 1.0
    drain_timeout_s: float = 30.0
    asr_config: Path | None = None
    server_check: bool = True
    enhancer: Any = None
    """Optional FrameProcessor applied before the STT (``--enhance aic``), as room input does."""


def meta_path_for(out: Path) -> Path:
    return out.with_name(out.name.removesuffix(".jsonl") + ".meta.json")


async def replay(cfg: ReplayConfig) -> dict[str, Any]:
    audio, rate, file_channels = load_wav(cfg.wav)
    server_config = fetch_server_config(cfg.settings.riva_server)
    if cfg.server_check and "UNAVAILABLE" in str(server_config.get("unavailable", "")):
        raise SystemExit(f"riva_server at {cfg.settings.riva_server} is not reachable: {server_config}")

    adapter = build_stt(cfg.settings)
    assert isinstance(adapter, stt.MultiSpeakerAdapter)
    inner = adapter.wrapped_stt
    word_tags: dict[int, list[int]] = {}
    _capture_word_speakers(inner, word_tags)

    writer = JsonlWriter(cfg.out)
    t0 = time.monotonic()
    fed = 0
    seq = 0
    # raw events the adapter will emit something for, in order: (seq, type, cleared)
    pending: deque[tuple[int, str, bool]] = deque()
    counts: Counter[str] = Counter()
    primary_switches: list[dict[str, Any]] = []

    def base(layer: str) -> dict[str, Any]:
        nonlocal seq
        seq += 1
        return {
            "kind": "stt",
            "layer": layer,
            "seq": seq,
            "t": round(time.monotonic() - t0, 4),
            "audio_pos_samples": fed,
            "audio_pos_s": round(fed / rate, 4),
        }

    stream = adapter.stream()
    detector = stream._detector  # type: ignore[attr-defined]
    on_stt_event = detector.on_stt_event

    def observe(ev: stt.SpeechEvent) -> stt.SpeechEvent | None:
        rec = base("raw") | event_fields(ev)
        if ev.alternatives and (tags := word_tags.pop(id(ev.alternatives[0]), None)):
            rec["word_speaker_tags"] = [f"S{t}" if t > 0 else None for t in tags]
        text_before = ev.alternatives[0].text if ev.alternatives else None
        primary_before = detector._primary_speaker
        out = on_stt_event(ev)
        primary_after = detector._primary_speaker
        if out is None:
            action = "dropped"
        elif out.alternatives and out.alternatives[0].text != text_before:
            action = "modified"
        else:
            action = "passed"
        rec["adapter_action"] = action
        if primary_after is not None:
            rec["primary_speaker"] = primary_after
        if primary_before != primary_after:
            rec["primary_speaker_before"] = primary_before
            primary_switches.append({"seq": rec["seq"], "t": rec["t"], "from": primary_before, "to": primary_after})
        if out is not None and out.alternatives and out.alternatives[0].is_primary_speaker is not None:
            rec["is_primary_speaker"] = out.alternatives[0].is_primary_speaker
        counts[f"raw.{rec['type']}.{action}"] += 1
        writer.write(rec)
        if out is not None:
            pending.append((rec["seq"], rec["type"], False))
        elif ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
            pending.append((rec["seq"], "final", True))  # adapter sends an empty final instead
        return out

    detector.on_stt_event = observe

    async def consume() -> None:
        async for ev in stream:
            rec = base("adapter") | event_fields(ev)
            if pending and pending[0][1] == rec["type"]:
                src, _, cleared = pending.popleft()
                rec["source_seq"] = src
                if cleared:
                    rec["cleared_suppressed_final"] = True
            if detector._primary_speaker is not None:
                rec["primary_speaker"] = detector._primary_speaker
            counts[f"adapter.{rec['type']}"] += 1
            writer.write(rec)

    async def feed() -> None:
        nonlocal fed
        frame = max(1, int(rate * cfg.frame_ms / 1000))
        samples = np.concatenate([audio, np.zeros(int(rate * cfg.tail_silence_s), dtype=np.int16)])
        start = time.monotonic()
        for i in range(0, len(samples), frame):
            delay = start + (i / rate) / cfg.speed - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            chunk = samples[i : i + frame]
            if len(chunk) < frame:  # enhancers want a constant frame size
                chunk = np.pad(chunk, (0, frame - len(chunk)))
            audio_frame = rtc.AudioFrame(
                data=chunk.tobytes(), sample_rate=rate, num_channels=1, samples_per_channel=len(chunk)
            )
            if cfg.enhancer is not None:
                audio_frame = aic.enhance(cfg.enhancer, audio_frame)
            stream.push_frame(audio_frame)
            fed = i + len(chunk)
        stream.end_input()  # flush: riva_server finalizes and returns the last finals

    consumer = asyncio.create_task(consume())
    drained = True
    try:
        await feed()
        try:
            await asyncio.wait_for(consumer, timeout=cfg.drain_timeout_s)
        except asyncio.TimeoutError:
            drained = False
    finally:
        consumer.cancel()
        await stream.aclose()
        writer.close()

    summary = {
        "events": dict(sorted(counts.items())),
        "primary_speaker_switches": primary_switches,
        "drained": drained,
        "wall_time_s": round(time.monotonic() - t0, 3),
    }
    meta = {
        "tool": "local_voice_agent.tools.replay_stt",
        "started_at": run_meta.utc_now(),
        "events_file": str(cfg.out),
        "wav": {
            "path": str(cfg.wav),
            "sha256": run_meta.sha256(cfg.wav),
            "sample_rate": rate,
            "channels_in_file": file_channels,
            "duration_s": round(len(audio) / rate, 4),
        },
        "replay": {
            "speed": cfg.speed,
            "frame_ms": cfg.frame_ms,
            "tail_silence_s": cfg.tail_silence_s,
            "time_fields": {
                "t": "monotonic seconds since run start, at event receipt",
                "audio_pos_s": "seconds of audio pushed when the event was received (includes tail silence)",
            },
        },
        "stt_options": {k: str(v) if not isinstance(v, (bool, int, float)) else v
                        for k, v in dataclasses.asdict(inner._opts).items()  # type: ignore[attr-defined]
                        if k != "function_id"},
        "adapter_options": {
            "detect_primary_speaker": adapter._detect_primary,  # type: ignore[attr-defined]
            "suppress_background_speaker": adapter._suppress_background,  # type: ignore[attr-defined]
            "primary_detection": dataclasses.asdict(adapter._opt),  # type: ignore[attr-defined]
        },
        "enhancement": aic.enhancer_description(cfg.settings) if cfg.enhancer is not None else None,
        "server_config": server_config,
        "asr_config_file": _config_snapshot(cfg.asr_config),
        "versions": run_meta.versions(),
        "git": run_meta.git_revision(),
        "summary": summary,
    }
    meta_path_for(cfg.out).write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return meta


def _config_snapshot(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return {
        "path": str(path),
        "sha256": run_meta.sha256(path),
        "note": "file as passed to this tool; the running riva_server may use another config",
        "content": path.read_text(),
    }


def main(argv: list[str] | None = None) -> None:
    from dotenv import load_dotenv

    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wav", type=Path)
    p.add_argument("--out", type=Path, help="events JSONL (default: <wav stem>.stt.jsonl)")
    p.add_argument("--riva", help="riva_server host:port (default: RIVA_SERVER or 127.0.0.1:50051)")
    p.add_argument("--speed", type=float, default=1.0, help="1.0 = real time")
    p.add_argument("--frame-ms", type=int, default=20)
    p.add_argument("--tail-silence", type=float, default=1.0, help="seconds of silence after the WAV")
    p.add_argument("--drain-timeout", type=float, default=30.0)
    p.add_argument("--max-speakers", type=int)
    p.add_argument("--no-suppress", action="store_true", help="keep background finals (still detects primary)")
    p.add_argument("--asr-config", type=Path, default=Path(__file__).resolve().parents[2] / "config" / "asr.mac.yaml")
    p.add_argument("--no-server-check", action="store_true")
    p.add_argument(
        "--enhance", choices=["none", "aic"], help="ai-coustics enhancement before STT (default: AUDIO_ENHANCEMENT)"
    )
    args = p.parse_args(argv)

    settings = Settings()
    overrides: dict[str, Any] = {}
    if args.riva:
        overrides["riva_server"] = args.riva
    if args.max_speakers:
        overrides["max_speakers"] = args.max_speakers
    if args.no_suppress:
        overrides["suppress_background"] = False
    if args.enhance:
        overrides["audio_enhancement"] = args.enhance
    settings = dataclasses.replace(settings, **overrides)
    enhancer = aic.build_enhancer(settings) if settings.audio_enhancement == "aic" else None

    out = args.out or Path(args.wav.stem + ".stt.jsonl")
    meta = asyncio.run(
        replay(
            ReplayConfig(
                wav=args.wav,
                out=out,
                settings=settings,
                speed=args.speed,
                frame_ms=args.frame_ms,
                tail_silence_s=args.tail_silence,
                drain_timeout_s=args.drain_timeout,
                asr_config=args.asr_config,
                server_check=not args.no_server_check,
                enhancer=enhancer,
            )
        )
    )
    json.dump(meta["summary"], sys.stdout, indent=2)
    print(f"\nevents: {out}\nmeta:   {meta_path_for(out)}")


if __name__ == "__main__":
    main()

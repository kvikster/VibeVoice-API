"""Run a VAD over a WAV and write its timeline: probability per inference and speech events.

    python -m local_voice_agent.tools.vad_scores C_mix.wav --vad aic --out runs/C.vad.aic.jsonl
    python -m local_voice_agent.tools.vad_scores C_mix.wav --vad silero --out runs/C.vad.silero.jsonl
    python -m local_voice_agent.tools.vad_scores C_mix.wav --enhance aic --vad aic_enhancer ...

Same VAD objects as the agent (``aic.build_vad``), so ``silero`` and ``aic`` share
Silero's state machine and differ only in the model; ``--enhance aic`` puts the
ai-coustics enhancer in front, as ``AUDIO_ENHANCEMENT=aic`` does in a room.

Records (``kind: "vad"``, on the WAV clock):

* ``type: "inference"`` - ``p_speech`` (the model's speech probability; the
  ``aic_enhancer`` VAD only exposes a boolean, reported as ``speaking``) and
  ``speaking`` (the debounced state);
* ``type: "start_of_speech"`` / ``"end_of_speech"`` - with ``speech_duration_s`` /
  ``silence_duration_s``.

Useful on the A / B / C corpus: speech the VAD finds in B (background only) is a
false trigger; speech it misses in C (mix) against A is a lost caller turn.
Needs ``AIC_LICENSE_KEY`` for the ai-coustics backends.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import vad as lk_vad

from .. import aic
from ..jsonl import JsonlWriter
from ..settings import Settings
from . import meta as run_meta
from .replay_stt import load_wav

_TYPES = {
    lk_vad.VADEventType.START_OF_SPEECH: "start_of_speech",
    lk_vad.VADEventType.END_OF_SPEECH: "end_of_speech",
    lk_vad.VADEventType.INFERENCE_DONE: "inference",
}


async def score(
    wav: Path,
    out: Path,
    *,
    settings: Settings,
    vad: lk_vad.VAD | None = None,
    enhancer: Any = None,
    frame_ms: int = 10,
) -> dict[str, Any]:
    audio, rate, _ = load_wav(wav)
    vad = vad or aic.build_vad(settings)
    if enhancer is None and settings.audio_enhancement == "aic":
        enhancer = aic.build_enhancer(settings)
    stream = vad.stream()
    writer = JsonlWriter(out)
    counts: Counter[str] = Counter()
    # ai_coustics.VAD() only forwards the enhancer's boolean; its "probability" is a constant 1.0
    has_probability = not (vad.provider == "ai-coustics" and not isinstance(vad, aic.AicVAD))

    async def collect() -> None:
        async for ev in stream:
            kind = _TYPES.get(ev.type)
            if kind is None:
                continue
            t = round(ev.timestamp, 4)
            rec: dict[str, Any] = {"kind": "vad", "type": kind, "t": t, "audio_pos_s": t}
            if kind == "inference":
                if has_probability:
                    rec["p_speech"] = round(ev.probability, 4)
                rec["speaking"] = ev.speaking
            elif kind == "start_of_speech":
                rec["speech_duration_s"] = round(ev.speech_duration, 3)
            else:
                rec["silence_duration_s"] = round(ev.silence_duration, 3)
            counts[kind] += 1
            writer.write(rec)

    collector = asyncio.create_task(collect())
    n = max(1, int(rate * frame_ms / 1000))
    try:
        for i in range(0, len(audio), n):
            chunk = audio[i : i + n]
            if len(chunk) < n:
                chunk = np.pad(chunk, (0, n - len(chunk)))
            frame = rtc.AudioFrame(data=chunk.tobytes(), sample_rate=rate, num_channels=1, samples_per_channel=n)
            if enhancer is not None:
                frame = aic.enhance(enhancer, frame)
            stream.push_frame(frame)
            if i % (n * 50) == 0:
                await asyncio.sleep(0)  # let the VAD task run
        stream.end_input()
        await collector
    finally:
        await stream.aclose()
        writer.close()

    meta = {
        "tool": "local_voice_agent.tools.vad_scores",
        "started_at": run_meta.utc_now(),
        "wav": {"path": str(wav), "sha256": run_meta.sha256(wav), "sample_rate": rate,
                "duration_s": round(len(audio) / rate, 4)},
        "vad": {"backend": settings.vad_backend, "model": vad.model, "provider": vad.provider,
                "options": _vad_options(vad)},
        "enhancement": aic.enhancer_description(settings) if enhancer is not None else None,
        "counts": dict(counts),
        "versions": run_meta.versions() | _aic_versions(),
    }
    out.with_name(out.name.removesuffix(".jsonl") + ".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def _vad_options(vad: lk_vad.VAD) -> dict[str, Any] | None:
    opts = getattr(vad, "_opts", None)
    return dataclasses.asdict(opts) if dataclasses.is_dataclass(opts) else None


def _aic_versions() -> dict[str, str | None]:
    from importlib import metadata

    out: dict[str, str | None] = {}
    for pkg in ("aic-sdk", "livekit-plugins-ai-coustics", "livekit-plugins-silero"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wav", type=Path)
    p.add_argument("--vad", choices=["silero", "aic", "aic_enhancer"], help="default: VAD_BACKEND")
    p.add_argument("--enhance", choices=["none", "aic"], help="default: AUDIO_ENHANCEMENT")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    overrides = {k: v for k, v in {"vad_backend": args.vad, "audio_enhancement": args.enhance}.items() if v}
    settings = dataclasses.replace(Settings(), **overrides)
    out = args.out or Path(f"{args.wav.stem}.vad.{settings.vad_backend}.jsonl")
    meta = asyncio.run(score(args.wav, out, settings=settings))
    print(json.dumps(meta["counts"]), f"\nvad timeline: {out}")


if __name__ == "__main__":
    main()

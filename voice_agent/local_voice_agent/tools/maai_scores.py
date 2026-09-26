"""Score a caller WAV with MaAI bc_det and write one JSONL record per 80 ms frame.

    python -m local_voice_agent.tools.maai_scores caller.wav [--agent-wav agent.wav] \
        --out caller.maai.jsonl

With ``--agent-wav`` (same timeline as the caller WAV) the two-channel model is
used, as in live option 1; without it the mono model, as in the bargein server.
Records are ``{"kind": "maai", "t": <s>, "audio_pos_s": <s>, "p_bc": ...}`` on the
WAV's own clock, so they line up with ``replay_stt``'s ``audio_pos_s`` and can be
fed to ``replay_policy --maai``. A frame at ``t`` only uses audio up to ``t``.

Needs the ``maai`` extra (downloads model weights from Hugging Face on first use).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..backchannel.maai_detector import SAMPLE_RATE, MaaiBackchannelDetector
from ..jsonl import JsonlWriter
from . import meta as run_meta
from .replay_stt import load_wav


def _as_16k_float(path: Path) -> np.ndarray:
    audio, rate, _ = load_wav(path)
    if rate != SAMPLE_RATE:
        raise SystemExit(f"{path}: expected {SAMPLE_RATE} Hz (convert with ffmpeg -ar {SAMPLE_RATE})")
    return audio.astype(np.float32) / 32768.0


def score(
    caller: Path,
    out: Path,
    *,
    agent: Path | None = None,
    device: str = "cpu",
    detector_factory=MaaiBackchannelDetector,
) -> dict:
    user = _as_16k_float(caller)
    agent_audio = _as_16k_float(agent) if agent else None
    writer = JsonlWriter(out)
    mode = "bc_det" if agent_audio is not None else "bc_det_mono"

    def on_frame(t: float, p: float) -> None:
        writer.write({"kind": "maai", "t": round(t, 4), "audio_pos_s": round(t, 4), "p_bc": round(p, 4), "mode": mode})

    det = detector_factory(two_channel=agent_audio is not None, device=device, on_frame=on_frame, realtime=False)
    step = SAMPLE_RATE  # 1 s at a time keeps the agent buffer aligned and small
    try:
        for i in range(0, len(user), step):
            if agent_audio is not None:
                det.push_agent_samples(agent_audio[i : i + step])
            det.push_user_samples(user[i : i + step])
        det.wait_idle()
    finally:
        det.close()
        writer.close()
    meta = {
        "tool": "local_voice_agent.tools.maai_scores",
        "started_at": run_meta.utc_now(),
        "mode": mode,
        "caller_wav": {"path": str(caller), "sha256": run_meta.sha256(caller)},
        "agent_wav": {"path": str(agent), "sha256": run_meta.sha256(agent)} if agent else None,
        "frame_s": 0.08,
        "versions": run_meta.versions(),
    }
    out.with_name(out.name.removesuffix(".jsonl") + ".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wav", type=Path, help="caller audio, 16 kHz")
    p.add_argument("--agent-wav", type=Path, help="agent audio on the same timeline, 16 kHz")
    p.add_argument("--out", type=Path)
    p.add_argument("--device", default="cpu")
    args = p.parse_args(argv)
    out = args.out or Path(args.wav.stem + ".maai.jsonl")
    score(args.wav, out, agent=args.agent_wav, device=args.device)
    print(f"maai frames: {out}")


if __name__ == "__main__":
    main()

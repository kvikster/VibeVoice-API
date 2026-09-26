"""Run metadata: package versions, git revision, file fingerprints."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

PACKAGES = (
    "local-voice-agent",
    "livekit-agents",
    "livekit-plugins-nvidia",
    "livekit",
    "nvidia-riva-client",
    "grpcio",
    "numpy",
    "maai",
)


def versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {"python": sys.version.split()[0], "platform": platform.platform()}
    for pkg in PACKAGES:
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def git_revision() -> dict[str, object] | None:
    here = Path(__file__).resolve().parent
    try:
        commit = subprocess.run(
            ["git", "-C", str(here), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(here), "status", "--porcelain", "--", "."],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return {"commit": commit, "dirty": bool(dirty)}


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

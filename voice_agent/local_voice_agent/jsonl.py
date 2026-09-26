"""JSONL helpers shared by the replay tools and the shadow logger."""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from livekit.agents import NOT_GIVEN, stt
from livekit.agents.utils import is_given

EVENT_TYPE_NAMES = {
    stt.SpeechEventType.START_OF_SPEECH: "start_of_speech",
    stt.SpeechEventType.INTERIM_TRANSCRIPT: "interim",
    stt.SpeechEventType.PREFLIGHT_TRANSCRIPT: "preflight",
    stt.SpeechEventType.FINAL_TRANSCRIPT: "final",
    stt.SpeechEventType.RECOGNITION_USAGE: "recognition_usage",
    stt.SpeechEventType.END_OF_SPEECH: "end_of_speech",
}
TRANSCRIPT_TYPES = ("interim", "preflight", "final")


def event_fields(ev: stt.SpeechEvent) -> dict[str, Any]:
    """Event type plus whatever the first alternative actually carries.

    Fields the STT did not provide (e.g. speaker_id on interims, word timings)
    are left out rather than written as null.
    """
    out: dict[str, Any] = {"type": EVENT_TYPE_NAMES.get(ev.type, str(ev.type))}
    if not ev.alternatives:
        return out
    sd = ev.alternatives[0]
    out["text"] = sd.text
    if sd.speaker_id is not None:
        out["speaker_id"] = sd.speaker_id
    if sd.is_primary_speaker is not None:
        out["is_primary_speaker"] = sd.is_primary_speaker
    if sd.start_time or sd.end_time:
        out["start_time_s"] = round(sd.start_time, 3)
        out["end_time_s"] = round(sd.end_time, 3)
    if sd.confidence:
        out["confidence"] = sd.confidence
    if sd.words:
        out["words"] = [_word(w) for w in sd.words]
    return out


def speech_duration(record: dict[str, Any]) -> float | None:
    """Duration of the event's words (``end_time_s - start_time_s``), when present."""
    start, end = record.get("start_time_s"), record.get("end_time_s")
    if start is None or end is None or end <= start:
        return None
    return round(end - start, 3)


def _word(w: Any) -> dict[str, Any]:
    word: dict[str, Any] = {"text": str(w)}
    # livekit-plugins-nvidia 1.8.3 passes Riva word times through in milliseconds
    if is_given(getattr(w, "start_time", NOT_GIVEN)):
        word["start_ms"] = round(float(w.start_time), 1)
    if is_given(getattr(w, "end_time", NOT_GIVEN)):
        word["end_ms"] = round(float(w.end_time), 1)
    if getattr(w, "speaker_id", None) is not None:
        word["speaker_id"] = w.speaker_id
    return word


class JsonlWriter:
    """Appends records from any thread without blocking the caller."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", encoding="utf-8")
        self._q: queue.Queue[dict | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="jsonl-writer", daemon=True)
        self._thread.start()

    def write(self, record: dict) -> None:
        self._q.put(record)

    def close(self) -> None:
        self._q.put(None)
        self._thread.join()
        self._fh.close()

    def _run(self) -> None:
        while (rec := self._q.get()) is not None:
            self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._fh.flush()


def read_jsonl(path: str | Path) -> Iterator[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)

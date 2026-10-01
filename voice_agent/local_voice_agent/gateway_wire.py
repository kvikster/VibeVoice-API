"""Small, versioned wire format for STT events sent by the audio gateway."""

from __future__ import annotations

from livekit.agents import stt
from livekit.agents.types import TimedString
from livekit.agents.utils import is_given

WIRE_VERSION = 1
SAMPLE_RATE = 16000


def event_to_wire(event: stt.SpeechEvent, *, time_offset_s: float = 0.0) -> dict:
    alternatives = []
    for item in event.alternatives:
        words = None
        if item.words is not None:
            words = []
            for word in item.words:
                value = {"text": str(word), "speaker_id": word.speaker_id}
                for name in (
                    "start_time",
                    "end_time",
                    "confidence",
                    "start_time_offset",
                ):
                    field = getattr(word, name)
                    if is_given(field):
                        value[name] = (
                            field + time_offset_s
                            if name in ("start_time", "end_time", "start_time_offset")
                            else field
                        )
                words.append(value)
        alternatives.append(
            {
                "language": str(item.language),
                "text": item.text,
                "start_time": item.start_time + time_offset_s,
                "end_time": item.end_time + time_offset_s,
                "confidence": item.confidence,
                "speaker_id": item.speaker_id,
                "is_primary_speaker": item.is_primary_speaker,
                "words": words,
            }
        )
    usage = event.recognition_usage
    return {
        "type": "stt",
        "event": {
            "type": event.type.value,
            "request_id": event.request_id,
            "alternatives": alternatives,
            "recognition_usage": (
                {
                    "audio_duration": usage.audio_duration,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                }
                if usage is not None
                else None
            ),
        },
    }


def event_from_wire(message: dict) -> stt.SpeechEvent:
    if message.get("type") != "stt" or not isinstance(message.get("event"), dict):
        raise ValueError("invalid gateway STT event")
    payload = message["event"]
    alternatives = []
    for item in payload.get("alternatives", []):
        words = item.get("words")
        alternatives.append(
            stt.SpeechData(
                language=item["language"],
                text=item["text"],
                start_time=item.get("start_time", 0.0),
                end_time=item.get("end_time", 0.0),
                confidence=item.get("confidence", 0.0),
                speaker_id=item.get("speaker_id"),
                is_primary_speaker=item.get("is_primary_speaker"),
                words=(
                    [TimedString(**word) for word in words]
                    if words is not None
                    else None
                ),
            )
        )
    usage = payload.get("recognition_usage")
    return stt.SpeechEvent(
        type=stt.SpeechEventType(payload["type"]),
        request_id=payload.get("request_id", ""),
        alternatives=alternatives,
        recognition_usage=stt.RecognitionUsage(**usage) if usage is not None else None,
    )

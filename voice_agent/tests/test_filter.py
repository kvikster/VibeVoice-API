from types import SimpleNamespace

import pytest

from livekit.agents import stt

from local_voice_agent.backchannel.filter import InterruptionFilterMixin
from local_voice_agent.backchannel.policy import FilterConfig, MaaiReading

INTERIM = stt.SpeechEventType.INTERIM_TRANSCRIPT
FINAL = stt.SpeechEventType.FINAL_TRANSCRIPT


class FakeMaai:
    def __init__(self, p: float) -> None:
        self.p = p
        self.cleared = False

    def reading(self, window_s: float) -> MaaiReading:
        return MaaiReading("available", self.p, evaluated_at=1.0, window_s=window_s, clock="fake")

    def clear_agent(self) -> None:
        self.cleared = True


class ListLog:
    def __init__(self) -> None:
        self.records = []

    def write(self, rec) -> None:
        self.records.append(rec)


class Harness(InterruptionFilterMixin):
    def __init__(self, state="speaking", *, mode="enforce", maai=None, agent_text="Let me explain.") -> None:
        self.session = SimpleNamespace(agent_state=state, on=lambda *a, **k: None)
        self.filter_config = FilterConfig()
        self.filter_mode = mode
        self.maai = maai
        self.decision_log = ListLog()
        self._agent_text = agent_text
        self.clock = 10.0

    def _now(self) -> float:
        return self.clock

    def set_state(self, state: str) -> None:
        self.session.agent_state = state
        self._on_agent_state(state)


def ev(kind, text):
    return stt.SpeechEvent(type=kind, alternatives=[stt.SpeechData(language="en", text=text)])


@pytest.mark.parametrize("text", ["mhm", "yeah.", "Okay, right.", "I am with you", "Do not stop"])
def test_drops_backchannels_while_speaking(text):
    h = Harness()
    assert not h._process(ev(INTERIM, text))
    assert not h._process(ev(FINAL, text))


def test_passes_everything_when_listening():
    h = Harness(state="listening")
    assert h._process(ev(FINAL, "mhm"))
    assert h._process(ev(INTERIM, "yes"))


def test_grace_window_after_a_statement():
    h = Harness()
    h._process(ev(INTERIM, "mhm"))  # observes "speaking"
    h.clock = 10.5
    h.set_state("listening")
    h.clock = 11.0
    assert not h._process(ev(FINAL, "mhm"))  # still inside the 1 s grace
    h.clock = 12.0
    assert h._process(ev(FINAL, "mhm"))


def test_answer_to_a_question_is_never_dropped():
    h = Harness(agent_text="Would you like the premium plan?")
    h._process(ev(INTERIM, "mhm"))
    h.clock = 10.5
    h.set_state("listening")
    h.clock = 10.8
    assert h._process(ev(FINAL, "Yes"))
    assert h.decision_log.records[-2]["reason"] == "awaiting_answer"


def test_barge_in_words_pass_immediately():
    assert Harness()._process(ev(INTERIM, "wait"))


def test_short_interims_wait_for_final():
    h = Harness()
    assert not h._process(ev(INTERIM, "can you"))
    assert h._process(ev(INTERIM, "can you tell me more"))
    assert h._process(ev(FINAL, "can you"))


def test_empty_final_from_multispeaker_adapter_passes():
    assert Harness()._process(ev(FINAL, ""))


def test_speech_boundaries_pass():
    h = Harness()
    assert h._process(stt.SpeechEvent(type=stt.SpeechEventType.START_OF_SPEECH))
    assert h._process(stt.SpeechEvent(type=stt.SpeechEventType.END_OF_SPEECH))


def test_maai_vetoes_unknown_short_utterance():
    assert not Harness(maai=FakeMaai(0.8))._process(ev(FINAL, "but high"))
    assert Harness(maai=FakeMaai(0.1))._process(ev(FINAL, "but high"))
    # never vetoes longer utterances or barge-in words
    assert Harness(maai=FakeMaai(0.9))._process(ev(FINAL, "tell me more about that"))
    assert Harness(maai=FakeMaai(0.9))._process(ev(FINAL, "stop"))


def test_agent_audio_cleared_when_agent_stops_speaking():
    maai = FakeMaai(0.0)
    h = Harness(maai=maai)
    h.set_state("listening")
    assert maai.cleared


def test_shadow_forwards_everything_and_logs_what_enforce_would_do():
    h = Harness(mode="shadow")
    events = [ev(INTERIM, "mhm"), ev(FINAL, "mhm"), ev(INTERIM, "can"), ev(FINAL, "stop")]
    assert all(h._process(e) for e in events)
    decisions = [r for r in h.decision_log.records if r.get("policy") == "text_filter"]
    assert [(d["action"], d["mode"]) for d in decisions] == [
        ("drop", "shadow"),
        ("drop", "shadow"),
        ("hold", "shadow"),
        ("pass", "shadow"),
    ]


def test_log_is_replayable_input():
    h = Harness(maai=FakeMaai(0.3))
    h._process(ev(FINAL, "mhm"))
    kinds = [r["kind"] for r in h.decision_log.records]
    assert kinds == ["agent", "stt", "decision", "decision"]  # catch-up agent record first
    stt_rec = h.decision_log.records[1]
    assert stt_rec["type"] == "final" and stt_rec["text"] == "mhm" and stt_rec["maai"]["p_bc"] == 0.3

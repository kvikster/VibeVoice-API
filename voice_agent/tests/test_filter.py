from types import SimpleNamespace

import pytest

from livekit.agents import stt

from local_voice_agent.backchannel.filter import FilterConfig, InterruptionFilterMixin

INTERIM = stt.SpeechEventType.INTERIM_TRANSCRIPT
FINAL = stt.SpeechEventType.FINAL_TRANSCRIPT


class FakeMaai:
    def __init__(self, p: float) -> None:
        self.p = p
        self.cleared = False

    def recent_max(self, window_s: float) -> float:
        return self.p

    def clear_agent(self) -> None:
        self.cleared = True


class Harness(InterruptionFilterMixin):
    def __init__(self, state: str = "speaking", maai=None) -> None:
        self.session = SimpleNamespace(agent_state=state)
        self.filter_config = FilterConfig()
        self.maai = maai
        self._last_speaking_at = 0.0


def ev(kind, text):
    return stt.SpeechEvent(type=kind, alternatives=[stt.SpeechData(language="en", text=text)])


@pytest.mark.parametrize("text", ["mhm", "yeah.", "Okay, right."])
def test_drops_backchannels_while_speaking(text):
    h = Harness()
    assert h._should_drop(ev(INTERIM, text))
    assert h._should_drop(ev(FINAL, text))


def test_passes_everything_when_listening():
    h = Harness(state="listening")
    assert not h._should_drop(ev(FINAL, "mhm"))
    assert not h._should_drop(ev(INTERIM, "yes"))


def test_grace_window_after_agent_stops():
    h = Harness()
    h._should_drop(ev(INTERIM, "mhm"))  # records "speaking"
    h.session.agent_state = "listening"
    assert h._should_drop(ev(FINAL, "mhm"))  # still inside the 1 s grace


def test_barge_in_words_pass_immediately():
    h = Harness()
    assert not h._should_drop(ev(INTERIM, "wait"))


def test_short_interims_wait_for_final():
    h = Harness()
    assert h._should_drop(ev(INTERIM, "can you"))
    assert not h._should_drop(ev(INTERIM, "can you tell me more"))
    assert not h._should_drop(ev(FINAL, "can you"))


def test_empty_final_from_multispeaker_adapter_passes():
    h = Harness()
    assert not h._should_drop(ev(FINAL, ""))


def test_speech_boundaries_pass():
    h = Harness()
    assert not h._should_drop(stt.SpeechEvent(type=stt.SpeechEventType.START_OF_SPEECH))
    assert not h._should_drop(stt.SpeechEvent(type=stt.SpeechEventType.END_OF_SPEECH))


def test_maai_vetoes_unknown_short_utterance():
    assert Harness(maai=FakeMaai(0.8))._should_drop(ev(FINAL, "but high"))
    assert not Harness(maai=FakeMaai(0.1))._should_drop(ev(FINAL, "but high"))
    # never vetoes longer utterances or barge-in words
    assert not Harness(maai=FakeMaai(0.9))._should_drop(ev(FINAL, "tell me more about that"))
    assert not Harness(maai=FakeMaai(0.9))._should_drop(ev(FINAL, "stop"))


def test_agent_audio_cleared_after_grace():
    maai = FakeMaai(0.0)
    h = Harness(state="listening", maai=maai)
    h._should_drop(ev(FINAL, "hello"))
    assert maai.cleared

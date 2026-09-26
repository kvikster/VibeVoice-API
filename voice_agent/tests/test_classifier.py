import numpy as np

from local_voice_agent.bargein_server.classifier import (
    BargeinClassifier,
    OverlapState,
    new_tail,
)

S = 1_000_000_000  # ns


def state_at(elapsed_s: float, transcript: str | None = None) -> tuple[OverlapState, int]:
    st = OverlapState(first_created_at=0, last_created_at=0, transcript=transcript)
    return st, int((elapsed_s - 0.1) * S)


def test_new_tail_growing_window():
    prev = np.arange(1600, dtype=np.int16)
    cur = np.arange(3200, dtype=np.int16)
    tail, cont = new_tail(prev, cur)
    assert cont and np.array_equal(tail, np.arange(1600, 3200))


def test_new_tail_rolling_window():
    audio = np.arange(60000, dtype=np.int16)
    prev, cur = audio[:48000], audio[1760:49760]  # 3 s window slid by 110 ms
    tail, cont = new_tail(prev, cur)
    assert cont and np.array_equal(tail, audio[48000:49760])


def test_new_tail_unrelated_window():
    tail, cont = new_tail(np.ones(1600, np.int16), np.zeros(3200, np.int16))
    assert not cont and len(tail) == 3200


def test_rules_with_transcript():
    c = BargeinClassifier(has_asr=True, has_maai=True)
    assert not c.decide(*state_at(0.1, "stop"), None).is_interruption  # too short
    assert c.decide(*state_at(0.4, "stop"), 0.9).is_interruption
    assert not c.decide(*state_at(0.8, "uh-huh"), 0.1).is_interruption
    assert c.decide(*state_at(0.5, "tell me more"), 0.9).is_interruption
    assert not c.decide(*state_at(0.8, "Paris"), 0.8).is_interruption  # MaAI: backchannel
    assert c.decide(*state_at(0.8, "Paris"), 0.1).is_interruption
    assert not c.decide(*state_at(0.4, "Paris"), 0.1).is_interruption  # wait for more


def test_no_words_never_interrupts_when_asr_is_available():
    c = BargeinClassifier(has_asr=True, has_maai=False)
    assert not c.decide(*state_at(5.0, None), None).is_interruption


def test_fallbacks_without_asr():
    c = BargeinClassifier(has_asr=False, has_maai=True)
    assert c.decide(*state_at(0.7, None), 0.1).is_interruption
    assert not c.decide(*state_at(0.7, None), 0.9).is_interruption
    c = BargeinClassifier(has_asr=False, has_maai=False)
    assert not c.decide(*state_at(1.0, None), None).is_interruption
    assert c.decide(*state_at(2.5, None), None).is_interruption

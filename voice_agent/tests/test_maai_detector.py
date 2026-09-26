"""MaaiBackchannelDetector plumbing with a stand-in for the ``maai`` package
(the real model downloads weights from Hugging Face)."""

import queue
import sys
import time
import types

import numpy as np
import pytest

from livekit import rtc


class FakeMaai:
    instances: list["FakeMaai"] = []

    def __init__(self, mode, **kwargs):
        self.mode = mode
        self.result_dict_queue = queue.Queue()
        self.calls = []
        self.resets = 0
        FakeMaai.instances.append(self)

    def process(self, x1, x2):
        self.calls.append((x1.copy(), x2.copy()))
        loud = float(np.abs(x1).mean()) > 0.05
        self.result_dict_queue.put({"p_bc_det": [0.9 if loud else 0.1, 0.0]})

    def reset_runtime_state(self):
        self.resets += 1


@pytest.fixture
def detector(monkeypatch):
    fake = types.ModuleType("maai")
    fake.Maai = FakeMaai
    fake.MaaiInput = types.SimpleNamespace(Chunk=lambda: object())
    monkeypatch.setitem(sys.modules, "maai", fake)
    from local_voice_agent.backchannel.maai_detector import MaaiBackchannelDetector

    FakeMaai.instances.clear()
    det = MaaiBackchannelDetector()
    yield det
    det.close()


def frame(value: float, seconds: float, rate: int) -> rtc.AudioFrame:
    n = int(rate * seconds)
    data = np.full(n, int(value * 32767), dtype=np.int16)
    return rtc.AudioFrame(data=data.tobytes(), sample_rate=rate, num_channels=1, samples_per_channel=n)


def wait_for(cond, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end and not cond():
        time.sleep(0.01)
    assert cond()


def test_aligned_80ms_chunks_and_history(detector):
    model = FakeMaai.instances[0]
    assert model.mode == "bc_det"
    detector.push_agent(frame(0.3, 0.5, 24000))  # TTS audio, resampled to 16 kHz
    # 0.4 s of loud user audio = 5 model frames, minus ~18 ms resampler latency -> 4
    detector.push_user(frame(0.5, 0.4, 48000))
    wait_for(lambda: len(model.calls) == 4)
    user, agent = model.calls[0]
    assert len(user) == len(agent) == 1280
    assert agent.max() > 0.2  # agent channel carries the queued TTS audio
    wait_for(lambda: detector.recent_max(1.0) == pytest.approx(0.9))


def test_agent_channel_is_silence_when_agent_is_quiet(detector):
    model = FakeMaai.instances[0]
    detector.push_user(frame(0.0, 0.16, 16000))
    wait_for(lambda: len(model.calls) == 2)
    assert not model.calls[0][1].any()
    wait_for(lambda: detector.latest() == pytest.approx(0.1))


def test_reset_discards_state(detector):
    model = FakeMaai.instances[0]
    detector.push_user(frame(0.5, 0.16, 16000))
    wait_for(lambda: detector.recent_max(1.0) > 0.5)
    detector.reset()
    assert detector.recent_max(10.0) == 0.0
    wait_for(lambda: model.resets == 1)

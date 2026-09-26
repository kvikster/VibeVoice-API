"""ai-coustics integration.

The real SDK needs a license key and downloads models from ai-coustics' CDN, so
``AicVAD`` runs against a stand-in ``aic_sdk`` here. The official LiveKit plugin
runs for real, with an invalid key, to check it degrades to pass-through.
"""

import dataclasses
import sys
import types

import numpy as np
import pytest

from livekit import rtc

from local_voice_agent import aic
from local_voice_agent.bargein_server.aic_vad import AicVadFactory, AicVadHub
from local_voice_agent.jsonl import read_jsonl
from local_voice_agent.settings import Settings
from local_voice_agent.tools.vad_scores import score

from .fake_riva import write_wav


class FakeModel:
    def get_id(self):
        return "fake-vad"

    def get_optimal_sample_rate(self):
        return 16000


class FakeVadContext:
    def __init__(self, vad):
        self._vad = vad

    def raw_vad_probability(self):
        return 0.95 if self._vad.last_rms > 0.05 else 0.02

    def get_prediction_delay(self):
        return 0

    def reset(self):
        self._vad.resets += 1


class FakeVad:
    instances = []

    def __init__(self, model, license_key, config=None, otel_config=None):
        self.license_key, self.config, self.otel_config = license_key, config, otel_config
        self.last_rms, self.resets, self.blocks = 0.0, 0, 0
        FakeVad.instances.append(self)

    def process(self, audio):
        assert audio.dtype == np.float32 and len(audio) == self.config.block_size
        self.blocks += 1
        self.last_rms = float(np.sqrt(np.mean(audio**2)))

    def get_context(self):
        return FakeVadContext(self)


@pytest.fixture
def fake_aic_sdk(monkeypatch, tmp_path):
    mod = types.ModuleType("aic_sdk")
    downloads = []

    class Model:
        @staticmethod
        def download(model_id, download_dir):
            downloads.append((model_id, download_dir))
            return str(tmp_path / f"{model_id}.aicmodel")

        @staticmethod
        def from_file(path):
            return FakeModel()

    class ProcessorConfig:
        @staticmethod
        def optimal(model, sample_rate=None, block_size=None, variable_block_size=False):
            return types.SimpleNamespace(sample_rate=16000, block_size=256)

    mod.Model, mod.ProcessorConfig, mod.Vad = Model, ProcessorConfig, FakeVad
    mod.OtelConfig = lambda enable, **kw: types.SimpleNamespace(enable=enable)
    monkeypatch.setitem(sys.modules, "aic_sdk", mod)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    FakeVad.instances.clear()
    return downloads


def settings(**kw):
    return dataclasses.replace(Settings(), **{"aic_license_key": "test-key", **kw})


async def test_aic_vad_runs_silero_state_machine_on_aic_probability(tmp_path, fake_aic_sdk):
    wav = write_wav(tmp_path / "a.wav", [(0.5, 1.5, 0.5)], duration_s=3.0)
    out = tmp_path / "a.vad.jsonl"
    meta = await score(wav, out, settings=settings(vad_backend="aic", aic_models_dir=str(tmp_path)))
    recs = list(read_jsonl(out))
    starts = [r for r in recs if r["type"] == "start_of_speech"]
    ends = [r for r in recs if r["type"] == "end_of_speech"]
    assert len(starts) == 1 and 0.5 <= starts[0]["t"] <= 0.7
    assert len(ends) == 1 and 1.9 <= ends[0]["t"] <= 2.3  # 1.5 s + min_silence 0.55 s
    inference = [r for r in recs if r["type"] == "inference"]
    assert max(r["p_speech"] for r in inference) > 0.8 and min(r["p_speech"] for r in inference) < 0.1
    assert meta["vad"]["model"] == "ai-coustics fake-vad"
    assert meta["vad"]["options"]["min_silence_duration"] == 0.55
    assert meta["vad"]["prediction_delay_samples"] == 0
    assert fake_aic_sdk == [("vad-2.1-xxs-16khz", str(tmp_path))]
    vad = FakeVad.instances[-1]
    assert vad.license_key == "test-key" and vad.otel_config.enable is False
    import os

    assert os.environ["DO_NOT_TRACK"] == "1"


def test_aic_vad_is_compatible_with_the_turn_detector(fake_aic_sdk, tmp_path):
    vad = aic.build_vad(settings(vad_backend="aic", aic_vad_model_path=str(tmp_path / "local.aicmodel")))
    assert isinstance(vad, aic.AicVAD)
    assert vad.min_silence_duration >= 0.25  # LiveKit's streaming TurnDetector requirement
    assert fake_aic_sdk == []  # a local model file means no download


def test_gateway_voice_focus_vad_processes_incremental_tail(fake_aic_sdk, tmp_path):
    config = settings(
        aic_vad_model="vad-vf-2.0-s-16khz",
        aic_vad_model_path=str(tmp_path / "voice-focus.aicmodel"),
    )
    scorer = AicVadFactory(config)()
    loud = np.full(128, 12000, dtype=np.int16)
    assert scorer.push(loud) is None
    assert scorer.push(loud) > 0.9
    scorer.reset()
    assert scorer.push(np.zeros(256, dtype=np.int16)) < 0.1
    assert FakeVad.instances[-1].resets == 1


def test_gateway_vad_hub_excludes_other_rooms_and_stale_scores(monkeypatch):
    from local_voice_agent.bargein_server import aic_vad

    clock = [100.0]
    monkeypatch.setattr(aic_vad.time, "monotonic", lambda: clock[0])
    hub = AicVadHub(max_age_s=0.5)
    headers = {"X-LiveKit-Room-ID": "room-a", "X-LiveKit-Job-ID": "job-a"}
    lease = hub.start(headers)
    hub.publish(lease, 0.9, 480)
    assert hub.read(headers).probability == 0.9
    assert hub.read({"X-LiveKit-Room-ID": "room-b", "X-LiveKit-Job-ID": "job-a"}) is None
    clock[0] += 0.6
    assert hub.read(headers) is None
    hub.close(lease)


async def test_enhancer_vad_reads_the_flag_on_each_frame(tmp_path):
    from livekit.plugins import ai_coustics

    class FlagEnhancer:  # stands in for the enhancer: annotates frames like the plugin does
        def _process(self, frame):
            loud = np.abs(np.frombuffer(frame.data, dtype=np.int16)).mean() > 1000
            frame.userdata[ai_coustics.FRAME_USERDATA_AIC_VAD_ATTRIBUTE] = bool(loud)
            return frame

    wav = write_wav(tmp_path / "b.wav", [(0.5, 1.5, 0.5)], duration_s=2.5)
    out = tmp_path / "b.vad.jsonl"
    s = settings(vad_backend="aic_enhancer", audio_enhancement="aic")
    await score(wav, out, settings=s, vad=ai_coustics.VAD(), enhancer=FlagEnhancer())
    recs = list(read_jsonl(out))
    assert [r["type"] for r in recs if r["type"] != "inference"] == ["start_of_speech", "end_of_speech"]
    assert all("p_speech" not in r for r in recs if r["type"] == "inference")


async def test_silero_through_the_same_tool(tmp_path):
    wav = write_wav(tmp_path / "c.wav", [(0.5, 1.5, 0.5)], duration_s=2.0)
    out = tmp_path / "c.vad.jsonl"
    meta = await score(wav, out, settings=Settings())
    recs = list(read_jsonl(out))
    assert meta["vad"]["model"] == "silero" and recs and all("p_speech" in r for r in recs if r["type"] == "inference")


def test_official_enhancer_uses_the_ai_coustics_key_and_fails_open():
    from livekit.plugins import ai_coustics

    enhancer = aic.build_enhancer(settings(aic_license_key="not-a-real-key"))
    assert isinstance(enhancer._auth, ai_coustics.AiCousticsApi)  # not LiveKit Cloud
    samples = (np.sin(np.arange(480) / 5) * 8000).astype(np.int16)
    frame = rtc.AudioFrame(data=samples.tobytes(), sample_rate=48000, num_channels=1, samples_per_channel=480)
    out = aic.enhance(enhancer, frame)  # invalid key / no model: the plugin passes audio through
    assert np.array_equal(np.frombuffer(out.data, dtype=np.int16), samples)


def test_settings_validation_and_key_hygiene():
    with pytest.raises(ValueError, match="AUDIO_ENHANCEMENT=aic"):
        dataclasses.replace(Settings(), vad_backend="aic_enhancer")
    with pytest.raises(ValueError, match="VAD_BACKEND"):
        dataclasses.replace(Settings(), vad_backend="webrtc")
    with pytest.raises(ValueError, match="AIC_LICENSE_KEY"):
        aic.build_vad(dataclasses.replace(Settings(), vad_backend="aic", aic_license_key=None))
    assert "secret-key" not in repr(dataclasses.replace(Settings(), aic_license_key="secret-key"))
    with pytest.raises(ValueError, match="AIC_ENHANCER_MODEL"):
        aic.build_enhancer(settings(aic_enhancer_model="quail_xxl"))

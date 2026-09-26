"""replay_stt against a scripted Riva server, through the real nvidia plugin and MultiSpeakerAdapter."""

import dataclasses
import json

import pytest

from local_voice_agent.jsonl import read_jsonl
from local_voice_agent.settings import Settings
from local_voice_agent.tools.replay_stt import ReplayConfig, meta_path_for, replay

from .fake_riva import FakeRiva, Step, response, serve, write_wav

# caller (S1, loud) 0.2-1.4 s, then a background talker (S2, 5x quieter) 1.8-2.8 s
CALLER_FINAL = response(
    "Hello there.", final=True, words=[("Hello", 200, 700, 1), ("there.", 800, 1300, 1)]
)
BACKGROUND_FINAL = response(
    "Background talk.", final=True, words=[("Background", 1900, 2300, 2), ("talk.", 2400, 2700, 2)]
)


@pytest.fixture
def riva():
    fake = FakeRiva(
        script=[
            Step(0.6, response("hello", final=False)),
            Step(1.5, CALLER_FINAL),
            Step(2.2, response("background", final=False)),
        ],
        on_end=[BACKGROUND_FINAL],  # only arrives because the stream is flushed at WAV end
    )
    server, addr = serve(fake)
    yield fake, addr
    server.stop(0)


async def run(tmp_path, addr, **settings_overrides):
    wav = write_wav(tmp_path / "mix.wav", [(0.2, 1.4, 0.5), (1.8, 2.8, 0.1)], duration_s=3.0)
    out = tmp_path / "mix.stt.jsonl"
    settings = dataclasses.replace(Settings(), riva_server=addr, **settings_overrides)
    meta = await replay(ReplayConfig(wav=wav, out=out, settings=settings, speed=20.0, tail_silence_s=0.3))
    return list(read_jsonl(out)), meta


def finals(records, layer):
    return [r for r in records if r["layer"] == layer and r["type"] == "final"]


async def test_raw_and_adapter_layers_from_one_pass(tmp_path, riva):
    fake, addr = riva
    records, meta = await run(tmp_path, addr)

    raw = finals(records, "raw")
    assert [r["text"] for r in raw] == ["Hello there.", "Background talk."]
    assert raw[0]["adapter_action"] == "passed" and raw[0]["is_primary_speaker"] is True
    assert raw[1]["adapter_action"] == "dropped" and raw[1]["speaker_id"] == "S2"
    assert all(r["primary_speaker"] == "S1" for r in raw)
    assert raw[0]["word_speaker_tags"] == ["S1", "S1"]

    adapted = finals(records, "adapter")
    assert [r["text"] for r in adapted] == ["Hello there.", ""]
    assert adapted[1]["cleared_suppressed_final"] is True
    assert adapted[1]["source_seq"] == raw[1]["seq"]

    # interims carry no speaker tags or word timings: those keys are absent, not null
    interim = next(r for r in records if r["layer"] == "raw" and r["type"] == "interim")
    assert "speaker_id" not in interim and "words" not in interim and "word_speaker_tags" not in interim

    # the last final only exists because end of WAV flushed the stream
    assert raw[1]["audio_pos_s"] >= 3.0
    assert meta["summary"]["drained"] is True
    assert fake.configs[0].config.diarization_config.enable_speaker_diarization is True


async def test_timing_fields_and_meta(tmp_path, riva):
    _, addr = riva
    records, meta = await run(tmp_path, addr)
    ts = [r["t"] for r in records]
    assert ts == sorted(ts)
    assert all(r["audio_pos_samples"] == round(r["audio_pos_s"] * 16000) for r in records)

    on_disk = json.loads(meta_path_for(tmp_path / "mix.stt.jsonl").read_text())
    assert on_disk["server_config"]["models"][0]["model_name"] == "fake-nemotron-en"
    assert on_disk["versions"]["livekit-agents"] == "1.8.3"
    assert on_disk["stt_options"]["enable_diarization"] is True
    assert on_disk["adapter_options"]["suppress_background_speaker"] is True
    assert on_disk["wav"]["duration_s"] == 3.0
    assert on_disk["summary"]["events"]["raw.final.dropped"] == 1


async def test_without_suppression_background_final_passes(tmp_path, riva):
    _, addr = riva
    records, _ = await run(tmp_path, addr, suppress_background=False)
    assert [r["text"] for r in finals(records, "adapter")] == ["Hello there.", "Background talk."]
    assert finals(records, "adapter")[1]["is_primary_speaker"] is False


async def test_enhancer_runs_before_the_stt(tmp_path, riva):
    import numpy as np

    from livekit import rtc

    class Halve:  # stands in for the ai-coustics FrameProcessor
        frames = 0

        def _process(self, frame):
            self.frames += 1
            data = (np.frombuffer(frame.data, dtype=np.int16) // 2).astype(np.int16)
            return rtc.AudioFrame(data=data.tobytes(), sample_rate=frame.sample_rate, num_channels=1,
                                  samples_per_channel=frame.samples_per_channel)

    _, addr = riva
    wav = write_wav(tmp_path / "mix.wav", [(0.2, 1.4, 0.5), (1.8, 2.8, 0.1)], duration_s=3.0)
    settings = dataclasses.replace(Settings(), riva_server=addr, audio_enhancement="aic", aic_license_key="k")
    enhancer = Halve()
    meta = await replay(ReplayConfig(wav=wav, out=tmp_path / "e.jsonl", settings=settings, speed=20.0,
                                     tail_silence_s=0.3, enhancer=enhancer))
    assert enhancer.frames == 165  # (3.0 s + 0.3 s) / 20 ms
    assert meta["enhancement"]["model"] == "quail_vf_l"
    assert meta["summary"]["events"]["raw.final.passed"] == 1

import json

from livekit.agents import stt

from local_voice_agent.jsonl import read_jsonl
from local_voice_agent.tools.replay_policy import main, replay

from .test_filter import FINAL, INTERIM, FakeMaai, Harness, ev

LOG = [
    {"kind": "agent", "t": 0.0, "state": "speaking", "text": "Let me walk you through the plans."},
    {"kind": "stt", "t": 1.3, "type": "interim", "text": "I am"},
    {"kind": "stt", "t": 1.6, "type": "final", "text": "I am with you"},
    {"kind": "stt", "t": 2.3, "type": "interim", "text": "Stop"},
    {"kind": "stt", "t": 2.7, "type": "final", "text": "Stop"},
    {"kind": "agent", "t": 3.0, "state": "listening", "text": "Shall I book the first plan?"},
    {"kind": "stt", "t": 3.4, "type": "final", "text": "Yes"},
    {"kind": "agent", "t": 5.0, "state": "speaking", "text": "Great, booking it now."},
    {"kind": "maai", "t": 5.8, "p_bc": 0.82},
    {"kind": "stt", "t": 5.9, "type": "final", "text": "but high"},
]


def decisions(records, **kw):
    return [json.dumps(r, sort_keys=True) for r in replay(records, layer=None, **kw)]


def test_same_log_gives_same_decisions():
    assert decisions(LOG) == decisions(LOG)


def test_decisions_never_depend_on_later_events():
    full = decisions(LOG)
    for cut in range(len(LOG)):
        prefix = decisions(LOG[:cut])
        assert prefix == full[: len(prefix)]


def test_input_order_does_not_matter():
    assert decisions(list(reversed(LOG))) == decisions(LOG)


def text_filter(records):
    return [(r["text"], r["action"], r["reason"]) for r in replay(records, layer=None) if r["policy"] == "text_filter"]


def test_expected_decisions():
    assert text_filter(LOG) == [
        ("I am", "hold", "phrase_prefix_awaits_final"),
        ("I am with you", "drop", "continuer_phrase"),
        ("Stop", "pass", "interrupt_token"),
        ("Stop", "pass", "interrupt_token"),
        ("Yes", "pass", "awaiting_answer"),
        ("but high", "drop", "maai_backchannel"),
    ]


def test_maai_is_optional_and_reported():
    without = [r for r in LOG if r["kind"] != "maai"]
    last = [r for r in replay(without, layer=None) if r["policy"] == "text_filter"][-1]
    assert (last["action"], last["reason"]) == ("pass", "content_words")
    assert last["signals"]["maai"] == {"status": "unavailable"}

    last = [r for r in replay(LOG, layer=None) if r["policy"] == "text_filter"][-1]
    assert last["signals"]["maai"] == {
        "status": "available",
        "p_bc": 0.82,
        "evaluated_at": 5.8,
        "window_s": 1.5,
        "clock": "event_time_s",
    }


def test_maai_frames_outside_the_window_are_unavailable():
    log = LOG[:-2] + [{"kind": "maai", "t": 4.0, "p_bc": 0.9}, LOG[-1]]  # 1.9 s before, window 1.5 s
    last = [r for r in replay(log, layer=None) if r["policy"] == "text_filter"][-1]
    assert last["signals"]["maai"]["status"] == "unavailable"
    assert last["reason"] == "content_words"


def test_replay_stt_output_uses_adapter_layer_and_audio_clock():
    records = [
        {"kind": "agent", "audio_pos_s": 0.0, "state": "speaking", "text": "Hello."},
        {"kind": "stt", "layer": "raw", "seq": 1, "t": 1.05, "audio_pos_s": 1.0, "type": "final",
         "text": "Background talk."},
        {"kind": "stt", "layer": "adapter", "seq": 2, "t": 1.06, "audio_pos_s": 1.0, "type": "final", "text": ""},
    ]
    out = [r for r in replay(records) if r["policy"] == "text_filter"]
    assert [(r["event_seq"], r["t"], r["reason"]) for r in out] == [(2, 1.0, "empty_transcript")]
    raw = [r for r in replay(records, layer="raw") if r["policy"] == "text_filter"]
    assert raw[0]["text"] == "Background talk." and raw[0]["interruption"] == "interrupt"


def test_live_log_replays_to_the_logged_decisions():
    h = Harness(maai=FakeMaai(0.2))
    script = [
        (10.0, None, ev(INTERIM, "mhm")),
        (10.2, None, ev(FINAL, "Do not stop")),
        (10.4, None, stt.SpeechEvent(type=stt.SpeechEventType.END_OF_SPEECH)),
        (10.6, None, ev(INTERIM, "can you")),
        (10.9, None, ev(FINAL, "can you tell me more")),
        (11.0, "listening", None),
        (11.3, None, ev(FINAL, "okay")),
    ]
    for t, state, event in script:
        h.clock = t
        if state:
            h.set_state(state)
        if event:
            h._process(event)
    logged = [r for r in h.decision_log.records if r["kind"] == "decision"]
    replayed = list(replay(h.decision_log.records, layer=None, time_field="t"))
    strip = lambda rs: [{k: v for k, v in r.items() if k != "mode"} for r in rs]  # noqa: E731
    assert strip(replayed) == strip(logged)


def test_cli(tmp_path, capsys):
    events = tmp_path / "events.jsonl"
    events.write_text("".join(json.dumps(r) + "\n" for r in LOG if r["kind"] != "agent"))
    agent = tmp_path / "agent.jsonl"
    agent.write_text("".join(json.dumps(r) + "\n" for r in LOG if r["kind"] == "agent"))
    out = tmp_path / "decisions.jsonl"
    main([str(events), "--agent", str(agent), "--layer", "all", "--out", str(out)])
    written = list(read_jsonl(out))
    assert len(written) == 12 and {r["policy"] for r in written} == {"text_filter", "interruption_classifier"}
    assert "continuer_phrase" in capsys.readouterr().err


def test_lone_final_back_dates_the_overlap_by_its_word_timing():
    records = [
        {"kind": "agent", "t": 0.0, "state": "speaking", "text": "Here are the plans."},
        {"kind": "stt", "t": 3.0, "type": "final", "text": "Stop", "start_time_s": 2.3, "end_time_s": 2.7},
        {"kind": "stt", "t": 3.1, "type": "end_of_speech"},
    ]
    cl = [r for r in replay(records, layer=None) if r["policy"] == "interruption_classifier"]
    assert (cl[0]["decision"], cl[0]["reason"], cl[0]["signals"]["elapsed_overlap_s"]) == (
        "interrupt",
        "interrupt_token",
        0.4,
    )
    assert (cl[1]["decision"], cl[1]["reason"]) == ("not_applicable", "no_user_utterance")

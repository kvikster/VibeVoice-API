"""The reviewer's check set, in two contexts, for both policies (text rules only, no MaAI).

Each utterance arrives as a streaming partial at +0.3 s and a final at +0.6 s
after the user starts, the way NeMo-Speech.cpp emits them.
"""

import pytest

from local_voice_agent.policy_runner import PolicyRunner

CASES = {
    # text: (interim partial, expected text filter on the final while the agent speaks,
    #        expected classifier on the final while the agent speaks)
    "I am with you": ("I am", ("drop", "continuer_phrase", "no_interrupt"), ("no_interrupt", "continuer_phrase")),
    "Please proceed": ("Please", ("drop", "continuer_phrase", "no_interrupt"), ("no_interrupt", "continuer_phrase")),
    "Yes": ("Yes", ("drop", "backchannel_tokens", "no_interrupt"), ("no_interrupt", "backchannel_tokens")),
    "Okay": ("Okay", ("drop", "backchannel_tokens", "no_interrupt"), ("no_interrupt", "backchannel_tokens")),
    "Stop": ("Stop", ("pass", "interrupt_token", "interrupt"), ("interrupt", "interrupt_token")),
    "Do not stop": ("Do not", ("drop", "continuer_phrase", "no_interrupt"), ("no_interrupt", "continuer_phrase")),
}


def while_agent_speaks(text: str, partial: str):
    r = PolicyRunner()
    r.agent(0.0, "speaking", "Let me walk you through the three plans we offer.")
    user = 2.0
    interim = r.stt(user + 0.3, "interim", partial)
    final = r.stt(user + 0.6, "final", text)
    return interim, final


def after_agent_question(text: str, partial: str):
    r = PolicyRunner()
    r.agent(0.0, "speaking", "Shall I book the first plan for you?")
    r.agent(3.0, "listening")
    user = 3.2  # inside the 1 s grace window that would otherwise drop "Yes"
    interim = r.stt(user + 0.3, "interim", partial)
    final = r.stt(user + 0.6, "final", text)
    return interim, final


@pytest.mark.parametrize("text", list(CASES))
def test_agent_speaking(text):
    partial, (action, reason, interruption), (decision, code) = CASES[text]
    (tf_interim, cl_interim), (tf_final, cl_final) = while_agent_speaks(text, partial)

    assert (tf_final["action"], tf_final["reason"], tf_final["interruption"]) == (action, reason, interruption)
    assert (cl_final["decision"], cl_final["reason"]) == (decision, code)
    assert tf_final["agent"] == {"state": "speaking", "since_speaking_s": 0.0, "awaiting_answer": False}
    assert tf_final["signals"]["maai"] == {"status": "unavailable"}
    assert cl_final["signals"]["asr"] == {"status": "received", "text": text}

    # the partial never interrupts through the text filter unless it is a barge-in word;
    # the classifier's overlap starts at the first transcript, so it always waits on it
    if text == "Stop":
        assert (tf_interim["action"], tf_interim["interruption"]) == ("pass", "interrupt")
    else:
        assert tf_interim["action"] in ("hold", "drop") and tf_interim["interruption"] == "no_interrupt"
    assert (cl_interim["decision"], cl_interim["reason"]) == ("wait", "overlap_too_short")


@pytest.mark.parametrize("text", list(CASES))
def test_answer_after_agent_question(text):
    partial = CASES[text][0]
    (tf_interim, cl_interim), (tf_final, cl_final) = after_agent_question(text, partial)
    for rec in (tf_interim, tf_final):
        assert (rec["action"], rec["reason"], rec["interruption"]) == ("pass", "awaiting_answer", "not_applicable")
        assert rec["agent"]["awaiting_answer"] is True and rec["agent"]["state"] == "listening"
    for rec in (cl_interim, cl_final):
        assert (rec["decision"], rec["reason"]) == ("not_applicable", "agent_not_speaking")


def test_grace_window_after_a_statement_still_drops_backchannels():
    r = PolicyRunner()
    r.agent(0.0, "speaking", "Your order has been placed.")
    r.agent(2.0, "listening")
    tf, _ = r.stt(2.5, "final", "Okay")
    assert (tf["action"], tf["reason"]) == ("drop", "backchannel_tokens")
    tf, _ = r.stt(3.5, "final", "Okay")  # past the 1 s grace
    assert (tf["action"], tf["reason"]) == ("pass", "agent_not_speaking")


def test_do_not_stop_partial_waits_instead_of_interrupting():
    r = PolicyRunner()
    r.agent(0.0, "speaking", "Let me explain.")
    tf, _ = r.stt(2.0, "interim", "Do")
    assert (tf["action"], tf["reason"]) == ("hold", "phrase_prefix_awaits_final")
    tf, cl = r.stt(2.3, "interim", "Do not")
    assert (tf["action"], tf["reason"]) == ("hold", "phrase_prefix_awaits_final")
    assert (cl["decision"], cl["reason"]) == ("wait", "phrase_prefix_waiting")


def test_real_content_interrupts():
    r = PolicyRunner()
    r.agent(0.0, "speaking", "Let me explain.")
    r.stt(2.0, "interim", "Can")
    tf, cl = r.stt(2.6, "interim", "Can you tell me the price")
    assert (tf["action"], tf["interruption"]) == ("pass", "interrupt")
    assert cl["decision"] == "interrupt" and cl["reason"] == "content_words"

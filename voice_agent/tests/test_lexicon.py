import pytest

from local_voice_agent.backchannel.lexicon import Verdict, analyze, classify, content_words


@pytest.mark.parametrize(
    "text",
    ["mhm", "Uh-huh.", "yeah yeah", "Okay, right.", "mm hmm", "I see.", "got it", "wow", "Yes"],
)
def test_backchannels(text):
    assert classify(text) is Verdict.BACKCHANNEL


@pytest.mark.parametrize(
    "text", ["I am with you", "I'm with you", "Please proceed", "go on", "Do not stop", "Don't stop."]
)
def test_continuers(text):
    a = analyze(text)
    assert a.verdict is Verdict.BACKCHANNEL and a.kind == "continuer_phrase"


@pytest.mark.parametrize(
    "text", ["Stop.", "wait wait", "no", "Sorry, what?", "hold on", "actually", "Do not stop, wait"]
)
def test_barge_in_words(text):
    assert classify(text) is Verdict.INTERRUPT


@pytest.mark.parametrize("text", ["yeah I want the suite", "Paris", "but high", "I am hungry"])
def test_content(text):
    assert classify(text) is Verdict.CONTENT


@pytest.mark.parametrize("text", ["Do", "Do not", "I am", "Please", "yeah I am"])
def test_streaming_prefix_of_a_phrase(text):
    a = analyze(text)
    assert a.verdict is Verdict.CONTENT and a.prefix_pending


def test_prefix_only_counts_at_the_end():
    assert not analyze("I am hungry").prefix_pending
    assert not analyze("please tell me").prefix_pending


def test_empty():
    assert classify("  ...  ") is Verdict.EMPTY


def test_content_words_ignores_fillers_and_phrases():
    assert content_words("uh, I see, the blue one") == 3
    assert content_words("mm hmm okay") == 0

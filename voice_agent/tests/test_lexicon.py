import pytest

from local_voice_agent.backchannel.lexicon import Verdict, classify, content_words


@pytest.mark.parametrize(
    "text",
    ["mhm", "Uh-huh.", "yeah yeah", "Okay, right.", "mm hmm", "I see.", "got it", "wow"],
)
def test_backchannels(text):
    assert classify(text) is Verdict.BACKCHANNEL


@pytest.mark.parametrize("text", ["Stop.", "wait wait", "no", "Sorry, what?", "hold on", "actually"])
def test_barge_in_words(text):
    assert classify(text) is Verdict.INTERRUPT


@pytest.mark.parametrize("text", ["yeah I want the suite", "Paris", "but high", "yes"])
def test_content(text):
    assert classify(text) is Verdict.CONTENT


def test_empty():
    assert classify("  ...  ") is Verdict.EMPTY


def test_content_words_ignores_fillers_and_phrases():
    assert content_words("uh, I see, the blue one") == 3
    assert content_words("mm hmm okay") == 0

import pytest

from aether.talk import looks_like_place, parse_reply


def test_rejects_assistant_echo():
    assert looks_like_place("stay here") is False
    assert looks_like_place("listening to stay here") is False
    assert looks_like_place("ok") is False


def test_accepts_cities():
    assert looks_like_place("Hyderabad") is True
    assert looks_like_place("San Francisco") is True
    assert looks_like_place("new york") is True
    assert looks_like_place("Hyderabad?") is True
    assert looks_like_place("St. Louis") is True
    assert looks_like_place("東京") is True
    assert looks_like_place("São Paulo") is True
    assert looks_like_place("Stratford-upon-Avon") is True


@pytest.mark.parametrize(
    "text",
    [
        "hahaha", "haha", "hehe", "lol", "hello", "hi", "hey", "thanks", "thank you", "idk", "asdf", "qwerty",
        "zzzzzz", "aaaaaa", "12345", "!!!", "???", "a", "", "   ", "@#$%", "<script>", "x" * 61,
        "this is a very long sentence that is not a place at all",
    ],
)
def test_rejects_chatter_noise_and_junk(text):
    assert looks_like_place(text) is False


@pytest.mark.parametrize("text", ["hahaha", "hello", "asdf", "12345", "lol", "!!!"])
def test_junk_never_becomes_a_place_intent(text):
    assert parse_reply(text, has_place=False)[0] != "place"
    assert parse_reply(text, has_place=True)[0] != "place"

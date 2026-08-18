from aether.talk import looks_like_place


def test_rejects_assistant_echo():
    assert looks_like_place("stay here") is False
    assert looks_like_place("listening to stay here") is False
    assert looks_like_place("ok") is False


def test_accepts_cities():
    assert looks_like_place("Hyderabad") is True
    assert looks_like_place("San Francisco") is True
    assert looks_like_place("new york") is True

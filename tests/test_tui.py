import asyncio

from textual.widgets import Input, RichLog

from aether import tui
from aether.clients import PlaceNotFound
from aether.clients.http import ApiError
from tests.test_snapshot import make_brief


def chat_text(app) -> str:
    log = app.query_one("#chat", RichLog)
    return "\n".join(strip.text for strip in log.lines)


async def _session(inputs, fake):
    tui.build_brief_sync = fake
    app = tui.AetherApp()
    async with app.run_test() as pilot:
        for text in inputs:
            box = app.query_one(Input)
            box.value = text
            await pilot.press("enter")
            await pilot.pause(0.3)
        await pilot.pause(0.3)
        return chat_text(app)


def play(inputs, fake):
    original = tui.build_brief_sync
    try:
        return asyncio.run(_session(inputs, fake))
    finally:
        tui.build_brief_sync = original


def boom(exc):
    def _raise(**kwargs):
        raise exc

    return _raise


def test_chatter_never_hits_the_lookup():
    calls = []
    text = play(["hahaha", "hello", "12345"], lambda **kw: calls.append(kw))
    assert calls == []
    assert text.count("doesn't look like a place name") == 3


def test_unknown_place_says_it_does_not_exist():
    text = play(["blahblahblah"], boom(PlaceNotFound("blahblahblah")))
    assert "can't find a place called 'blahblahblah'" in text


def test_typo_gets_a_suggestion():
    text = play(["hyderbad"], boom(PlaceNotFound("hyderbad", "Hyderabad")))
    assert "Did you mean Hyderabad?" in text


def test_network_failure_is_not_blamed_on_the_place():
    text = play(["Paris"], boom(ApiError("nominatim: timed out")))
    assert "not the place" in text
    assert "can't find a place" not in text


def test_success_shows_what_it_locked_onto():
    text = play(["Hyderabad"], lambda **kw: make_brief())
    assert "Locked on Hyderabad, India." in text
    assert "Risk LOW" in text

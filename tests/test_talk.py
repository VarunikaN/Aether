from aether.talk import parse_reply


def test_first_message_is_a_city():
    assert parse_reply("Hyderabad", has_place=False) == ("place", "hyderabad")
    assert parse_reply("what's happening in Tokyo", has_place=False) == ("place", "tokyo")


def test_followups_are_topics():
    assert parse_reply("weather", has_place=True)[0] == "weather"
    assert parse_reply("flights", has_place=True)[0] == "flights"
    assert parse_reply("iss", has_place=True)[0] == "iss"
    assert parse_reply("earthquakes", has_place=True)[0] == "quakes"


def test_stay_here_is_not_a_city():
    assert parse_reply("stay here", has_place=True) == ("stay", "")
    assert parse_reply("stay here", has_place=False) == ("stay", "")
    assert parse_reply("here", has_place=True) == ("stay", "")
    assert parse_reply("ok", has_place=True) == ("stay", "")


def test_switch_city_and_quit():
    assert parse_reply("Tokyo", has_place=True) == ("place", "tokyo")
    assert parse_reply("somewhere else", has_place=True)[0] == "move"
    assert parse_reply("quit", has_place=True)[0] == "quit"


def test_mississippi_is_not_iss():
    assert parse_reply("Mississippi", has_place=False) == ("place", "mississippi")

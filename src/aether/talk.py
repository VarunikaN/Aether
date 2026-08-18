from __future__ import annotations

import re

QUIT = {"q", "quit", "exit", "bye", "goodbye", "stop"}
MOVE = {
    "elsewhere",
    "somewhere else",
    "another place",
    "new place",
    "change city",
    "move",
    "switch",
    "leave",
    "go away",
}
STAY = {
    "stay",
    "stay here",
    "stay there",
    "stay put",
    "here",
    "here only",
    "keep",
    "keep looking",
    "this",
    "this place",
    "same",
    "same place",
    "remain",
    "yes",
    "y",
    "yeah",
    "yep",
    "ok",
    "okay",
    "sure",
    "continue",
    "don't move",
    "do not move",
    "still here",
}
HELP = {"help", "?", "h", "options", "menu"}

TOPICS = {
    "weather": ("weather", "rain", "temp", "temperature", "hot", "cold", "wind", "forecast", "drizzle", "sun"),
    "quakes": ("quake", "quakes", "earthquake", "earthquakes", "seismic", "tremor"),
    "flights": ("flight", "flights", "plane", "planes", "traffic", "airborne"),
    "iss": ("iss", "orbit"),
    "events": ("event", "events", "fire", "wildfire", "disaster", "eonet"),
    "risk": ("risk", "danger", "safe", "safety", "alert"),
    "all": ("all", "everything", "full", "brief", "summary"),
}

PLACE_PREFIX = (
    r"what(?:'s| is) happening (?:in|at|near) ",
    r"what(?:'s| is) the (?:weather|risk) (?:in|at|near) ",
    r"(?:look at|check|scan|go to|move to|switch to) ",
    r"tell me about ",
)

_VERBS = {
    "stay",
    "here",
    "want",
    "show",
    "tell",
    "give",
    "please",
    "just",
    "more",
    "again",
    "looking",
    "listen",
    "listening",
}


def _norm(line: str) -> str:
    return " ".join(line.strip().lower().split())


def extract_place(text: str) -> str:
    place = text
    for prefix in PLACE_PREFIX:
        place = re.sub(rf"^{prefix}", "", place)
    place = re.sub(r"^(?:in|at|near)\s+", "", place)
    return place.strip(" ?.,!")


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def looks_like_place(text: str) -> bool:
    text = _norm(text)
    if not text or text in QUIT | MOVE | STAY | HELP:
        return False
    tokens = re.findall(r"[a-z]+", text)
    if not tokens or len(tokens) > 5:
        return False
    if any(token in _VERBS for token in tokens) and not any(token in {"in", "at", "near"} for token in tokens):
        return False
    topic_words = {word for words in TOPICS.values() for word in words}
    if all(token in topic_words or token in _VERBS for token in tokens):
        return False
    return True


def parse_reply(line: str, *, has_place: bool) -> tuple[str, str]:
    text = _norm(line)
    if not text:
        return "empty", ""
    if text in QUIT:
        return "quit", ""
    if text in HELP:
        return "help", ""
    if text in MOVE:
        return "move", ""
    if text in STAY:
        return "stay", ""
    if _has_word(text, "iss") or "space station" in text:
        return "iss", ""

    directed = re.search(
        r"\b(?:happening|weather|risk|look|scan|check|go|move|switch)\b.*\b(?:in|at|near|to)\s+(.+)$",
        text,
    )
    if directed:
        place = extract_place(directed.group(1))
        if looks_like_place(place):
            return "place", place

    if not has_place:
        for topic, words in TOPICS.items():
            if text == topic or text in words:
                return topic, ""
        if looks_like_place(text):
            return "place", extract_place(text)
        return "unknown", text

    for topic, words in TOPICS.items():
        if any(_has_word(text, word) for word in words) or _has_word(text, topic):
            return topic, ""
    if looks_like_place(text):
        return "place", extract_place(text)
    return "unknown", text

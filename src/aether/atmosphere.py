from __future__ import annotations


def field(kind: str, tick: int, width: int, height: int) -> str:
    width = max(20, width)
    height = max(6, height)
    if kind in {"rain", "storm"}:
        return _rain(tick, width, height, storm=kind == "storm")
    if kind in {"clear_night", "twilight"}:
        return _stars(tick, width, height)
    if kind == "snow":
        return _snow(tick, width, height)
    if kind == "fog":
        return _fog(tick, width, height)
    if kind == "cloud":
        return _cloud(tick, width, height)
    return _sun(tick, width, height)


def _rain(tick: int, width: int, height: int, storm: bool) -> str:
    glyphs = "|'`." if not storm else "|/⚡'."
    rows = []
    for y in range(height):
        chars = []
        for x in range(width):
            n = (x * 17 + (y * 3) + tick * 2) % 23
            if n == 0:
                chars.append(glyphs[x % len(glyphs)])
            elif n == 1 and storm:
                chars.append("/")
            else:
                chars.append(" ")
        rows.append("".join(chars))
    return "\n".join(rows)


def _stars(tick: int, width: int, height: int) -> str:
    rows = []
    for y in range(height):
        chars = []
        for x in range(width):
            n = (x * 29 + y * 13) % 47
            blink = (tick + x + y) % 11
            if n == 0 and blink not in {0, 1}:
                chars.append("*")
            elif n == 7 and blink > 3:
                chars.append("·")
            elif n == 19:
                chars.append(".")
            else:
                chars.append(" ")
        rows.append("".join(chars))
    return "\n".join(rows)


def _snow(tick: int, width: int, height: int) -> str:
    rows = []
    for y in range(height):
        chars = []
        for x in range(width):
            n = (x * 11 + y * 5 + tick) % 19
            chars.append("*" if n == 0 else "·" if n == 4 else " ")
        rows.append("".join(chars))
    return "\n".join(rows)


def _fog(tick: int, width: int, height: int) -> str:
    wave = "~˜-."[tick % 4]
    rows = []
    for y in range(height):
        offset = (tick + y) % 6
        rows.append((" " * offset + (wave * ((width // 2) + 2)))[:width])
    return "\n".join(rows)


def _cloud(tick: int, width: int, height: int) -> str:
    blob = "   .--.      .-.     .--.   "
    shift = tick % max(1, len(blob))
    band = (blob[shift:] + blob[:shift]) * (width // 8 + 2)
    rows = [" " * width for _ in range(height)]
    mid = height // 2
    rows[max(0, mid - 1)] = band[:width]
    rows[mid] = ("  (      )   (   )   (      )  " * 8)[:width]
    return "\n".join(rows)


def _sun(tick: int, width: int, height: int) -> str:
    frames = [
        ["    \\   /    ", "  —  ●  —  ", "    /   \\    "],
        ["    |   |    ", "  /  ●  \\  ", "    |   |    "],
    ]
    art = frames[tick % 2]
    rows = [" " * width for _ in range(height)]
    top = max(0, height // 2 - 1)
    for i, line in enumerate(art):
        if top + i < height:
            pad = max(0, (width - len(line)) // 2)
            rows[top + i] = (pad * " " + line).ljust(width)[:width]
    return "\n".join(rows)

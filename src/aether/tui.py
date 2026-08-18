from __future__ import annotations

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Input, RichLog, Static

from aether.atmosphere import field
from aether.collect import build_brief_sync
from aether.models import Brief
from aether.sky import TWILIGHT, Sky, sky_from_brief
from aether.talk import parse_reply
from aether.voice import answer, summary_lines

CSS = """
Screen {
    background: #05070c;
}

Screen.twilight { background: #070b12; }
Screen.rain { background: #02131c; }
Screen.storm { background: #14071a; }
Screen.clear_day { background: #140e04; }
Screen.clear_night { background: #070614; }
Screen.cloud { background: #0b1016; }
Screen.fog { background: #121110; }
Screen.snow { background: #0b141c; }

#hud {
    height: 16;
    padding: 0 1;
}

Screen.rain #hud { background: #03202c; border-bottom: heavy #0ea5e9; }
Screen.storm #hud { background: #1a0824; border-bottom: heavy #d946ef; }
Screen.clear_day #hud { background: #2a1c04; border-bottom: heavy #f59e0b; }
Screen.clear_night #hud { background: #120c28; border-bottom: heavy #8b5cf6; }
Screen.cloud #hud { background: #151b22; border-bottom: heavy #94a3b8; }
Screen.fog #hud { background: #1c1917; border-bottom: heavy #a8a29e; }
Screen.snow #hud { background: #0f2433; border-bottom: heavy #7dd3fc; }
Screen.twilight #hud { background: #0c1220; border-bottom: heavy #64748b; }

#atmos {
    width: 3fr;
    color: #38bdf8;
}
Screen.clear_day #atmos { color: #fbbf24; }
Screen.clear_night #atmos { color: #c4b5fd; }
Screen.storm #atmos { color: #e879f9; }
Screen.cloud #atmos { color: #cbd5e1; }
Screen.fog #atmos { color: #a8a29e; }
Screen.snow #atmos { color: #e0f2fe; }
Screen.twilight #atmos { color: #64748b; }

#vitals {
    width: 3fr;
    padding: 1 2;
}

#place {
    text-style: bold;
    color: #e2e8f0;
    text-align: left;
}

#temp {
    text-style: bold;
    color: #7dd3fc;
    content-align: left middle;
    height: 3;
}

Screen.clear_day #temp { color: #fbbf24; }
Screen.storm #temp { color: #f0abfc; }
Screen.clear_night #temp { color: #ddd6fe; }

#mood {
    color: #94a3b8;
}

#stats {
    width: 3fr;
    padding: 1 2;
}

#risk {
    text-style: bold;
    height: 2;
}
Screen.rain #risk { color: #7dd3fc; }
Screen.clear_day #risk { color: #fbbf24; }
Screen.storm #risk { color: #f0abfc; }

#metrics {
    color: #cbd5e1;
}

#chat {
    height: 1fr;
    background: #05070c;
    border: none;
    padding: 1 2;
    scrollbar-color: #334155;
}

Input {
    dock: bottom;
    background: #020617;
    color: #e2e8f0;
    border: tall #334155;
    padding: 0 2;
}
Screen.rain Input { border: tall #0ea5e9; }
Screen.storm Input { border: tall #d946ef; }
Screen.clear_day Input { border: tall #f59e0b; }
Screen.clear_night Input { border: tall #8b5cf6; }

Footer { background: #020617; color: #64748b; }
"""


class Atmos(Static):
    kind: reactive[str] = reactive("twilight")
    tick: reactive[int] = reactive(0)

    def on_mount(self) -> None:
        self.set_interval(0.14, self._step)

    def _step(self) -> None:
        self.tick += 1
        width = max(self.size.width, 24)
        height = max(self.size.height, 8)
        self.update(field(self.kind, self.tick, width, height))


class AetherApp(App[None]):
    CSS = CSS
    TITLE = "AETHER"
    BINDINGS = [("ctrl+q", "quit", "quit")]

    brief: Brief | None = None
    sky: Sky = TWILIGHT
    loading: bool = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="hud"):
            yield Atmos(id="atmos")
            with Vertical(id="vitals"):
                yield Static("AETHER", id="place")
                yield Static("—°", id="temp")
                yield Static("waiting on a place", id="mood")
            with Vertical(id="stats"):
                yield Static("RISK  —", id="risk")
                yield Static("name a city to recode the sky", id="metrics")
        yield RichLog(id="chat", markup=True, highlight=False, wrap=True)
        yield Input(placeholder="Hyderabad  ·  weather  ·  flights  ·  iss  ·  quit")
        yield Footer()

    def on_mount(self) -> None:
        self.add_class("twilight")
        log = self.query_one("#chat", RichLog)
        log.write("[b #94a3b8]aether[/]  I watch weather, quakes, flights, the ISS, and open events.")
        log.write("[b #94a3b8]aether[/]  Where should I look?")
        self.query_one(Input).focus()

    def _paint_hud(self) -> None:
        sky = self.sky
        for name in ("twilight", "rain", "storm", "clear_day", "clear_night", "cloud", "fog", "snow"):
            self.remove_class(name)
        self.add_class(sky.name)
        self.query_one("#atmos", Atmos).kind = sky.name
        place = self.query_one("#place", Static)
        temp = self.query_one("#temp", Static)
        mood = self.query_one("#mood", Static)
        risk = self.query_one("#risk", Static)
        metrics = self.query_one("#metrics", Static)
        brief = self.brief
        if brief is None:
            place.update("AETHER")
            temp.update("—°")
            mood.update(sky.mood)
            risk.update("RISK  —")
            metrics.update("name a city to recode the sky")
            return
        weather = brief.weather
        degrees = "—" if weather is None or weather.temp_c is None else f"{weather.temp_c:.0f}°"
        condition = "" if weather is None else weather.weather_text
        rain = "—" if weather is None or weather.next_6h_precip_mm is None else f"{weather.next_6h_precip_mm:.1f} mm / 6h"
        iss = "—" if brief.iss is None or brief.iss.distance_km is None else f"{brief.iss.distance_km:.0f} km"
        place.update(brief.place.name.upper())
        temp.update(degrees)
        mood.update(f"{condition}  ·  {sky.mood}")
        risk.update(f"RISK  {brief.risk.level}")
        metrics.update(
            f"{len(brief.flights)} flights    {len(brief.quakes)} quakes    ISS {iss}\n{rain}"
        )

    def _say(self, who: str, text: str) -> None:
        color = "#38bdf8" if who == "aether" else "#94a3b8"
        if self.sky.name == "clear_day" and who == "aether":
            color = "#fbbf24"
        elif self.sky.name == "storm" and who == "aether":
            color = "#e879f9"
        elif self.sky.name == "clear_night" and who == "aether":
            color = "#c4b5fd"
        self.query_one("#chat", RichLog).write(f"[b {color}]{who}[/]  {text}")

    def _speak(self, lines: list[str]) -> None:
        for line in lines:
            self._say("aether", line)

    @on(Input.Submitted)
    def on_submit(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return
        if self.loading:
            self._say("aether", "Wait — still listening to the last place.")
            return
        self._say("you", text)
        self._handle(text)

    def _handle(self, text: str) -> None:
        intent, payload = parse_reply(text, has_place=self.brief is not None)
        if intent == "quit":
            self._speak(["Later."])
            self.exit()
            return
        if intent == "empty":
            self._speak(["Say a city, or weather / flights / quakes / ISS / events."])
            return
        if intent in {"unknown", "help"} and self.brief is None:
            self._speak(["That is not a city. Try Hyderabad, Tokyo, or London."])
            return
        if intent == "unknown":
            self._speak(answer("unknown", self.brief))
            return
        if intent == "help":
            self._speak(answer("help", self.brief))
            return
        if intent == "stay":
            if self.brief is None:
                self._speak(["Name a city first."])
            else:
                self._speak(answer("stay", self.brief))
            return
        if intent == "move":
            self.brief = None
            self.sky = TWILIGHT
            self._paint_hud()
            self._speak(["Where next?"])
            return
        if intent == "place":
            self._begin_listen(payload)
            return
        if self.brief is None:
            self._speak(["Name a city first. I recode the whole screen to that sky."])
            return
        self._speak(answer(intent, self.brief))

    def _begin_listen(self, query: str) -> None:
        self.loading = True
        self._say("aether", f"Listening to {query}…")
        self.load_place(query)

    @work(thread=True, exclusive=True)
    def load_place(self, query: str) -> None:
        try:
            brief = build_brief_sync(query=query)
        except Exception as exc:
            self.call_from_thread(self._listen_failed, query, str(exc))
            return
        self.call_from_thread(self._listen_ok, brief)

    def _listen_failed(self, query: str, _detail: str) -> None:
        self.loading = False
        self._speak([f"No lock on {query}.", "Name a real city."])

    def _listen_ok(self, brief: Brief) -> None:
        self.loading = False
        self.brief = brief
        self.sky = sky_from_brief(brief)
        self._paint_hud()
        self._speak(summary_lines(brief))


def run() -> int:
    AetherApp().run()
    return 0

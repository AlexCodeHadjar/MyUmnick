"""Интернет по смыслу реплики (ADR-0036): погода Open-Meteo, новости SearXNG с текстом статьи."""

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

import pytest

from vtuber.domain import SearchSource, SourcesFound
from vtuber.kernel import EventBus, PluginContext
from vtuber_web_search import WebSearchPlugin
from vtuber_web_search.intent import News, Search, Weather, classify
from vtuber_web_search.weather import city_variants

FORECAST = {
    "current": {
        "temperature_2m": -3.4,
        "apparent_temperature": -8.1,
        "weather_code": 71,
        "wind_speed_10m": 12.0,
    },
    "daily": {
        "temperature_2m_max": [-1.0, 2.0],
        "temperature_2m_min": [-6.0, -2.0],
        "weather_code": [71, 3],
        "precipitation_probability_max": [80, 10],
    },
}
ARTICLE = (
    "<html><head><title>AI news</title></head><body><nav>menu menu</nav><article><h1>AI news</h1>"
    + "<p>A new open model was released today and it beats older models on many tests.</p>" * 5
    + "</article><footer>footer</footer></body></html>"
)


@dataclass(slots=True)
class _Web:
    """Заглушка Open-Meteo, SearXNG и сайта новостей на одном порту; помнит запросы."""

    places: Mapping[str, str] = field(default_factory=lambda: {"Москва": "Moscow"})
    news: list[dict[str, str]] = field(default_factory=list)
    requests: list[str] = field(default_factory=list)

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        target = (await reader.readuntil(b"\r\n\r\n")).decode().split(" ", 2)[1]
        self.requests.append(target)
        body, kind = self._route(target)
        head = f"HTTP/1.1 200 OK\r\nContent-Type: {kind}\r\nContent-Length: {len(body)}\r\n"
        writer.write(f"{head}Connection: close\r\n\r\n".encode() + body)
        await writer.drain()
        writer.close()

    def _route(self, target: str) -> tuple[bytes, str]:
        parts = urlsplit(target)
        query = {key: values[0] for key, values in parse_qs(parts.query).items()}
        if parts.path == "/geo":
            name = self.places.get(query["name"])
            rows = [] if name is None else [{"name": name, "latitude": 55.75, "longitude": 37.62}]
            return json.dumps({"results": rows}).encode(), "application/json"
        if parts.path == "/forecast":
            return json.dumps(FORECAST).encode(), "application/json"
        if parts.path == "/article":
            return ARTICLE.encode(), "text/html; charset=utf-8"
        return json.dumps({"results": self.news}).encode(), "application/json"


@dataclass(slots=True)
class _World:
    web: _Web
    plugin: WebSearchPlugin
    sources: list[tuple[SearchSource, ...]]
    base: str


@asynccontextmanager
async def _world(web: _Web, language: str = "ru") -> AsyncIterator[_World]:
    server = await asyncio.start_server(web.handle, "127.0.0.1", 0)
    base = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
    bus = EventBus()
    sources: list[tuple[SearchSource, ...]] = []

    async def on_sources(event: SourcesFound) -> None:
        sources.append(event.sources)

    bus.subscribe(SourcesFound, on_sources)
    settings = {
        "searxng_url": base,
        "geocoding_url": f"{base}/geo",
        "forecast_url": f"{base}/forecast",
        "timeout_s": 2.0,
    }
    plugin = WebSearchPlugin()
    await plugin.setup(PluginContext("web_search", bus, settings, language=language))
    try:
        yield _World(web, plugin, sources, base)
    finally:
        await plugin.shutdown()
        server.close()


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("Какая сегодня погода в Москве?", Weather("Москве", "today")),
        ("Будет ли завтра дождь?", Weather(None, "tomorrow")),
        ("What's the weather in New York?", Weather("New York", "now")),
        ("Расскажи новости про космос", News("космос")),
        ("What's the news about AI?", News("AI")),
        ("Что нового в мире?", News("")),
        ("Какой сегодня курс евро?", Search("Какой сегодня курс евро")),
        ("Who won the match yesterday?", Search("Who won the match yesterday")),
        ("Найди в интернете рецепт борща", Search("рецепт борща")),
    ],
)
def test_intent_is_recognised(text: str, intent: object) -> None:
    assert classify(text, auto=True) == intent


@pytest.mark.parametrize(
    "text",
    ["Как дела?", "Расскажи анекдот", "I love you", "Помнишь, как меня зовут?", "Спой песню"],
)
def test_ordinary_replies_never_search(text: str) -> None:
    assert classify(text, auto=True) is None


def test_explicit_only_mode_ignores_weather_words() -> None:
    assert classify("Какая погода в Москве?", auto=False) is None


def test_city_variants_cover_russian_cases() -> None:
    assert "Москва" in city_variants("Москве")
    assert "Казань" in city_variants("Казани")
    assert "Россия" in city_variants("России")


async def test_weather_in_moscow_has_real_numbers_and_source() -> None:
    async with _world(_Web()) as world:
        context = await world.plugin.context("Какая сегодня погода в Москве?")

    assert context is not None
    assert "Moscow" in context
    assert "от -6 до -1 °C" in context
    assert "вероятность осадков 80%" in context
    assert world.sources == [(SearchSource("Open-Meteo", "https://open-meteo.com/"),)]
    assert world.web.requests[0].startswith("/geo?name=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B5")


async def test_weather_now_in_english_uses_home_city() -> None:
    async with _world(_Web(), language="en") as world:
        context = await world.plugin.context("What's the weather like?")

    assert context is not None
    assert "Now in Moscow: light snow, -3 °C, feels like -8 °C" in context


async def test_unknown_city_is_said_honestly() -> None:
    async with _world(_Web(places={})) as world:
        context = await world.plugin.context("Какая погода в Нигдеграде?")

    assert context is not None
    assert "не нашёлся" in context


async def test_news_reads_the_first_article() -> None:
    web = _Web()
    async with _world(web, language="en") as world:
        web.news = [{"title": "AI news", "url": f"{world.base}/article", "content": "A new model"}]
        context = await world.plugin.context("What's the news about AI?")

    assert context is not None
    assert "Text of the first article:" in context
    assert "beats older models" in context
    assert "menu menu" not in context
    search = next(r for r in web.requests if r.startswith("/search"))
    assert "categories=news" in search
    assert "time_range=day" in search
    assert "language=en" in search


async def test_ordinary_reply_does_not_touch_the_network() -> None:
    web = _Web()
    async with _world(web) as world:
        assert await world.plugin.context("Как дела?") is None
    assert web.requests == []

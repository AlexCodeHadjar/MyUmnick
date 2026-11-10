"""Новости (ADR-0036): свежая выдача SearXNG (категория news, за сутки) и текст первой статьи.

Текст статьи достаёт trafilatura без браузера — в потоке, разбор HTML не держит цикл событий.
Страница — чужой текст: разметка вычищена, текст обрезан, страница с попыткой командовать моделью
отбрасывается целиком.
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Final

import httpx
import trafilatura
from pydantic import BaseModel, ConfigDict, Field

from vtuber.domain import looks_like_attack

MAX_PAGE_BYTES: Final = 2_000_000
_QUOTES: Final = re.compile(r"[«»\[\]<>{}|]")


class Result(BaseModel):
    """Строка выдачи SearXNG."""

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    url: str = ""
    content: str = ""


class Answer(BaseModel):
    """Ответ SearXNG в формате json."""

    model_config = ConfigDict(extra="ignore")

    results: list[Result] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class NewsQuery:
    """Запрос новостей: тема (пусто — главное), язык издания, сколько статей прочитать."""

    topic: str
    language: str
    read_pages: int


def clean(text: str, limit: int) -> str:
    """Без кавычек и скобок (чужой текст не закроет цитату) и не длиннее `limit`."""
    return " ".join(_QUOTES.sub("", text).split())[:limit]


def news_params(query: NewsQuery, home_city: str) -> dict[str, str]:
    """Параметры SearXNG: без темы — главные новости страны языка издания."""
    fallback = "top news" if query.language == "en" else f"главные новости {home_city}"
    return {
        "q": query.topic or fallback,
        "format": "json",
        "categories": "news",
        "time_range": "day",
        "language": query.language,
    }


def extract_text(html: str) -> str | None:
    """Основной текст статьи без меню и рекламы; не вышло — None."""
    return trafilatura.extract(html, include_comments=False, include_tables=False)


async def read_page(client: httpx.AsyncClient, url: str, limit: int) -> str | None:
    """Текст статьи по адресу; сбой, не HTML или атака на модель — None (выдача остаётся).

    Ошибки сети глушатся: прочитать статью — дополнение к выдаче, а не условие ответа.
    """
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    if (
        "html" not in response.headers.get("content-type", "")
        or len(response.content) > MAX_PAGE_BYTES
    ):
        return None
    text = await asyncio.to_thread(extract_text, response.text)
    if not text or looks_like_attack(text):
        return None
    return clean(text, limit)

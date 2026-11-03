"""Хранилище фактов в SQLite с векторным поиском sqlite-vec (ADR-0015).

Факты и векторы — в одном файле: таблица `facts` и виртуальная `fact_vectors` (vec0, косинус) с
тем же rowid. Соединение одно; запросы идут в потоке (R-34) под замком — sqlite3 не любит
параллельную работу с одним соединением.
"""

from __future__ import annotations

import asyncio
import sqlite3
import struct
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Final, Self

from vtuber.domain import Fact, FactHit, FactId, FactSource, MemoryUnavailable, Vector

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

SCHEMA: Final = """
create table if not exists meta (key text primary key, value text not null);
create table if not exists facts (
    id integer primary key,
    text text not null,
    source text not null,
    importance real not null,
    created_at text not null,
    note text not null default ''
);
"""
SEARCH: Final = """
select f.id, f.text, f.source, f.importance, f.created_at, f.note, v.distance
from fact_vectors v join facts f on f.id = v.rowid
where v.embedding match ? and k = ?
order by v.distance
"""


class SqliteVecStore:
    """Реализует MemoryStorePort для векторов размерности `dimensions`; файл — `path`.

    База не открывается (нет каталога, нет расширения, другая размерность) — адаптер не падает
    при старте, а отвечает `MemoryUnavailable`: ход идёт без памяти.
    """

    def __init__(self, path: Path, dimensions: int) -> None:
        self._path = path
        self._dimensions = dimensions
        self._db: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._unavailable = "Хранилище памяти не открыто: адаптер используется вне `async with`"

    async def __aenter__(self) -> Self:
        try:
            self._db = await asyncio.to_thread(self._open)
        except (sqlite3.Error, OSError, ImportError, ValueError) as error:
            self._unavailable = f"Хранилище памяти {self._path} не открылось: {error}"
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        db, self._db = self._db, None
        if db is not None:
            await asyncio.to_thread(self._locked_close, db)

    async def add(self, fact: Fact, vector: Vector) -> FactId:
        """Факт и его вектор — одной транзакцией."""
        db = self._ready(vector)
        return await asyncio.to_thread(self._insert, db, fact, vector)

    async def all_facts(self) -> list[Fact]:
        """Все факты по порядку записи."""
        return await asyncio.to_thread(self._read_all, self._connection())

    async def remove_note(self, note: str) -> None:
        """Факты заметки — из таблицы и векторов одной транзакцией."""
        await asyncio.to_thread(self._delete_note, self._connection(), note)

    def _connection(self) -> sqlite3.Connection:
        if self._db is None:
            raise MemoryUnavailable(self._unavailable)
        return self._db

    def _read_all(self, db: sqlite3.Connection) -> list[Fact]:
        with self._lock:
            rows = db.execute(
                "select text, source, importance, created_at, note from facts order by id"
            ).fetchall()
        return [_fact(*row) for row in rows]

    def _delete_note(self, db: sqlite3.Connection, note: str) -> None:
        with self._lock, db:
            ids = db.execute("select id from facts where note = ?", (note,)).fetchall()
            db.executemany("delete from fact_vectors where rowid = ?", ids)
            db.executemany("delete from facts where id = ?", ids)

    async def search(self, query: Vector, limit: int) -> list[FactHit]:
        """KNN по косинусу; близость = 1 − расстояние."""
        db = self._ready(query)
        if limit < 1:
            msg = f"limit поиска — не меньше 1, получено {limit}"
            raise ValueError(msg)
        return await asyncio.to_thread(self._knn, db, query, limit)

    def _ready(self, vector: Vector) -> sqlite3.Connection:
        if self._db is None:
            raise MemoryUnavailable(self._unavailable)
        if len(vector) != self._dimensions:
            msg = f"вектор размерности {len(vector)}, хранилище — {self._dimensions}"
            raise ValueError(msg)
        return self._db

    def _open(self) -> sqlite3.Connection:
        # Типов у sqlite_vec нет; от него нужна только загрузка расширения в соединение.
        import sqlite_vec  # type: ignore[import-untyped]  # noqa: PLC0415 — ядро без группы `memory`

        db = sqlite3.connect(self._path, check_same_thread=False)
        try:
            db.enable_load_extension(True)  # noqa: FBT003 — позиционный API sqlite3
            sqlite_vec.load(db)
            db.enable_load_extension(False)  # noqa: FBT003
            # Иначе удалённый текст остаётся в свободных страницах файла, и «очистка» — неправда.
            db.execute("pragma secure_delete = on")
            db.executescript(SCHEMA)
            _add_note_column(db)
            self._check_dimensions(db)
        except BaseException:
            db.close()
            raise
        return db

    def _check_dimensions(self, db: sqlite3.Connection) -> None:
        row = db.execute("select value from meta where key = 'dimensions'").fetchone()
        if row is None:
            dims = self._dimensions
            db.execute(
                f"create virtual table if not exists fact_vectors using "
                f"vec0(embedding float[{dims}] distance_metric=cosine)"
            )
            db.execute("insert into meta values ('dimensions', ?)", (str(dims),))
            db.commit()
        elif int(row[0]) != self._dimensions:
            msg = (
                f"в базе векторы размерности {row[0]}, эмбеддер — {self._dimensions}: модель "
                "сменилась, старые векторы несравнимы — нужна переиндексация"
            )
            raise ValueError(msg)

    def _insert(self, db: sqlite3.Connection, fact: Fact, vector: Vector) -> FactId:
        with self._lock, db:
            cursor = db.execute(
                "insert into facts (text, source, importance, created_at, note)"
                " values (?, ?, ?, ?, ?)",
                (
                    fact.text,
                    fact.source.value,
                    fact.importance,
                    fact.created_at.isoformat(),
                    fact.note,
                ),
            )
            fact_id = cursor.lastrowid
            if fact_id is None:  # pragma: no cover — sqlite3 всегда даёт rowid после insert
                msg = "SQLite не вернул id нового факта"
                raise sqlite3.DatabaseError(msg)
            db.execute(
                "insert into fact_vectors (rowid, embedding) values (?, ?)",
                (fact_id, _blob(vector)),
            )
        return FactId(fact_id)

    def _knn(self, db: sqlite3.Connection, query: Vector, limit: int) -> list[FactHit]:
        with self._lock:
            rows = db.execute(SEARCH, (_blob(query), limit)).fetchall()
        return [FactHit(FactId(row[0]), _fact(*row[1:6]), 1.0 - row[6]) for row in rows]

    def _locked_close(self, db: sqlite3.Connection) -> None:
        with self._lock:
            db.close()


def _fact(text: str, source: str, importance: float, created: str, note: str) -> Fact:
    return Fact(text, FactSource(source), importance, datetime.fromisoformat(created), note=note)


def _add_note_column(db: sqlite3.Connection) -> None:
    """База прошлой версии: столбца нет; факты из неё перенесёт в заметки `reconcile`."""
    columns = {row[1] for row in db.execute("pragma table_info(facts)")}
    if "note" not in columns:
        db.execute("alter table facts add column note text not null default ''")
        db.commit()


def _blob(vector: Vector) -> bytes:
    """Вектор → float32 little-endian: формат vec0 (как `sqlite_vec.serialize_float32`)."""
    return struct.pack(f"<{len(vector)}f", *vector)

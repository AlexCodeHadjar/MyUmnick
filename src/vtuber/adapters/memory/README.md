# adapters/memory — эмбеддер e5 и хранилище фактов sqlite-vec

## Ответственность
Реализации портов долговременной памяти (ADR-0015): `E5Embedder` — тексты в векторы
multilingual-e5-small (ONNX, CPU), `SqliteVecStore` — факты с векторами в одном файле SQLite и
KNN по косинусу. НЕ решает, когда искать и что запоминать (сервис памяти и гейт — S-10.4,
S-10.5), не строит промпт.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `ObsidianVault(root)` | `MemoryVaultPort` на папке с Markdown (ADR-0020): заметка факта — атомарно, чаты и дневник — дописыванием; битая заметка — предупреждение |
| `E5Embedder(cfg)` | `EmbedderPort` в `async with`: модель грузится один раз с прогревом; нет файлов — `MemoryUnavailable` на запрос |
| `E5Config` | `model_dir` (`model.onnx`, `tokenizer.json`), `dimensions` (384), `threads`, `max_tokens` (≤ 512), `batch_size` |
| `SqliteVecStore(path, dimensions)` | `MemoryStorePort` в `async with`: открывает или создаёт базу; не открылась — `MemoryUnavailable` |

## Зависимости
- Порты `EmbedderPort`, `MemoryStorePort`; домен `Fact`, `FactHit`, `Vector`, `EmbedKind`,
  `MemoryUnavailable`; kernel `ConfigSection`.
- Группа `memory` (ADR-0015): `onnxruntime`, `tokenizers`, `numpy`, `sqlite-vec` — импорт
  ленивый, пакет импортируется и без неё.

## События
- Публикует: —
- Слушает: —

## Инварианты
- Контракты портов памяти (`tests/contract/test_embedder_contract.py`,
  `test_memory_store_contract.py`) проходят и для e5 (`-m slow`, нужна модель), и для sqlite-vec.
- e5: префикс `query: `/`passage: ` по `EmbedKind`; mean pooling по маске внимания; единичная
  норма; размерность модели сверяется с конфигом при загрузке.
- sqlite-vec: факт и вектор — одной транзакцией с общим rowid; близость = 1 − косинусное
  расстояние; размерность записана в базе — другая модель → `MemoryUnavailable` («нужна
  переиндексация»); база переживает перезапуск (`tests/integration/test_memory_adapters.py`).
- Работа с моделью и базой — в потоке (R-34); соединение SQLite одно, под замком.

## Производительность
- Машина разработки: запрос e5 — 5.4 мс (2 потока), пакет из 8 фактов — 39 мс; поиск топ-5 —
  p95 3.5 мс на 2000 фактах, 11.9 мс на 10 000; запрос e5 + поиск — p95 9.5 / 17.7 мс (бюджет
  «гейт + поиск» — 40 мс). Добавление факта ≈ 7 мс (коммит на факт).

## Как расширять
- Другая модель эмбеддингов: свой адаптер `EmbedderPort` + случай в
  `tests/contract/memory_factories.py`; старая база при смене размерности не откроется —
  переиндексация (S-10.4).
- Удаление и правка фактов (дедупликация, S-10.4) — расширить порт и контракт вместе.

## Связанные документы
ADR-0015, `docs/architecture.md` (Порты), `docs/performance.md` (бюджет поиска), T-12

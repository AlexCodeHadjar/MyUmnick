# ADR-0015: долговременная память — multilingual-e5-small в ONNX на CPU и sqlite-vec
- Статус: принято
- Дата: 2026-10-29

## Контекст
Этап 10 (FR-10): витюбер помнит факты о пользователе между запусками. Бюджет — «решение о
поиске + поиск ≤ 40 мс» (`docs/performance.md`), TTFT p95 с памятью — не больше +40 мс.
Видеокарта отдана LLM (T-11): эмбеддинги — на CPU. Порты уже есть (S-10.1): `EmbedderPort`,
`MemoryStorePort`. Стек (`docs/stack.md`): multilingual-e5-small, хранилище — sqlite-vec.

## Рассмотренные варианты
Модель: **multilingual-e5-small** (MIT, 384 измерения, русский — в обучении) против bge-m3
(1024 измерения, в ~5 раз тяжелее на CPU). Для коротких фактов о пользователе small хватает.

Как запускать e5:
1. **ONNX Runtime + `tokenizers`** — официальная ONNX-сборка из репозитория модели
   (`onnx/model.onnx`, fp32, 470 МБ), onnxruntime уже есть у Piper (ADR-0013); `tokenizers` —
   Rust-колесо HF (Apache-2.0). Замер на машине разработки (2 потока): запрос — 5.4 мс, пакет
   из 8 фактов — 39 мс.
2. sentence-transformers на torch (torch есть у Silero) — тянет transformers (сотни МБ), а
   выигрыша по скорости на CPU нет.
3. Квантованные ONNX из репозитория: `model_qint8_avx512_vnni.onnx` требует AVX512-VNNI
   (процессор целевой машины неизвестен), `model_O4.onnx` — fp16 для GPU. Не берём.

Хранилище: **sqlite-vec 0.1.9** (MIT/Apache-2.0; расширение SQLite, KNN по косинусу в `vec0`)
против FAISS (отдельный индекс рядом с базой фактов, синхронизировать два хранилища) и полного
перебора в numpy (хватает на тысячи фактов, но факты и векторы опять в разных местах). Один
файл SQLite с фактами и векторами проще бэкапить и переносить.

## Решение
- Необязательная группа `memory`: `numpy`, `onnxruntime`, `tokenizers`, `sqlite-vec`
  (`uv sync --all-extras`, как у `silero` и `piper`). `tokenizers` транзитивно приносит
  `huggingface-hub` — сеть им не используется: токенизатор читается из файла.
- Модель — `models/memory/e5-small/` (вне git): `model.onnx`, `tokenizer.json`, `config.json` из
  `https://huggingface.co/intfloat/multilingual-e5-small/tree/main/onnx` (ревизия `614241f`).
- `E5Embedder`: префиксы e5 (`query: ` / `passage: `) добавляет адаптер по `EmbedKind`;
  mean pooling по маске внимания, нормировка; потоки ONNX — из конфига; инференс — в потоке
  (R-34). Импорт onnxruntime/tokenizers — ленивый: ядро без группы `memory` запускается.
- `SqliteVecStore`: таблица фактов + `vec0(embedding float[N] distance_metric=cosine)` с тем же
  rowid; близость = 1 − косинусное расстояние; соединение одно, доступ из потоков под
  замком. Размерность записывается в базу: другая модель — `MemoryUnavailable` с подсказкой
  (векторы старой модели несравнимы с новыми).

## Последствия
- `docs/licenses.md`: e5-small — MIT; sqlite-vec — MIT/Apache-2.0; tokenizers,
  huggingface-hub — Apache-2.0; onnxruntime — MIT.
- Контракты портов памяти прогоняются на настоящих адаптерах: e5 — медленный (`-m slow`,
  загрузка модели), без файла модели — пропуск с причиной; sqlite-vec — быстрый.
- Подключение к ходу (гейт поиска, факты в промпт) — S-10.5; секция `[memory]` конфига — там же.

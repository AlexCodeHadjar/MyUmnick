# adapters/setup — загрузка файлов мастера

## Ответственность
Реализация `FileFetcher` по HTTP. Не проверяет суммы и не пишет на диск: это `application/setup/Installer`.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `HttpFetcher(cfg)`, `HttpFetcherConfig` | `fetch(url, offset)`: докачка через Range; сервер без Range — начало пропускается |

## Инварианты
- Сетевой сбой — `SetupFailed` с текстом для пользователя. Сеть используется только по согласию (NFR-06).

## Связанные документы
S-13.2, `application/setup/README.md`

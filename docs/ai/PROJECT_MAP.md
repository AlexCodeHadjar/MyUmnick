# PROJECT MAP

> Автогенерация: `python tools/gen_map.py`. Не редактировать.

## src/vtuber
Ядро локального ИИ-витюбера.

## src/vtuber/adapters
Адаптеры: реализации портов для конкретных движков.

## src/vtuber/adapters/llm
Адаптеры языковых моделей (LLMPort).

## src/vtuber/adapters/memory
Адаптеры долговременной памяти: эмбеддеры и хранилища.

## src/vtuber/adapters/stt
Адаптеры распознавания речи (STTPort).

## src/vtuber/adapters/tts
Адаптеры синтеза речи (TTSPort).

## src/vtuber/application
Прикладной слой: сценарии диалога и конвейер ответа поверх портов.

## src/vtuber/bootstrap
Корень композиции: сборка графа объектов и точка входа.

## src/vtuber/domain
Доменный слой: неизменяемые сущности и значения диалога, речи и эмоций.

## src/vtuber/gateway
Шлюз: WebSocket-сервер и протокол обмена с UI.

## src/vtuber/kernel
Общие механизмы ядра: шина событий, реестр, телеметрия, конфиг, логи.

## src/vtuber/ports
Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру.

# Кадры персонажа, часть 3 — радио: сидит на музыкальном ящике (задание для ChatGPT)

> Замена «поёт стоя» для режима радио (2026-11-17, по просьбе пользователя: «слишком дёргается»).
> **Формат, масштаб, вступление, хвост, проверки — как в [FRAMES.md](FRAMES.md), разделы 2, 4, 6, 7.**
> Поведение — [BEHAVIOR.md](BEHAVIOR.md) §8.

## Идея
Персонаж **сидит на большом ретро-музыкальном ящике** (джукбокс), в наушниках на шее, и **медленно
болтает ножками** в такт музыке. Спереди на ящике — **пустое тёмное табло**: на нём программа сама пишет
название песни или станции. Движения **плавные и мелкие**, без рывков: между соседними кадрами меняется
совсем немного, и цикл замыкается без скачка (кадр 6 плавно переходит в кадр 1).

Пока кадров нет, программа показывает спокойную замену (`sing` медленным циклом, без подскоков).

## 0. Что нужно

| Файл | Что | Сколько |
|---|---|---|
| `jukebox.png` | основной кадр: сидит на ящике, ножки внизу | 1 |
| `jukebox_1.png … jukebox_6.png` | цикл: ножки медленно качаются, голова чуть кивает | 6 |
| `jukebox_blink.png` | как `jukebox.png`, глаза закрыты | 1 |

Всего 8 кадров.

## 1. Ящик — одинаковый во ВСЕХ кадрах (важно)
Ящик **не двигается ни на пиксель** — двигается только персонаж. Иначе табло с надписью будет «прыгать».
- **Ящик:** ретро-джукбокс с закруглённым верхом, тёмно-синий корпус (как плащ), голубая неоновая
  подсветка по краю (как огоньки-рожки), под табло — решётка динамика.
- **Размер и место на холсте 1024×1536:** ящик занимает нижние ~40% холста, от x≈0,15 до x≈0,85
  ширины; низ ящика — на нижней линии с отступом ~3% (как ступни `stand`).
- **Табло:** прямоугольник **строго пустой и однотонный** (цвет #0B1020, без текста, бликов и рисунка),
  по центру передней стенки. Границы — доли холста: **x от 0,28 до 0,72, y от 0,74 до 0,80**. Программа
  пишет название в этом прямоугольнике.
- Персонаж сидит на крышке ящика: сиденье — на y≈0,60 холста, ноги свешиваются по передней стенке, **не
  закрывая табло**.

## 2. Референсы
`character-reference.png`, `sit_edge.png` (как сидит), `sing.png` (наушники на шее). В вступление чата
добавьте фразу про наушники из [FRAMES-2.md](FRAMES-2.md) («Общая деталь для §1–2»).

## 3. Промпты

`jukebox.png`:
```
Full body, the same scale as the attached sit_edge.png. The character sits on the top of a big retro
jukebox music box, headphones resting around the neck, hands resting on the lid on both sides, legs
hanging down along the front of the box, relaxed and happy, eyes softly half-closed, enjoying music.
The jukebox: dark-blue body like the cloak, rounded top, soft glowing cyan neon trim like the horn flames,
a speaker grille below. On the front of the box there is an EMPTY flat display panel, a plain solid
dark rectangle (#0B1020) with nothing on it, centered, spanning 28%-72% of the image width and 74%-80% of
the image height. The box occupies the bottom 40% of the canvas from 15% to 85% of the width, its
bottom on the bottom line. The legs do not cover the display panel. Canvas 1024x1536, vertical.
```
`jukebox_1.png … jukebox_6.png` — по одному, после `jukebox.png`:
```
Exactly the same image as the previous jukebox.png — the jukebox, the display panel and the character's
position are identical to the pixel — but this is frame {N} of 6 of a slow, gentle loop of swinging the
legs to the music: {legs}. The head nods only very slightly, the hands stay on the lid. The change from
the previous frame is small and smooth. Canvas 1024x1536, vertical.
```
Вместо `{legs}`:
1. `both legs hang straight down`;
2. `the right leg swings a little forward, the left a little back`;
3. `the right leg swings forward a bit more, the left back a bit more, head tilted slightly right`;
4. `both legs hang straight down again`;
5. `the left leg swings a little forward, the right a little back`;
6. `the left leg swings forward a bit more, the right back a bit more, head tilted slightly left`.

`jukebox_blink.png`:
```
Exactly the same image as the previous jukebox.png — identical to the pixel — but both eyes are closed
(a soft curved line each). Nothing else changes.
```
К каждому промпту — хвост из FRAMES.md §4.

## 4. Проверки
- Ящик и табло **совпадают во всех 8 кадрах** (наложите два кадра с прозрачностью 50% — ящик не
  двоится).
- Табло пустое и однотонное, ноги его не закрывают.
- Соседние кадры отличаются немного: ноги на 5–10°, голова на 2–3°.
- Фон прозрачный, без ореола.

Готовые кадры — в папку с этими именами, пришлите путь.

# Кадры на перегенерацию (2026-11-17)

> **Сводное задание на все кадры — [FRAMES.md](FRAMES.md)** (2026-11-17). Этот файл — история.

Из 67 картинок второй генерации (`.codex/generated_images/01a1e86d…`) в пакет вошли 31 кадр (ходьба, сидение
на краю, стояние, «держат мышью», сон, полёт, «висит», полуприкрытые глаза сидя). Ниже — что переделать.
Нумерация — по времени создания файла.

## Что было не так
- **Дымный ореол вместо прозрачного фона.** Вокруг персонажа тёмное полупрозрачное облако, у № 59 фон вообще
  непрозрачный. Ореол сливается с телом, поэтому его не вырезать без порчи рисунка.
- **Буква «z» из промпта сна** попала в кадры ходьбы и стояния (№ 0–6, 12–15). Её я убрал сам, эти кадры
  в пакете.

## Перегенерировать
| Файл | Было (№) | Беда |
|---|---|---|
| `stand_talk_1.png`, `stand_talk_2.png`, `stand_talk_3.png` | 43, 46, 50, 59 | ореол; у 59 непрозрачный фон |
| `sit_edge_talk_1.png`, `sit_edge_talk_2.png`, `sit_edge_talk_3.png` | 39, 48, 64 | ореол |
| `laydown_talk_1.png`, `laydown_talk_2.png`, `laydown_talk_3.png` | 41, 53, 61 | ореол, тёмное пятно под телом |
| `stand_blink_1.png` | 45, 54 | ореол |
| `laydown_blink_1.png` | 51, 62 | ореол, тёмный фон |

Кадр № 52 (лёжа, рот открыт) чистый, но он один, а рту нужны все три уровня. Перегенерируйте `laydown_talk`
полностью.

## Как просить
Генерируйте **в новом чате**, приложив к первому сообщению картинку позы из пакета — `stand.png`,
`sit_edge.png` или `laydown.png` из папки `character-poses`. Каждый кадр — отдельным сообщением.
В конце **каждого** промпта — хвост против прошлых бед:

```
Output a clean cut-out: a fully transparent background (alpha 0) everywhere outside the character —
no glow halo, no smoke, no shadow, no dark aura, no vignette, no background color. The blue flames keep
their own light but do not spill onto the background. No letters, no "z", no text, no symbols.
Keep the exact same canvas (1024x1536), the same scale and the same position of the character as the
reference image. PNG, 1024x1536.
```

### Рот — `{pose}_talk_1…3` (для `stand`, `sit_edge`, `laydown`)
```
Exactly the same image as the attached {pose} reference — identical pose, framing, scale and position of
every pixel — but the mouth on the mask is {mouth}. Nothing else changes.
```
Вместо `{mouth}`: кадр 1 — `slightly open (a small dark oval)`, кадр 2 — `open as if saying "ah"`,
кадр 3 — `wide open, excited`. Затем хвост выше.

### Полуприкрытые глаза — `stand_blink_1`, `laydown_blink_1`
```
Exactly the same image as the attached {pose} reference — identical pose, framing, scale and position of
every pixel — but both eyes on the mask are half closed (halfway through a blink). Nothing else changes.
```
Затем хвост выше.

Готовые кадры — в любую папку с этими именами. Подгоню и проверю так же.

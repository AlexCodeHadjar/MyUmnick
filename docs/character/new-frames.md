# Новые кадры (2026-11-17): «тыкает пальцем», мордашка для угла окна, «гладят»

Нужны для двух новых возможностей:
- **спутник «тыкает» в кнопки и значки.** Сейчас вместо этой позы — `lean_side`, облокотился;
- **мордашка в углу окна программы.** Сейчас она вырезана из `stand`: моргание и рот — только одним кадром.

## Референсы — приложить к ПЕРВОМУ сообщению нового чата
Из папки `C:\Users\Alast\Documents\Codex\2026-11-16\x20-6\outputs\character-poses\`:
1. `character-reference.png` — эталонный лист персонажа;
2. `stand.png` — масштаб и стиль;
3. для мордашки дополнительно `stand_talk.png` и `stand_blink.png`.

Первое сообщение:
```
These attached images are the exact reference for the character: the hooded figure with a cream mask,
two black oval eyes and blue flame horns. Keep the design, colors, line style and proportions identical
in every image I ask for next. Do not add any background.
```

Хвост — в конце **каждого** следующего промпта. Он против бед прошлой генерации: дымного ореола, «z» и
съехавшего масштаба.
```
Output a clean cut-out: a fully transparent background (alpha 0) everywhere outside the character —
no glow halo, no smoke, no shadow, no dark aura, no vignette, no background color. The blue flames keep
their own light but do not spill onto the background. No letters, no "z", no text, no symbols.
Same character scale as the attached stand.png. PNG.
```

---

## 1. Тычет пальцем — `poke.png` и `poke_1.png … poke_3.png`
Точка опоры программы — **кончик пальца**: он должен быть справа, на уровне груди (примерно 88% ширины
и 42% высоты кадра).

`poke.png`:
```
Full body, 3/4 view facing RIGHT, floating slightly (feet not on the ground). Pose: leaning forward and
poking something in front of him with the index finger of the right arm stretched straight to the
RIGHT, curious playful expression. The fingertip is at the right side of the image at about chest
height (about 88% of the width, 42% of the height). Canvas 1024x1536, vertical.
```
Затем хвост.

`poke_1.png … poke_3.png` — цикл «тык-тык». Отправлять сразу после `poke.png`, по одному:
```
Using the previous poke image as the reference, draw frame {N} of 3 of a looping poke: frame 1 — the arm
pulled back a little, finger 5% further from the target; frame 2 — the finger touching the target exactly
where it was in poke.png; frame 3 — the finger pressing in, the cloak and flames jolting slightly.
The head and body stay in place, only the arm and the cloak move. Canvas 1024x1536, vertical.
```
Затем хвост.

## 2. Мордашка для угла окна — `head.png`, `head_talk_1…3.png`, `head_blink_1.png`, `head_blink.png`
Крупный план: рожки, капюшон, маска и бант, **квадрат 1024×1024**, персонаж по центру и одинаково во всех
кадрах.

`head.png`:
```
Close-up portrait of the same character: the blue flame horns, the hood, the cream mask and the bow of
the cloak, 3/4 view facing slightly to the RIGHT, calm friendly expression, mouth closed. The horns'
tips near the top edge, the bow near the bottom edge, centered. Square canvas 1024x1024.
```
Затем хвост.

Дальше — по одному, после `head.png`:
```
Exactly the same image as the previous head.png — identical framing, scale and position of every
pixel — but {change}. Nothing else changes. Square canvas 1024x1024.
```
Затем хвост. Вместо `{change}`:
- `head_talk_1.png` — `the mouth on the mask is slightly open (a small dark oval)`;
- `head_talk_2.png` — `the mouth is open as if saying "ah"`;
- `head_talk_3.png` — `the mouth is wide open, excited`;
- `head_blink_1.png` — `both eyes are half closed (halfway through a blink)`;
- `head_blink.png` — `both eyes are closed (a soft curved line each)`.

---

Готовые картинки — в любую папку с этими именами, пришлите путь. Подгоню, проверю совмещение и добавлю
во встроенного персонажа. Кадры с ореолом или со сдвигом верну на перегенерацию.

## 3. Гладят — `pet.png`, `pet_1.png`, `pet_2.png`
Когда пользователь кликает по спутнику, тот довольно жмурится. Точка опоры — **ступни, как у `stand.png`**:
та же линия пола и тот же масштаб. Пока кадра нет, программа показывает `stand` с закрытыми глазами.

`pet.png`:
```
Same character, full body, standing exactly like the attached stand.png (same scale, same feet position
on the bottom line). Pose: being petted on the head — eyes closed in two happy upward curves, head tilted
slightly toward the hand, shoulders raised in delight, small pink blush on the mask, the blue flame horns
glow a little brighter and curl happily. No hand drawn. Canvas 1024x1536, vertical.
```
Затем хвост.

`pet_1.png`, `pet_2.png` — сразу после `pet.png`, по одному:
```
Using the previous pet image as the reference, draw frame {N} of 2 of a tiny happy wiggle: frame 1 —
the body sways slightly to the left, frame 2 — slightly to the right; the feet stay exactly in place.
Canvas 1024x1536, vertical.
```
Затем хвост.

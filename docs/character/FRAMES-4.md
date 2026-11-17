# Кадры персонажа, часть 4 — переходы между позами для анимации 10/10 (задание для GPT или Gemini)

> 2026-11-18. Итог трёх раундов субагента-критика плавности ([ANIMATION.md](ANIMATION.md)). Кодом анимация
> доведена до **7,5–8/10**: разворот, поглаживание и покой — 8,5–9. Дальше упираемся в **кадры**: при
> переходах меняется строение тела (руки, ноги, опора), и сжатие, растяжка и растворение этого не скроют.
> Нужны **9 промежуточных кадров**. Программа уже умеет их проигрывать: кладёте файлы — переход
> становится плавным без правки кода.
>
> **Формат, масштаб, вступление, «хвост», проверки — как в [FRAMES.md](FRAMES.md), разделы 2, 4, 6, 7.**

## 0. Что нужно — сводка

| № | Файл | Переход | Что на кадре | Опора (низ кадра) |
|---|---|---|---|---|
| 1 | `laydown_to_stand_1.png` | лежит → стоит | приподнялся на локтях, голова поднята, ноги ещё лежат | ступни, как `stand` |
| 2 | `laydown_to_stand_2.png` | лежит → стоит | на одном колене, другая нога выставлена вперёд, рука упирается в пол | ступни, как `stand` |
| 3 | `stand_to_sit_corner_1.png` | стоит → сидит, обняв колени | присел наполовину, руки тянутся к коленям, плащ расходится | низ, как `sit_corner` |
| 4 | `walk_to_stand_1.png` | шёл → стоп | ноги сходятся, плащ по инерции качнулся вперёд | ступни, как `stand` |
| 5 | `stand_to_wave_1.png` | стоит → машет | рука поднята до плеча, ладонь ещё не раскрыта | ступни, как `stand` |
| 6 | `stand_to_held_1.png` | стоит → схватили | испуганно вытянулся вверх, руки и ноги дёрнулись, глаза широко открыты | кончик капюшона, как `held` |
| 7 | `float_to_stand_1.png` | приземлился → встаёт | присел после приземления, колени полусогнуты, руки в стороны для равновесия | ступни, как `stand` |
| 8 | `sit_edge_to_stand_1.png` | сидит на краю → встаёт | оттолкнулся руками от края, тело подалось вперёд, ноги ищут опору | ступни, как `stand` |
| 9 | `stand_to_lean_side_1.png` | стоит → у стены | шаг к стене, плечо разворачивается к ней | ступни, как `stand` |

**Обратные переходы не нужны:** программа играет те же кадры задом наперёд. Например, `stand → laydown` —
это `laydown_to_stand_2`, затем `_1`.

## 1. Как программа их использует (для понимания, что рисовать)
- Смена позы → если есть `<из>_to_<в>_1…N`, они проигрываются со скоростью 12 кадров/с, затем новая поза.
- Кадр рисуется с **точкой опоры новой позы**. Поэтому низ фигуры (ступни, сиденье) должен стоять на той
  же линии, что у конечной позы.
- Кадр — **поза ровно посередине** движения: ни начало, ни конец. Тогда при 12 кадрах/с глаз
  «досчитывает» движение.

## 2. Референсы — к первому сообщению чата
`character-reference.png` и **обе** позы перехода. Например, для №1–2 — `laydown.png` и `stand.png`; для №3 —
`stand.png` и `sit_corner.png`. Один переход (группа) — один новый чат.

## 3. Промпт — шаблон (GPT Image / ChatGPT)
После вступления из FRAMES.md §4.1:
```
The two attached poses are the START and the END of one smooth movement of this character:
START = {start} (first attachment), END = {end} (second attachment).
Draw ONE in-between frame of that movement: {middle}.
The character's scale, design, colors and line style are identical to the attachments; the {anchor}
is exactly where it is in the END pose. The pose is halfway between START and END, natural and
balanced, like a key in-between frame of hand-drawn animation. Canvas 1024x1536, vertical.
```
Затем «хвост» из FRAMES.md §4.2. Подстановки — из таблицы §0: `{start}`, `{end}` — названия поз
по-английски (*lying on the floor*, *standing*, *sitting hugging knees*, *walking*, *waving*, *held by the
hood*, *floating/landing*, *sitting on an edge*, *leaning on a wall*); `{middle}` — столбец «что на кадре»
по-английски; `{anchor}` — *feet* (большинство), *bottom* (№3), *tip of the hood* (№6).

Для №1–2 (два кадра одного перехода) после первого:
```
Using the previous in-between as a reference, draw the NEXT in-between (closer to END): {middle 2}.
Same scale, same feet line as the END pose.
```

## 4. Промпт — Gemini (Imagen / «Nano Banana»)
Gemini лучше держит персонажа, если явно перечислить, что **не меняется**:
```
Edit task. Keep EXACTLY: the character design (dark-blue hood and cloak, cream mask with two black oval
eyes, blue flame horns, blue flame tongues on the cloak hem, dark legs, small buckled boots), colors,
line style, proportions and size (cream mask ~184 px tall on 1024x1536). Transparent background, no
shadow, no glow halo, no text.
Change ONLY the pose: {middle}. This is the in-between frame between {start} and {end}; the {anchor}
stays where it is in the {end} image.
Output: PNG 1024x1536 with alpha.
```
Gemini иногда возвращает белый фон — тогда попросите `Return the same image with a fully transparent
background (alpha), nothing else changed`.

## 5. Проверки
- Наложите кадр на конечную позу с прозрачностью 50%: ступни (или сиденье, капюшон для №6) совпадают.
- Маска 175–200 px в высоту — масштаб тот же.
- Поза действительно «посередине»: на неё не похожа ни начальная, ни конечная.
- Фон прозрачный, без ореола и текста.

## 6. Ожидаемый результат
По оценке критика, переходы №1–9 закрывают все оставшиеся рывки. Ожидаемая оценка — **9,5–10/10**.
Остаток — вторичное движение огоньков (ANIMATION.md §4) — кадров не требует.

Готовые кадры — в папку с этими именами, пришлите путь: подгоню под пакет (как `frames-3`), добавлю в
`index.json` и прогоню критика.

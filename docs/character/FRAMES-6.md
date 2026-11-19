# Кадры для сцен настольного спутника (FRAMES-6) — задание на генерацию

_2026-11-18. Продолжение [FRAMES-5.md](FRAMES-5.md): сцены из раздела 13 `docs/HANDOVER_CHATGPT.md` уже
работают в коде, но почти все — на чужих позах и эмодзи. Здесь — свои кадры для каждой сцены._

Общие требования — **[FRAMES.md](FRAMES.md) §2–§4** (формат, масштаб, опора, брак, как генерировать). Ниже —
краткая выжимка и всё новое.

---

## 1. Что нужно — сводка

| № | Группа | Файлы | Кадров | Сцена (сейчас → станет) | Опора |
|---|---|---|---|---|---|
| 1 | Тянется к курсору (цикл) | `reach_1…3` | 3 | `reach` один кадр → «кошка за указкой» | ступни (0,5; 0,97) |
| 2 | Жмурится от поглаживания | `purr`, `purr_1…2` | 3 | `pet` → довольно жмурится, покачивается | ступни |
| 3 | Стучит по стеклу | `knock`, `knock_1…3` | 4 | `wave` + круги → стучит кулачком в экран | ступни |
| 4 | Тащит коробку | `carry_box_1…6` | 6 | ходьба + 📦 → коробка на спине, шатается | ступни |
| 5 | Ставит штамп | `stamp`, `stamp_1…3` | 4 | стоит + текст → замах и удар штампом | ступни |
| 6 | Ловит бумажку | `hug_paper`, `hug_paper_1…2` | 3 | `pet` + 📄 → ловит листок и прижимает к груди | ступни |
| 7 | Пугается вспышки | `flinch`, `flinch_1…2` | 3 | `pet` + ✧ → зажмурился, закрылся руками | ступни |
| 8 | Сдувает ветром | `blown_1…4` | 4 | `float` + ≋ → его уносит, плащ рвётся по ветру | середина (0,5; 0,6) |
| 9 | Читает книжку | `read_1…3` | 3 | стоит + прямоугольники → сидит и листает | низ (0,5; 0,95) |
| 10 | Рисует | `draw_1…3` | 3 | стоит + круг → рисует на листке | низ (0,5; 0,95) |
| 11 | Жонглирует | `juggle_1…4` | 4 | `dance` → подбрасывает (иконки рисует код) | ступни |
| 12 | Спотыкается и падает | `trip_1…4` | 4 | `dizzy` → `laydown` → споткнулся, упал, встал | ступни |
| 13 | Бежит за жуком | `chase_1…6` | 6 | ходьба → азартный бег с наклоном | ступни |
| 14 | Вертит находку | `inspect_1…4` | 4 | стоит → к глазам, трясёт, нюхает (значок рисует код) | ступни |
| 15 | Прячет в карман | `pocket_1…3` | 3 | → прячет в карман | ступни |
| 16 | Оттопыренный карман | `stand_pocket`, `stand_pocket_1…4`, `walk_pocket_1…8` | 13 | → карман заметно топорщится (после «спрятал») | ступни |
| 17 | Кладёт обратно | `put_back_1…3` | 3 | → наклоняется и кладёт | ступни |
| 18 | Выбрасывает и отряхивает руки | `throw_1…2`, `dust_hands_1…2` | 4 | → бросок вправо, хлопает ладонями | ступни |
| 19 | Строит | `build_1…4` | 4 | → кладёт блок, стучит молоточком | ступни |
| 20 | Записка | `note_put_1…3`, `note_take_1…3` | 6 | → прилепляет стикер / подбегает и забирает | ступни |

**Всего 87 кадров.** Порядок генерации — по пользе: 3, 4, 7, 8, 14, 15, 18, 2, 1, 12, 13, 5, 6, 19, 20, 9, 10,
11, 17, 16 (группа 16 самая дорогая — делать последней, можно ограничиться `stand_pocket` без цикла).

Предметы, которые **рисует код** поверх кадра (их на картинке быть не должно): значок файла, иконки для
жонглирования, жук, кольца от стука, вспышка, линии ветра, текст штампа, блоки постройки, текст стикера.
Предметы, которые **рисуются в кадре**: коробка (4), штамп (5), листок (6), книжка (9), карандаш и лист (10),
молоточек (19), стикер в руке (20), сам карман (15, 16).

---

## 2. Требования к каждому кадру (выжимка из FRAMES.md §2)

- PNG RGBA, холст **1024 × 1536**, вертикальный, фон **полностью прозрачный** (alpha 0).
- Масштаб: белая маска **175–200 px** в высоту (эталон в `stand.png` — 184 × 160). Стоя — рост ~95 % холста,
  подошвы ~45 px от низа.
- Персонаж смотрит **вправо** (3/4 вправо). Влево программа отражает сама.
- Опора — в точке из таблицы раздела 1 (доли холста от левого верхнего угла). Сидя (9, 10) — как
  `sit_corner`: низ на 0,95.
- Кадры одной группы — **в одной рамке**: голова и ступни на месте, двигается только то, что указано.
- Брак: ореол или дым вокруг, тень или пятно под телом, непрозрачный фон, буквы и «z», обводка, свечение по
  краю, смена масштаба внутри группы.

## 3. Референсы

Из папки `C:\Users\Alast\Documents\Codex\2026-11-16\x20-6\outputs\character-poses\` (PNG 1024×1536) или,
если её нет, из пакета `ui/public/characters/default/` (WebP — для референса годится):

| Группы | Приложить к первому сообщению чата |
|---|---|
| 1, 2, 3, 5, 6, 7, 11, 14, 15, 17, 18, 19, 20 | `character-reference.png`, `stand.png`, `pet.png` (для 2, 6, 7), `reach.webp` (для 1) |
| 4, 13, 16 (`walk_pocket`) | `character-reference.png`, `walk.png`, `walk_1.png`, `walk_5.png` |
| 8 | `character-reference.png`, `float.png` |
| 9, 10 | `character-reference.png`, `sit_corner.png` |
| 12 | `character-reference.png`, `stand.png`, `laydown.png`, `dizzy.webp` |

**Одна группа — один новый чат.**

## 4. Вступление и хвост (как в FRAMES.md §4)

Вступление — первым сообщением, с референсами:
```
The attached images are the exact reference for one character: a small hooded figure with a dark-blue
hood and cloak, a cream mask with two black oval eyes, blue flame horns, blue flame tongues along the
cloak hem, dark legs and small boots with buckles. Keep the design, colors, line style, shading and
proportions identical in every image I ask for next. Every image is a clean cut-out on a fully
transparent background. Do not reply with text, only with images.
```

Хвост — в конце **каждого** промпта кадра:
```
Output a clean cut-out: a fully transparent background (alpha 0) everywhere outside the character —
no glow halo, no smoke, no shadow, no dark aura, no vignette, no outline, no background color. The blue
flames keep their own light but do not spill onto the background. No letters, no "z", no text, no
symbols. Same character scale as the attached reference: the cream mask is about 184 px tall on a
1024x1536 canvas. Full body, 3/4 view facing RIGHT. PNG, 1024x1536, vertical.
```

Кадры цикла после базового:
```
Using the previous image as the reference — same framing, scale, and feet position — draw frame {N} of {M}
of a looping animation: {что меняется в кадре N}. Everything else stays in place.
```

---

## 5. Промпты по группам

Ниже — только описание позы; к каждому добавить хвост.

### 1. `reach_1…3` — тянется к курсору
Цикл к готовому `reach.webp` (приложить его):
1. `Standing, leaning forward toward something just above and to the right, one hand reaching out with open fingers, eyes fixed on it.`
2. `Same, on tiptoes, the hand stretched further and higher, body leaning more, cloak swinging back.`
3. `Same, a quick little paw-swipe: the hand flicked sideways as if trying to catch a moving dot, playful.`

### 2. `purr`, `purr_1…2` — жмурится от поглаживания
`purr`: `Standing like stand.png, being petted: eyes closed as two happy upward curves, head tilted, shoulders raised, small pink blush on the mask, flame horns slightly brighter.`
`purr_1`: `head tilted the other way, swaying.` `purr_2`: `head back in the middle, shoulders relaxed, blissful.`

### 3. `knock`, `knock_1…3` — стучит изнутри по стеклу экрана
`knock`: `Standing facing the viewer more than usual (front 3/4), one fist raised at head height close to the viewer as if knocking on glass between us, curious face.`
Цикл: `1 — fist pulled back; 2 — fist touching the "glass" (fingers slightly squashed flat); 3 — the other palm pressed flat against the glass, peeking.`
Опора — ступни; кулак в точке ≈ (0,7; 0,38) — там код рисует кольца.

### 4. `carry_box_1…6` — тащит коробку на спине
Цикл ходьбы, 6 кадров: `Walking to the right, bent forward under the weight of a big cardboard box carried on the back with both hands holding straps; knees bent, wobbly steps. Frame {N}: {left foot forward / passing / right foot forward / passing / staggering slightly back / recovering}.`
Коробка — простая, светло-коричневая, **без надписей**. Высота коробки ~35 % роста. Код качает кадр по размеру файла, поэтому коробка жёстко «приклеена» к спине.

### 5. `stamp`, `stamp_1…3` — ставит штамп «Сохранено!»
`stamp`: `Standing, holding a big round rubber stamp with a wooden handle in both hands, raised above the head, determined face.`
Цикл: `1 — stamp raised high; 2 — stamp slammed down in front at waist height, little jump; 3 — stamp lifted, proud pose, one hand on hip.`
Оттиск и текст рисует код (точка оттиска ≈ (0,72; 0,7)). На штампе — **ни одной буквы**.

### 6. `hug_paper`, `hug_paper_1…2` — ловит бумажку
`hug_paper_1`: `Arms stretched up catching a small white sheet of paper fluttering down.`
`hug_paper_2`: `Bringing the sheet down to the chest.` `hug_paper`: `Hugging the sheet to the chest with both arms, eyes closed happily.`
На листке — серые полоски вместо текста.

### 7. `flinch`, `flinch_1…2` — пугается вспышки скриншота
`flinch`: `Startled by a bright flash: eyes squeezed shut (two short lines), both hands up covering the mask, shoulders hunched, slight jump.`
`flinch_1`: `peeking through the fingers.` `flinch_2`: `hands down, blinking, dizzy little wobble.`
Вспышку рисует код — в кадре света нет.

### 8. `blown_1…4` — сдувает ветром (Win+D)
`Floating, blown away by a strong wind from the left: body tilted, cloak and flame horns streaming to the right, holding the hood with one hand. Frame {N}: {lifted / spinning a quarter turn / tumbling / hanging on, cloak flapping}.`
Опора — середина тела (0,5; 0,6). Линии ветра рисует код.

### 9. `read_1…3` — читает крошечную книжку
`Sitting on the floor like sit_corner.png, holding a tiny open book with both hands, reading. Frame {N}: {reading / turning a page / small laugh, book tilted}.`
Книжка — тёмно-синяя обложка, страницы без текста (серые полоски).

### 10. `draw_1…3` — рисует
`Sitting like sit_corner.png, a small sheet of paper on the knees, drawing with a yellow pencil, tongue-out concentration. Frame {N}: {pencil on paper / pencil moved / holding the drawing up proudly — the drawing is a simple blue scribble}.`

### 11. `juggle_1…4` — жонглирует
`Standing, juggling with both hands, looking up; hands empty — the juggled objects are added later. Frame {N}: {left hand up / both hands at chest / right hand up / both hands catching}.`
Ладони в верхней точке ≈ y 0,45 — там код рисует иконки.

### 12. `trip_1…4` — спотыкается
`1 — mid-step, toe catching on nothing, arms flailing; 2 — falling forward; 3 — lying face down, legs up (on the floor line, bottom 0,92); 4 — sitting up, rubbing the hood, embarrassed.`
Кадр 3 — опора как у `laydown` (низ 0,92); остальные — ступни. Подогнать как одну группу по масштабу.

### 13. `chase_1…6` — бежит за жуком
`Running to the right, leaning forward, excited face, one hand reaching forward to catch something small near the ground. Frame {N}: run cycle 1–6, with frame 6 a little pounce.`

### 14. `inspect_1…4` — вертит находку
Руки держат **пустое место** — значок файла рисует код в точке ≈ (0,68; 0,42).
`1 — holding something small up close to the eyes, squinting; 2 — shaking it next to the ear; 3 — sniffing it, mask tilted; 4 — holding it at arm's length, thinking.`

### 15. `pocket_1…3` — прячет в карман
`1 — opening a small pocket on the front of the cloak with one hand; 2 — tucking something small into it; 3 — patting the pocket, satisfied.`
Карман — у правого бедра, тёмно-синий с голубым кантом.

### 16. `stand_pocket`, `stand_pocket_1…4`, `walk_pocket_1…8` — оттопыренный карман
`Exactly the same image as the attached {stand|walk_N}.png — identical pose, framing, scale — but the pocket on the cloak at the right hip is visibly bulging, stuffed with something.`
Генерировать по каждому кадру `stand`/`walk` отдельно (приложить исходный кадр). Минимум — только `stand_pocket`.

### 17. `put_back_1…3` — кладёт обратно
`1 — bending down, hand holding something small low to the right; 2 — placing it on the ground carefully; 3 — standing up, small wave goodbye to it.`

### 18. `throw_1…2`, `dust_hands_1…2` — выбрасывает
`throw_1 — wind-up, arm back; throw_2 — throwing forward to the right, arm extended, empty hand open.`
`dust_hands_1 — clapping hands together in front of the chest, satisfied; dust_hands_2 — hands apart, little dust puff is NOT drawn.`
Корзину рисует код справа на уровне пола.

### 19. `build_1…4` — строит
`1 — carrying a small paper block in both hands; 2 — placing it down to the right; 3 — tapping it with a tiny wooden mallet; 4 — stepping back, admiring, hands on hips.`
Блоки рисует код; в кадре — только блок в руках (1) и молоточек (3).

### 20. `note_put_1…3`, `note_take_1…3` — записка
`note_put: 1 — holding a small yellow sticky note above the head; 2 — sticking it onto an invisible wall to the right at head height; 3 — pointing at it, cheerful.`
`note_take: 1 — running to the right; 2 — peeling the note off; 3 — holding it to the chest, waving.`
На стикере — **без текста** (текст рисует код). Стикер в точке ≈ (0,78; 0,3).

---

## 6. Подгонка и подключение (делает Codex)

1. Группа подгоняется **одним преобразованием**: масштаб — по высоте белой маски к `stand`, опора — в точку из
   раздела 1. Экспорт: WebP, качество 90, высота 768 → `ui/public/characters/default/`, имена — в `index.json`.
2. Новые позы — в тип `Pose`, `ANCHORS`, `FALLBACK` (на нынешнюю позу сцены, чтобы без кадров ничего не
   сломалось), `LOOP_FPS` (`ui/src/features/companion/look/pack.ts`).
3. Сцены переключить с временных поз на новые: `look/diversions.ts` (`knock`, `read`, `draw`, `juggle`,
   `trip`, `bug` → `chase`), `behavior/desktopEvents.ts` (`POSES`: download → `carry_box`, save → `stamp`,
   copy → `hug_paper`, screenshot → `flinch`, desktop → `blown`), сцены находки/кармана/постройки/записок.
   Эмодзи `📦 📄 ✧ ≋` убрать — их заменяют кадры.
4. Записать в этот файл (раздел «Принято»): какие кадры приняты, масштабы и исключения.

## Принято (2026-11-18)

Все 87 кадров приняты и подключены. Замечания к генерации и что стоит перегенерировать —
[FRAMES-6-REVIEW.md](FRAMES-6-REVIEW.md).

**Подгонка** (одноразовый скрипт на Pillow вне репозитория, Pillow — не зависимость):
- масштаб — по высоте белой маски к `stand.png` (маска ищется в верхней части фигуры, чтобы не ловить
  листки и книжку); у стоящих на месте групп (`juggle`, `purr`, `dust_hands`, `knock`, `hug_paper`,
  `inspect`, `pocket`, `stand_pocket`, `flinch`) — по росту фигуры; руки на маске (`flinch`,
  `flinch_1`) — по ширине маски;
- группа с разбросом масштаба меньше 8 % — один масштаб на группу (цикл не «дышит»), больше — каждый
  кадр по себе; бег `chase` — общий масштаб, кроме `chase_4` (нарисован мельче);
- опора по x — середина ступней (у `blown` — центр тела), по y — 0,97 (стоя), 0,95 (`read`, `draw`),
  0,45 (`blown`);
- холст 800 × 768, WebP q90. Не влезло сверху (поднятый штамп, рожки) — холст выше, лишнее **только
  сверху**: 776–912 px у `build_1…3`, `dust_hands`, `flinch`, `hug_paper`, `inspect`, `juggle`, `knock`,
  `pocket`, `purr`, `purr_2`, `stamp*`, `stand_pocket*`. Программа рисует их в том же масштабе
  (`look/placement.ts`, высота кадра `stand` — обычная).

**Подключение** (`look/scenePoses.ts`): позы в `Pose`, замены на прежние позы (пакет пользователя без
этих кадров ведёт себя как раньше), опоры, частота. Сцены: поглаживание → `purr`; стук, чтение, рисунок,
жонглирование, падение, жук → `knock`, `read`, `draw`, `juggle`, `trip` (1,6 с), `chase`; загрузка,
сохранение, копирование, скриншот, Win+D → `carry_box`, `stamp`, `hug_paper`, `flinch`, `blown`
(эмодзи убраны; кодом — оттиск штампа, вспышка, линии ветра); находка → `inspect`, финал `pocket` /
`put_back` / `throw` + `dust_hands`; полный карман → `stand_pocket`, `walk_pocket`; новый блок
постройки → `build`; записка → `note_put`, забрал → `note_take`.

## Исправленная генерация (`frames-6-revised`, 2026-11-18)

Все 87 кадров заменены исправленными (`…\outputs\frames-6-revised\`), имена прежние — код и `index.json` не менялись.
Проверка: PNG 1024×1536, прозрачный фон, ореола нет у всех 87.

- **Что исправлено в рисунке:** `knock` — вид спереди, кулак у «стекла»; `inspect_1`, `inspect_3` — любопытное лицо
  вместо прищура; `stand_pocket*`, `walk_pocket*` — карман заметно оттопырен.
- **Подгонка** — тем же способом, что выше. Ручные масштабы (детектор маски ошибается): `chase_6` 0,99 (прыжок с
  наклоном), `read_2` 0,95 (маску сбивает раскрытая книга; по росту фигуры относительно `read_1`).
- Масштаб внутри групп у генератора снова скачет (`knock_2/3`, `inspect_1`, `chase_2`, `stamp_1/3` мельче) —
  выровнено подгонкой. `stamp_1` и `stamp_3` по маске верны, просто поза компактнее.
- Высокие кадры (место сверху): 776–824 px — `build`, `chase_6`, `dust_hands`, `flinch`, `hug_paper`, `inspect`,
  `juggle`, `knock`, `pocket`, `purr`, `stamp`, `stand_pocket*`.


## Без кадров с сумкой (2026-11-18)

По просьбе пользователя убраны `stand_pocket*` и `walk_pocket*`: оттопыренный карман дёргался и бросался в глаза.
С вещами в кармане персонаж стоит и ходит обычными `stand` / `walk`; механизм варианта позы удалён. Сцена «прячет
в карман» (`pocket_1…3`) осталась.

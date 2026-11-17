# Кадры персонажа для генерации в ChatGPT — полное задание

Единый документ для всех кадров персонажа: что уже есть, что сгенерировать, в каком формате и масштабе, какие
референсы приложить и как проверить результат. Он заменяет разрозненные `prompts.md` (шаги 1–4),
`regenerate.md` и `new-frames.md`: те остаются как история.

Персонаж — капюшон тёмно-синего цвета, кремовая маска с двумя чёрными овальными глазами, голубые
огненные рожки, плащ с бантом и голубыми языками пламени по краю, тёмные ноги, сапожки с пряжками.

---

## 1. Что уже есть, а что нужно

**Уже в программе** (`ui/public/characters/default/`, 51 файл):

| Группа | Кадры |
|---|---|
| Позы | `stand`, `walk`, `sit_edge`, `perch_corner`, `lean_side`, `hang_side`, `sit_corner`, `laydown`, `sleep`, `held`, `float` |
| Циклы | `walk_1…8`, `stand_1…4`, `sit_edge_1…4`, `held_1…4`, `hang_side_1…4`, `float_1…3`, `sleep_1…3` |
| Лицо | `stand_talk`, `stand_blink`, `sit_edge_talk`, `sit_edge_blink`, `sit_edge_blink_1`, `laydown_talk`, `laydown_blink` |
| Мордашка в углу окна | `head`, `head_talk`, `head_blink` — вырезаны из `stand`, низкого качества |

**Нужно сгенерировать** — по убыванию пользы:

| № | Группа | Файлы | Сколько | Зачем |
|---|---|---|---|---|
| A | Рот при речи (перегенерация) | `stand_talk_1…3`, `sit_edge_talk_1…3`, `laydown_talk_1…3` | 9 | липсинк по громкости; прошлые — с ореолом |
| B | Полуприкрытые глаза (перегенерация) | `stand_blink_1`, `laydown_blink_1` | 2 | мягкое моргание; прошлые — с ореолом |
| C | Тычет пальцем | `poke`, `poke_1…3` | 4 | «тыканье» в кнопки и значки; сейчас вместо него «облокотился» |
| D | Гладят | `pet`, `pet_1…2` | 3 | реакция на клик; сейчас — `stand` с закрытыми глазами |
| E | Мордашка для угла окна | `head`, `head_talk_1…3`, `head_blink_1`, `head_blink` | 6 | крупный план вместо вырезки из `stand` |
| F | Циклы оставшихся поз | `perch_corner_1…4`, `lean_side_1…4`, `sit_corner_1…4`, `laydown_1…4` | 16 | чтобы и эти позы «дышали» |
| G | Эмоции мордашки (по желанию) | `head_happy`, `head_sad`, `head_surprised`, `head_angry`, `head_thinking` | 5 | окно программы меняет лицо по эмоции ответа; подключу, когда придут |

Всего 45 кадров; без группы G — 40.

---

## 2. Общие требования — для КАЖДОГО кадра

### 2.1. Формат
| Что | Позы (группы A–D, F) | Мордашка (E, G) |
|---|---|---|
| Файл | PNG, RGBA | PNG, RGBA |
| Холст | **1024 × 1536**, вертикальный | **1024 × 1024**, квадрат |
| Фон | **полностью прозрачный** (alpha 0) | **полностью прозрачный** |
| Имя | ровно как в таблицах ниже, латиницей, нижний регистр | то же |

### 2.2. Масштаб — один на всех
Мерило — **белая маска**, она есть во всех позах и не меняет форму. В эталонном `stand.png` маска
**184 px в высоту и 160 px в ширину**, персонаж от кончиков рожек до подошв — **1465 px, 95% холста**.
- **В каждом кадре поз** маска — **175–200 px в высоту**. Сильнее — кадр будет крупнее или мельче остальных,
  и персонаж будет «прыгать» в размере.
- **Стоячие позы** (`stand`, `pet`, `lean_side`, кадры цикла) — рост ~95% холста, подошвы на нижней линии
  с отступом ~3% (около 45 px).
- **Мордашка** (группы E, G) — свой масштаб: маска ~**300 px** в высоту на квадрате 1024. Кончики рожек у
  верхнего края, бант у нижнего, маска чуть выше центра.

### 2.3. Точка опоры
Программа ставит в точку опоры место, за которое персонаж держится или на котором стоит. Если оно на картинке
не там, где ждёт программа, я подвину кадр. Но всё, что генератор нарисует **за краем холста** после
сдвига, обрежется. Поэтому держите опору примерно здесь (доли холста от левого верхнего угла):

| Поза | Опора | Где на холсте |
|---|---|---|
| `stand`, `walk`, `lean_side`, `pet` | середина ступней | x ≈ 0,5; низ ≈ 0,97 |
| `sit_edge`, `perch_corner` | сиденье (линия края, на который сел) | x ≈ 0,5; y ≈ 0,62–0,67 |
| `sit_corner` | ягодицы и подошвы на полу | x ≈ 0,5; низ ≈ 0,95 |
| `laydown`, `sleep` | тело на линии пола | x ≈ 0,5; низ ≈ 0,92 |
| `held` | кончик капюшона, за который держат | x ≈ 0,5; верх ≈ 0,06 |
| `hang_side` | кулаки, которыми держится | x ≈ 0,5; верх ≈ 0,04 |
| `float` | середина тела | x ≈ 0,5; y ≈ 0,6 |
| `poke` | **кончик вытянутого пальца** | x ≈ 0,88; y ≈ 0,42 |

### 2.4. Направление
**Персонаж смотрит вправо** или вправо в три четверти. Влево программа отражает сама. Исключения —
`laydown` и `sleep` (голова слева, как в имеющихся).

### 2.5. Беды прошлых генераций — их быть не должно
1. **Дымный ореол вокруг персонажа.** Полупрозрачное тёмное облако, «аура», пятно под телом. Это главная
   беда: 13 кадров прошлого раза ушли в брак.
2. **Буквы.** «z» из промпта сна в кадрах ходьбы и стояния, любые надписи.
3. **Непрозрачный фон** (был у одного кадра).
4. **Сдвиг и смена масштаба** в вариантах, которые должны совпадать до пикселя.
5. **Обводка, тень на полу, свечение по краю холста.**

---

## 3. Референсы — что прикладывать

Все из папки `C:\Users\Alast\Documents\Codex\2026-11-16\x20-6\outputs\character-poses\`.

| Группа | Приложить к первому сообщению чата |
|---|---|
| A, B — `stand_*` | `character-reference.png`, `stand.png`, `stand_talk.png`, `stand_blink.png` |
| A, B — `sit_edge_*` | `character-reference.png`, `sit_edge.png`, `sit_edge_talk.png`, `sit_edge_blink.png` |
| A, B — `laydown_*` | `character-reference.png`, `laydown.png`, `laydown_talk.png`, `laydown_blink.png` |
| C — `poke` | `character-reference.png`, `stand.png` |
| D — `pet` | `character-reference.png`, `stand.png`, `stand_blink.png` |
| E, G — `head*` | `character-reference.png`, `stand.png`, `stand_talk.png`, `stand_blink.png` |
| F | `character-reference.png` + базовая поза группы (`perch_corner.png`, `lean_side.png`, `sit_corner.png` или `laydown.png`) |

**Одна группа — один новый чат.** В длинном чате генератор «плывёт»: меняет лицо, масштаб, добавляет ореол.

---

## 4. Как генерировать

1. Новый чат, приложить референсы группы (раздел 3) и отправить **вступление**:
   ```
   The attached images are the exact reference for one character: a small hooded figure with a dark-blue
   hood and cloak, a cream mask with two black oval eyes, blue flame horns, blue flame tongues along the
   cloak hem, dark legs and small boots with buckles. Keep the design, colors, line style, shading and
   proportions identical in every image I ask for next. Every image is a clean cut-out on a fully
   transparent background. Do not reply with text, only with images.
   ```
2. **Один кадр — одно сообщение.** Промпт кадра (раздел 5), затем **хвост**:
   ```
   Output a clean cut-out: a fully transparent background (alpha 0) everywhere outside the character —
   no glow halo, no smoke, no shadow, no dark aura, no vignette, no outline, no background color. The blue
   flames keep their own light but do not spill onto the background. No letters, no "z", no text, no
   symbols. Same character scale as the attached reference: the cream mask is about 184 px tall on a
   1024x1536 canvas. PNG.
   ```
   Для мордашки (группы E, G) последнее предложение хвоста другое:
   `Square 1024x1024 canvas; the cream mask is about 300 px tall. PNG.`
3. Если кадр вышел с ореолом или «поплыл» — не исправляйте его в том же чате. Попросите заново:
   ```
   That one has a halo and the scale changed. Generate it again from the attached reference, strictly
   following the requirements.
   ```
4. Сохраните кадр под именем из таблицы.

---

## 5. Промпты по группам

### A. Рот при речи — `{pose}_talk_1`, `_2`, `_3`
Для `{pose}` = `stand`, `sit_edge`, `laydown` — по три кадра, **в чате своей позы**, сразу после
вступления:
```
Exactly the same image as the attached {pose}.png — identical pose, framing, scale and position of every
pixel — but the mouth on the mask is {mouth}. Nothing else changes.
```
| Кадр | `{mouth}` |
|---|---|
| `_talk_1` | `slightly open (a small dark oval)` |
| `_talk_2` | `open as if saying "ah"` |
| `_talk_3` | `wide open, excited` |

### B. Полуприкрытые глаза — `stand_blink_1`, `laydown_blink_1`
В чате своей позы:
```
Exactly the same image as the attached {pose}.png — identical pose, framing, scale and position of every
pixel — but both eyes on the mask are half closed (halfway through a blink). Nothing else changes.
```

### C. Тычет пальцем — `poke`, `poke_1…3`
`poke.png`:
```
Full body, 3/4 view facing RIGHT, floating slightly (feet off the ground). Leaning forward and poking
something in front of him with the index finger of the right arm stretched straight to the RIGHT, curious
playful expression. The fingertip is at the right side of the canvas at chest height — about 88% of the
width and 42% of the height. Canvas 1024x1536, vertical.
```
`poke_1…3`, сразу после `poke.png`:
```
Using the previous poke image as the reference, draw frame {N} of 3 of a looping poke: frame 1 — the arm
pulled back slightly, the fingertip about 40 px left of where it was; frame 2 — the fingertip exactly where
it was in poke.png; frame 3 — the finger pressing in, the cloak and flames jolting slightly. The head and
the body stay in place, only the arm and the cloak move. Canvas 1024x1536, vertical.
```

### D. Гладят — `pet`, `pet_1…2`
`pet.png`:
```
Full body, standing exactly like the attached stand.png — same scale, same feet position on the bottom
line. Being petted on the head: eyes closed in two happy upward curves, head tilted slightly toward the
hand, shoulders raised in delight, a small pink blush on the mask, the blue flame horns glow a little
brighter and curl happily. No hand drawn. Canvas 1024x1536, vertical.
```
`pet_1`, `pet_2`:
```
Using the previous pet image as the reference, draw frame {N} of 2 of a tiny happy wiggle: frame 1 — the
body sways slightly to the left, frame 2 — slightly to the right. The feet stay exactly in place.
Canvas 1024x1536, vertical.
```

### E. Мордашка — `head`, `head_talk_1…3`, `head_blink_1`, `head_blink`
`head.png`:
```
Close-up portrait of the same character: the blue flame horns, the hood, the cream mask and the bow of the
cloak, 3/4 view facing slightly to the RIGHT, calm friendly expression, mouth closed. The horns' tips near
the top edge, the bow near the bottom edge, the mask a little above the center, centered horizontally.
Square canvas 1024x1024.
```
Остальные — сразу после `head.png`:
```
Exactly the same image as the previous head.png — identical framing, scale and position of every
pixel — but {change}. Nothing else changes. Square canvas 1024x1024.
```
| Файл | `{change}` |
|---|---|
| `head_talk_1` | `the mouth on the mask is slightly open (a small dark oval)` |
| `head_talk_2` | `the mouth is open as if saying "ah"` |
| `head_talk_3` | `the mouth is wide open, excited` |
| `head_blink_1` | `both eyes are half closed (halfway through a blink)` |
| `head_blink` | `both eyes are closed (a soft curved line each)` |

### F. Циклы оставшихся поз — `{pose}_1…4`
Для `{pose}` = `perch_corner`, `lean_side`, `sit_corner`, `laydown`. **Свой чат на каждую позу**, по четыре
кадра:
```
Using the attached {pose}.png as the reference, draw frame {N} of 4 of a subtle seamless idle loop:
a slow breath (frame 1 neutral, 2 chest and hood slightly up, 3 neutral, 4 slightly down), the cloak hem
sways a little, the blue flame horns flicker with a different flame shape in each frame{extra}.
{anchor} stays exactly in place; the scale and the position do not change. Canvas 1024x1536, vertical.
```
| Поза | `{extra}` | `{anchor}` |
|---|---|---|
| `perch_corner` | `, the hanging leg swings slowly` | `The seat on the corner` |
| `lean_side` | `` (пусто) | `The feet and the shoulder against the wall` |
| `sit_corner` | `, the head nods a little` | `The body on the floor` |
| `laydown` | `, the raised foot taps lazily` | `The body on the floor line` |

### G. Эмоции мордашки (по желанию) — `head_{emotion}`
После `head.png` в чате группы E:
```
Exactly the same framing, scale and position as the previous head.png, but the expression is {emotion}:
{look}. The horns and the hood stay in place. Square canvas 1024x1024.
```
| Файл | `{emotion}` | `{look}` |
|---|---|---|
| `head_happy` | `happy` | `eyes curved in a smile, small open smiling mouth, flames brighter` |
| `head_sad` | `sad` | `eyes drooping, small frown, flames dimmer and lower` |
| `head_surprised` | `surprised` | `eyes wide and round, small "o" mouth, flames flaring up` |
| `head_angry` | `angry` | `eyes narrowed and slanted, flames sharp and tall` |
| `head_thinking` | `thinking` | `eyes looking up and to the side, mouth a small line, a hand near the mask` |

---

## 6. Проверки

### 6.1. Сами — до отправки (минута на кадр)
1. **Прозрачность.** Откройте PNG в просмотрщике с «шахматкой» (Paint 3D, Photoshop, онлайн-просмотрщик PNG).
   Вокруг персонажа должна быть чистая шахматка — без серого облака, тени и рамки.
2. **Ничего лишнего.** Нет букв, «z», подписей, водяных знаков.
3. **Варианты** (`_talk_*`, `_blink*`, `head_*` кроме `head`). Быстро переключайтесь между кадром и его основой:
   меняются только рот или глаза, всё остальное стоит на месте.
4. **Циклы** (`_1…N`). Переключайтесь по порядку: голова и опора не прыгают, двигаются только описанные части.
5. **Размер.** Маска примерно того же размера, что в эталоне; на глаз — не больше и не меньше.

### 6.2. Я — при приёме (автоматически)
| Проверка | Порог | Что делаю, если не прошло |
|---|---|---|
| Холст | 1024×1536 (позы), 1024×1024 (мордашка) | приму, но предупрежу: масштаб подгоню по маске |
| Фон прозрачный | углы холста — alpha 0; доля полупрозрачных пикселей вне тела < 1% | убираю мелкие пятна; ореол вокруг тела → в перегенерацию |
| Лишние пятна и буквы | связные области < 1,5% площади персонажа | вырезаю сам |
| Масштаб | высота маски в пределах ±10% от основы | подгоняю; если дальше ±20% — в перегенерацию |
| Совпадение варианта | вне лица пиксели отличаются от основы < 2% | в перегенерацию |
| Опора у циклов | смещение опоры между кадрами ≤ 12 px (на холсте 768) | подгоняю; больше — выбрасываю кадр |
| Повторы | соседние кадры цикла различаются хотя бы на 2% | одинаковые выбрасываю |

Потом совмещаю кадры с основой по маске, перевожу в WebP высотой 768 (мордашку — 512 × 512), кладу во
встроенный пакет и проверяю в окне: персонаж стоит, ходит, говорит и моргает без рывков. Брак описываю
списком — что, почему, промпт для перегенерации.

---

## 7. Куда положить и как сдать
1. Все готовые PNG — в одну папку, например
   `C:\Users\Alast\Documents\Codex\2026-11-16\x20-6\outputs\frames-2\`. Имена — строго из таблиц, без
   префиксов вроде `exec-…`.
2. Можно сдавать по группам, не дожидаясь всех.
3. Пришлите путь к папке. Что пришло без имён — разберу по картинкам, но с именами быстрее и без ошибок.

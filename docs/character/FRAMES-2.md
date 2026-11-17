# Кадры персонажа, часть 2 — радио, лазанье, эмоции тела (задание для ChatGPT)

> Продолжение [FRAMES.md](FRAMES.md) (2026-11-17). Зачем эти кадры — [BEHAVIOR.md](BEHAVIOR.md) §8–§10.
> **Формат, масштаб, вступление, хвост, проверки и куда класть — те же, что в FRAMES.md, разделы 2, 4, 6, 7.**
> Здесь только новое: группы, референсы, точки опоры и промпты.

Пока кадров нет, программа рисует замену (`stand`, `hang_side` …), так что генерировать можно в любом
порядке и частями. Присылайте папку — подгоню так же, как `frames-2` (одно преобразование на группу).

---

## 0. Что нужно — сводка

| § | Группа | Файлы | Сколько | Зачем | Замена, пока нет |
|---|---|---|---|---|---|
| 1 | Поёт (радио) | `sing`, `sing_1…4`, `sing_talk_1…3` | 8 | режим радио: поёт стоя | `stand` + подскок |
| 2 | Радио на паузе | `radio_idle`, `radio_idle_blink` | 2 | пауза: наушники на шее, слушает | `stand` |
| 3 | Лезет по стене | `climb`, `climb_1…4` | 5 | карабкается по боку окна | `hang_side` |
| 4 | Кружится голова | `dizzy`, `dizzy_1…2` | 3 | после тряски мышью | `float` |
| 5 | Машет рукой | `wave`, `wave_1…2` | 3 | приветствие, «что смотришь?» | `stand` |
| 6 | Выглядывает | `peek`, `peek_blink` | 2 | из-за края окна | — (не выглядывает) |
| 7 | Зевает | `yawn`, `yawn_1` | 2 | ночь, перед сном | `stand` |
| 8 | Танцует | `dance_1…4` | 4 | музыка в плеере | `stand` |

Всего 29 кадров. Самое важное — §1 и §3 (радио и лазанье).

---

## Общая деталь для §1–2: наушники и микрофон

Добавьте **в вступление** чатов §1 и §2 (после основного вступления FRAMES.md §4.1) одно предложение:
```
In this chat the character also wears accessories: big over-ear headphones resting AROUND THE NECK
(dark-blue band, round ear cups with glowing cyan rims, the same cyan as the horn flames), and holds a
small black handheld microphone with a silver mesh head. Keep these accessories identical in every image.
```

---

## 1. Поёт — `sing`, `sing_1…4`, `sing_talk_1…3`

**Референсы:** `character-reference.png`, `stand.png`, `stand_talk.png`.
**Опора:** середина ступней, x ≈ 0,5, низ ≈ 0,97 (как `stand`). Смотрит вправо в три четверти.

`sing.png`:
```
Full body, standing exactly like the attached stand.png (same scale, same feet position on the bottom
line). Headphones around the neck. The right hand holds the microphone close to the mask's mouth, the
left arm slightly raised in the rhythm, head tilted a little, eyes softly closed in two calm curves —
singing with feeling. Small mouth open on the mask. Canvas 1024x1536, vertical.
```
`sing_1.png … sing_4.png` — цикл покачивания в ритм, по одному после `sing.png`:
```
Using the previous sing image as the reference, draw frame {N} of 4 of a looping groove while singing:
frame 1 — body leans slightly left, frame 2 — upright, knees slightly bent, frame 3 — leans slightly
right, frame 4 — upright, heels slightly raised. The feet stay on the same bottom line, the microphone
stays at the mouth, the scale does not change. Canvas 1024x1536, vertical.
```
`sing_talk_1…3` — рот при пении поверх `sing.png`:
```
Exactly the same image as the previous sing.png — identical pose, framing, scale and position of every
pixel — but the mouth on the mask is {mouth}. Nothing else changes.
```
`{mouth}`: 1 — `slightly open`, 2 — `open as if singing "ah"`, 3 — `wide open, belting a high note`.

## 2. Радио на паузе — `radio_idle`, `radio_idle_blink`

**Референсы:** `character-reference.png`, `stand.png`. **Опора:** ступни, как `stand`.

`radio_idle.png`:
```
Full body, standing exactly like the attached stand.png (same scale and feet line). Headphones around
the neck, the microphone held loosely down by the hip in the right hand, the left hand touching one ear
cup as if listening for the next song, relaxed curious look. Canvas 1024x1536, vertical.
```
`radio_idle_blink.png` — тот же кадр, глаза закрыты:
```
Exactly the same image as the previous radio_idle.png — identical framing, scale and position of every
pixel — but both eyes are closed (a soft curved line each). Nothing else changes.
```

## 3. Лезет по стене — `climb`, `climb_1…4`

**Референсы:** `character-reference.png`, `hang_side.png`, `stand.png`.
**Стена — справа от персонажа**, вертикальная линия на **x ≈ 0,85** холста (сама стена НЕ рисуется,
только руки и ноги, упёртые в неё). **Опора программы — середина тела**, x ≈ 0,5, y ≈ 0,5.
Вид сбоку-сзади в три четверти: спина к нам, лицо (маска) чуть видно в профиль справа.

`climb.png`:
```
Full body, the same scale as the attached stand.png. The character climbs UP an invisible vertical wall
that is on the RIGHT side of the image at about 85% of the width: three-quarter back view, both hands
grip the wall at the right, one boot pressed against it, the other leg hanging, the cloak hanging down,
the mask seen in profile looking up. The center of the body is at the center of the canvas. Do not draw
the wall. Canvas 1024x1536, vertical.
```
`climb_1.png … climb_4.png` — цикл лазанья, по одному:
```
Using the previous climb image as the reference, draw frame {N} of 4 of a looping climb up the same
invisible wall on the right: frame 1 — right hand reaches up, left foot pushes; frame 2 — body pulled up,
both hands on the wall; frame 3 — left hand reaches up, right foot pushes; frame 4 — body pulled up again.
The body center stays at the canvas center, the hands and boots touch the line at about 85% of the width,
the scale does not change. Canvas 1024x1536, vertical.
```

## 4. Кружится голова — `dizzy`, `dizzy_1…2`

**Референсы:** `character-reference.png`, `stand.png`. **Опора:** ступни, как `stand`.
```
Full body, standing like the attached stand.png (same scale and feet line) but wobbly: knees bent
inward, body tilted, arms loose, eyes drawn as two small spirals, horn flames drooping and twisted —
dizzy after being shaken. Canvas 1024x1536, vertical.
```
`dizzy_1`, `dizzy_2` — покачивание: `frame {N} of 2: the body sways to the {left|right}, the feet stay in
place, the spiral eyes rotate a little.`

## 5. Машет рукой — `wave`, `wave_1…2`

**Референсы:** `character-reference.png`, `stand.png`. **Опора:** ступни.
```
Full body, standing exactly like the attached stand.png (same scale and feet line), the right arm raised
high, the hand waving hello, eyes happy curves, flames a bit brighter. Canvas 1024x1536, vertical.
```
`wave_1`, `wave_2`: `frame {N} of 2 of the waving loop: the raised hand tilts to the {left|right}; nothing
else moves.`

## 6. Выглядывает — `peek`, `peek_blink`

**Референсы:** `character-reference.png`, `stand.png`.
**Край окна — левая граница холста.** Видна только голова с рожками и одна рука из-за левого края.
**Опора:** левый край, x = 0, y ≈ 0,5.
```
Only the head with the flame horns and the left hand of the character are visible, peeking out from
behind the LEFT edge of the image as if from behind a wall: the hand grips the edge, the head leans out
to the right, curious eyes. Everything else is cut off by the left edge. The head is the same size as in
the attached stand.png. Canvas 1024x1536, vertical, the head at mid-height.
```
`peek_blink` — тот же кадр с закрытыми глазами (формула «Exactly the same image…» как в §2).

## 7. Зевает — `yawn`, `yawn_1`

**Референсы:** `character-reference.png`, `stand.png`. **Опора:** ступни.
```
Full body, standing exactly like the attached stand.png (same scale and feet line), stretching and
yawning: arms raised up, eyes squeezed shut, mouth wide open in a yawn, flames low and sleepy.
Canvas 1024x1536, vertical.
```
`yawn_1` — `the end of the yawn: arms coming down, one hand rubbing an eye, mouth closing.`

## 8. Танцует — `dance_1…4`

**Референсы:** `character-reference.png`, `stand.png`, `walk.png`. **Опора:** ступни (линия пола та же).
```
Full body, the same scale and feet line as the attached stand.png, frame {N} of 4 of a cute looping
dance: frame 1 — step to the left, arms up; frame 2 — spin a quarter, cloak flaring; frame 3 — step to the
right, arms out; frame 4 — little hop, both boots slightly off the ground. Happy eyes. Canvas 1024x1536,
vertical.
```

---

## Проверки (кратко, подробно — FRAMES.md §6)
- фон прозрачный, ореола и букв нет;
- маска 175–200 px в высоту (на мордашке не применяется — здесь мордашек нет);
- опора там, где указано в группе; у §3 — руки и сапоги на линии x ≈ 0,85;
- наушники и микрофон одинаковые во всех кадрах §1–2;
- варианты «Exactly the same image» совпадают с основой до пикселя.

Готовые кадры — в одну папку с этими именами, пришлите путь.

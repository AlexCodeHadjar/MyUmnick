# Промпты для генерации поз персонажа (GPT, генерация картинок)

Для «Сопровождения» (Этап 23, раздел 7.2): одна PNG на позу, по образцу Capri. Промпты — на английском:
генераторы картинок понимают его точнее. Передавайте их в GPT **по одному, в одном и том же чате**, чтобы
персонаж не «плыл» от позы к позе.

## Как действовать
1. Приложите к первому сообщению картинку вашего персонажа (ту, что в окошке) и отправьте **шаг 1** —
   получите эталонный лист персонажа.
2. Дальше в том же чате отправляйте промпты поз из **шага 2** по одному. Каждый начинается с общего блока
   требований — он уже вставлен в каждый промпт.
3. Сохраните каждую картинку под именем из заголовка (`stand.png`, `sit_edge.png` …) в одну папку.
4. В окне программы: правая кнопка на окошке персонажа → «Позы спутника (папка PNG)…» → выберите папку.

Размер и прозрачность: просите **PNG с прозрачным фоном, вертикальный формат 1024×1536**. Холст программы —
1 : 2; масштаб и линию ступней программа подгонит сама, если персонаж во всех позах одного роста и целиком
в кадре.

---

## Шаг 1 — эталонный лист (с приложенной картинкой персонажа)

```
Using the attached image as the exact character design, create a character reference sheet of this same
character: full body, front view and 3/4 view facing right, neutral standing pose, arms relaxed.
Keep the face, hairstyle, outfit, colors and proportions identical to the attached image.
Clean 2D anime illustration style, crisp lineart, soft cel shading, light from the top-left.
Plain transparent background, no floor, no shadow, no text, no frame.
PNG, 1536x1024.
```

---

## Шаг 2 — позы

Общий блок уже внутри каждого промпта. Если GPT отвечает картинкой с фоном — напишите:
«same image, but with a fully transparent background, PNG».

### stand.png — стоит (обязательно)
```
Same character as the reference sheet, identical design. Full body, 3/4 view facing RIGHT.
Pose: standing relaxed, weight on one leg, arms loose, friendly calm expression.
Requirements: the whole body fits in frame from top of the hair to the soles, the character height is about
92% of the image height, centered horizontally, the soles touch the bottom with a small 3% margin.
Same scale, style and lighting (top-left) as before. Transparent background, no floor, no shadow, no text.
PNG, 1024x1536, vertical.
```

### sit_edge.png — сидит на верхнем крае окна, ноги свешены вниз (обязательно)
```
Same character as the reference sheet, identical design. Full body, 3/4 view facing RIGHT.
Pose: sitting on the top edge of an invisible ledge, legs hanging down over the edge and slightly swinging,
hands resting on the ledge beside the hips, relaxed curious expression. The buttocks rest on a straight
invisible horizontal line at about 62% of the image height; nothing is drawn under the character.
Same scale as the standing pose (the character would be the same size if standing up).
Same style and top-left lighting. Transparent background, no ledge drawn, no shadow, no text.
PNG, 1024x1536, vertical.
```

### held.png — его держат мышью, болтается (обязательно)
```
Same character as the reference sheet, identical design. Full body, 3/4 view facing RIGHT.
Pose: being lifted by the back of the collar from above, body dangling, arms and legs hanging loosely,
slightly surprised, comic expression. The grab point (back of the collar) is at the very top center of the
image. Same scale as the standing pose. Same style and top-left lighting.
Transparent background, no hand drawn, no shadow, no text. PNG, 1024x1536, vertical.
```

### laydown.png — лежит на крае окна (обязательно)
```
Same character as the reference sheet, identical design. Full body, side view, head on the LEFT.
Pose: lying on the side on an invisible flat surface, propped on one elbow, relaxed and bored expression.
The body rests on an invisible horizontal line at about 92% of the image height.
Same scale as the standing pose. Same style and top-left lighting.
Transparent background, no surface drawn, no shadow, no text. PNG, 1024x1536, vertical.
```

### sleep.png — спит (обязательно)
```
Same character as the reference sheet, identical design. Full body, side view, head on the LEFT.
Pose: curled up asleep on an invisible flat surface, eyes closed, peaceful expression, maybe a small "z".
The body rests on an invisible horizontal line at about 92% of the image height.
Same scale as the standing pose. Same style and top-left lighting.
Transparent background, no surface drawn, no shadow. PNG, 1024x1536, vertical.
```

### perch_corner.png — сидит боком на углу окна (желательно)
```
Same character, identical design. Full body. Pose: sitting sideways on the corner of an invisible ledge,
one leg hanging down, the other bent, one hand on the corner, looking to the RIGHT.
Buttocks on an invisible horizontal line at about 62% of the image height. Same scale as the standing pose.
Same style and lighting. Transparent background, no ledge drawn, no shadow, no text. PNG, 1024x1536.
```

### hang_side.png — висит, держась за край сверху (желательно)
```
Same character, identical design. Full body, facing the viewer slightly to the RIGHT.
Pose: hanging from an invisible edge with both hands above the head, body and legs hanging down, playful
expression. The hands are at the very top center of the image. Same scale as the standing pose.
Same style and lighting. Transparent background, no edge drawn, no shadow, no text. PNG, 1024x1536.
```

### lean_side.png — стоит, облокотившись о край справа (желательно)
```
Same character, identical design. Full body, 3/4 view facing RIGHT.
Pose: standing and leaning the right shoulder against an invisible vertical wall on the right side of the
image, arms crossed, cool relaxed expression. Soles touch the bottom with a small 3% margin.
Same scale as the standing pose. Same style and lighting. Transparent background, no wall drawn. PNG, 1024x1536.
```

### sit_corner.png — сидит на полу в углу экрана (желательно)
```
Same character, identical design. Full body, 3/4 view facing RIGHT.
Pose: sitting on the floor with knees up, back leaning against an invisible wall, arms around the knees,
calm expression. Buttocks on the floor line at about 95% of the image height.
Same scale as the standing pose. Same style and lighting. Transparent background. PNG, 1024x1536.
```

### float.png — в прыжке, парит (желательно)
```
Same character, identical design. Full body, 3/4 view facing RIGHT.
Pose: mid-jump, legs tucked, arms slightly raised, excited expression, a little motion in the hair and clothes.
Body centered in the image. Same scale as the standing pose. Same style and lighting.
Transparent background, no shadow, no motion lines. PNG, 1024x1536.
```

### walk.png — шаг (желательно)
```
Same character, identical design. Full body, side view walking to the RIGHT, mid-stride, arms swinging,
cheerful expression. Soles on the bottom line with a small 3% margin. Same scale as the standing pose.
Same style and lighting. Transparent background, no shadow. PNG, 1024x1536.
```

---

## Шаг 3 — варианты для моргания и речи (по желанию)

Для каждой позы, у которой хотите моргание и «говорящий» рот (лучше всего — `stand`, `sit_edge`, `laydown`),
отправьте **сразу после картинки позы**:

`<поза>_blink.png`
```
Exactly the same image as the previous one — identical pose, framing, scale and position of every pixel —
but with the eyes closed. Transparent background. PNG, 1024x1536.
```

`<поза>_talk.png`
```
Exactly the same image as the previous one — identical pose, framing, scale and position of every pixel —
but with the mouth open as if speaking. Transparent background. PNG, 1024x1536.
```

Если вариант «съехал» относительно позы (персонаж сдвинулся или изменился в размере), лучше обойтись без
него: программа покажет моргание и речь как сможет и без этих картинок.

---

## Шаг 4 — промежуточные кадры для плавной анимации (по желанию)

Программа уже умеет проигрывать кадры. Как это работает:
- **Цикл позы.** Кадры `<поза>_1.png`, `<поза>_2.png`, … крутятся по кругу. Частота: ходьба 10 кадров в секунду,
  болтание в руке и полёт 8, ожидание и сидение на краю 5, лёжа 4, сон 3.
- **Рот.** Кадры `<поза>_talk_1…_N` выбираются по громкости голоса: `_1` приоткрыт … `_N` открыт широко.
  Закрытый рот — сама поза.
- **Моргание.** Кадр `<поза>_blink_1` — полуприкрытые глаза, он встаёт до и после закрытых (`<поза>_blink`).

Нет кадров — показывается одна картинка позы, как сейчас. Можно делать по одной группе за раз.

**Главное правило для GPT:** генерируйте кадры **в том же чате, сразу после картинки позы**, и каждый раз
требуйте тот же холст, масштаб и положение. В конце каждого промпта ниже уже стоит общий хвост:

```
Keep the exact same canvas (1024x1536), the same character scale and the same position in the frame as the
reference pose image; only the described parts move. Same style, same top-left lighting, same colors.
Transparent background, no shadow, no text, no motion lines. PNG, 1024x1536.
```

Порядок — от самого заметного к менее заметному.

### 1. Ходьба — `walk_1.png … walk_8.png` (8 кадров, цикл)
Сначала пришлите GPT готовую `walk.png` и попросите кадр 1, затем каждый следующий — «next frame».
```
Using the walking pose image as the reference, draw frame {N} of 8 of a seamless walk cycle to the RIGHT,
side view. Frame 1: right foot forward touching the ground, left foot back (contact). Frame 2: body lowest,
weight on the right foot (down). Frame 3: left leg passing the right one (passing). Frame 4: body highest,
right foot pushing off (up). Frames 5–8: the same four phases with the legs swapped. Arms swing opposite to
the legs, the cloak and the blue flame horns trail slightly behind. The soles of the supporting foot stay on
the same ground line in every frame.
Keep the exact same canvas (1024x1536), the same character scale and the same position in the frame as the
reference pose image; only the described parts move. Same style, same top-left lighting, same colors.
Transparent background, no shadow, no text, no motion lines. PNG, 1024x1536.
```
Замените `{N}` на 1…8 — восемь отдельных сообщений.

### 2. Сидит на краю, болтает ногами — `sit_edge_1.png … sit_edge_4.png` (4 кадра, цикл)
```
Using the sit_edge image as the reference, draw frame {N} of 4 of a gentle looping idle: sitting on the
invisible ledge, legs swinging slowly back and forth (frame 1 legs back, 2 middle, 3 legs forward, 4 middle),
the cloak hem and the flame horns flicker softly. The seat, the hands on the ledge, the head and the body stay
exactly in place.
Keep the exact same canvas (1024x1536), the same character scale and the same position in the frame as the
reference pose image; only the described parts move. Same style, same top-left lighting, same colors.
Transparent background, no shadow, no text, no motion lines. PNG, 1024x1536.
```

### 3. Стоит, «дышит» — `stand_1.png … stand_4.png` (4 кадра, цикл)
```
Using the stand image as the reference, draw frame {N} of 4 of a subtle looping idle animation: a slow
breath (frame 1 neutral, 2 chest and hood slightly up, 3 neutral, 4 slightly down), the cloak hem sways a
little, the blue flame horns flicker (different flame shapes in each frame). Feet stay exactly in place.
Keep the exact same canvas (1024x1536), the same character scale and the same position in the frame as the
reference pose image; only the described parts move. Same style, same top-left lighting, same colors.
Transparent background, no shadow, no text, no motion lines. PNG, 1024x1536.
```

### 4. Рот при речи — `stand_talk_1…3`, `sit_edge_talk_1…3`, `laydown_talk_1…3`
Для каждой из трёх поз — три кадра, сразу после картинки этой позы:
```
Exactly the same image as the {pose} reference — identical pose, framing, scale and position of every
pixel — but the mouth is {mouth}. Nothing else changes.
Transparent background. PNG, 1024x1536.
```
Вместо `{mouth}`: кадр 1 — `slightly open`, кадр 2 — `open as if saying "ah"`, кадр 3 — `wide open, excited`.

### 5. Полуприкрытые глаза — `stand_blink_1`, `sit_edge_blink_1`, `laydown_blink_1`
```
Exactly the same image as the {pose} reference — identical pose, framing, scale and position of every
pixel — but the eyes are half closed (halfway through a blink). Nothing else changes.
Transparent background. PNG, 1024x1536.
```

### 6. Болтается в руке — `held_1.png … held_4.png` (4 кадра, цикл)
```
Using the held image as the reference, draw frame {N} of 4 of a looping dangle: the character hangs by the
tip of the hood, the body swings slightly like a pendulum (frame 1 left, 2 center, 3 right, 4 center), legs
and arms trail the swing, small comic struggle. The tip of the hood stays exactly at the same point.
Keep the exact same canvas (1024x1536), the same character scale and the same position in the frame as the
reference pose image; only the described parts move. Same style, same top-left lighting, same colors.
Transparent background, no shadow, no text, no motion lines. PNG, 1024x1536.
```

### 7. Сон — `sleep_1.png … sleep_3.png` (3 кадра, цикл)
```
Using the sleep image as the reference, draw frame {N} of 3 of a calm sleeping loop: slow breathing (the
back rises a little in frame 2), the flame horns flicker softly, a small "z" floats up and fades
(frame 1 none, 2 small, 3 higher and fainter). The body stays in place on the same line.
Keep the exact same canvas (1024x1536), the same character scale and the same position in the frame as the
reference pose image; only the described parts move. Same style, same top-left lighting, same colors.
Transparent background, no shadow, no text, no motion lines. PNG, 1024x1536.
```

### 8. Полёт — `float_1.png … float_3.png` и 9. Висит — `hang_side_1.png … hang_side_4.png`
```
Using the {pose} image as the reference, draw frame {N} of {count} of a looping animation: for float — the
cloak and flames flutter upward, legs kick gently; for hang_side — the body sways slightly under the
hands, legs swing. The {anchor} stays exactly at the same point.
Keep the exact same canvas (1024x1536), the same character scale and the same position in the frame as the
reference pose image; only the described parts move. Same style, same top-left lighting, same colors.
Transparent background, no shadow, no text, no motion lines. PNG, 1024x1536.
```
Вместо `{anchor}`: для `float` — `center of the body`, для `hang_side` — `fists`.

**Куда класть:** в ту же папку, что и позы, с этими именами. Потом напишите мне: я подгоню кадры так же, как
позы (`README.md`), и добавлю их во встроенный пакет. Если кадр «съехал» и дёргает анимацию, я его выброшу.

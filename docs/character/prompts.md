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

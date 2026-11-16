# Mafia: The Old Country — UI Research & Takeaways for ATOF

**Дата:** 2026-11-16  
**Автор:** Агент 6 (дослідження без змін коду)  
**Scope:** HUD, мінімапа/навігація, підказки, меню, цілі, розшук, водіння.  
**Метод:** websearch/webfetch (розділи 2K patch notes, FAQ, accessibility review, гайди Game8/Spottis, портфоліо UI-дизайнерки Anna Wikström, Steam-обговорення) + читання `docs/gta_ui_research.md`, `docs/ui_best_practices_atof.md` та `engine.py`.

> **Про непевні факти.** Гра вийшла у серпні 2025 (DLC/патчі — пізніше 2025/2026), тож джерел порівняно небагато, а частина — маркетингові нотатки або фанатські гайди. Нижче факти позначено як **[підтверджено]** (офіційні patch notes/FAQ/портфоліо розробників), **[ймовірно]** (гайди/огляди) та **[непевно]** (логічне виведення або поодинокі свідчення) — особливо це стосується системи розшуку.

---

## 1. Ключові патерни UI Mafia: The Old Country

### 1.1 Головна філософія — мінімалізм («just enough»)

- **[підтверджено]** Anna Wikström (UI-дизайнерка гри) прямо формулює головний принцип: *«keep the information and UI minimalistic, so we opted to use icons over text, and we focused on giving the right information at the right time and hiding UI when it wasn't needed to allow the game visuals and cinematic style to really shine»*. Вона працювала над усіма аспектами HUD, включно зі станами пошкоджень/здоров'я.
  Джерело: https://www.annawikstrom.com/mafia-theoldcountry
- **[підтверджено]** Офіційні patch notes додали опцію **Contextual HUD**: елементи HUD приховані за замовчуванням і з'являються на кілька секунд після натискання **Ping** (PC — `TAB`, PS — touchpad, Xbox — View). Рекомендовано для другого проходження / досвідчених гравців.
  Джерела: https://mafia.2k.com/the-old-country/patch-notes , https://support.2k.com/hc/en-us/articles/46412050778003
- **[підтверджено]** Режим **Cinema Siciliano** — ч/з-фільтр, сицилійська озвучка, «clutter-free / minimal on-screen UI»; **Classic Difficulty** — «fewer HUD indicators». Тобто кількість HUD-елементів є **настравуваною**, а не фіксованою.
  Джерело: https://www.pcgamingwiki.com/wiki/Mafia:_The_Old_Country , patch notes

**Патерн:** HUD як *шар, що реагує на контекст і налаштування*, а не постійна панель. Іконка замість тексту; вимога — «правильна інформація в правильний момент».

### 1.2 Навігація без мінімапи — фішкова філософія гри

- **[підтверджено]** У Mafia: TOC **немає мінімапи** (на відміну від попередніх частин) — це свідомий дизайнерський вибір; у Steam-обговоренні гравці скаржаться на відсутність мінімапи та можливості ставити маркери.
  Джерело: https://steamcommunity.com/app/1941540/discussions/0/596283752196503433
- **[підтверджено]** Замість неї — **дорожні знаки (Navigation Signage)**: фізичні об'єкти вздовж доріг, які вказують напрямок до цілі, розроблені спільно з tech-art так, щоб бути видимими на скелястому/зеленому рельєфі; опція в `Settings > Gameplay`, увімкнена за замовчуванням. Це **diegetic**-навігація (знак у світі, а не плаваючий UI).
  Джерела: портфоліо Anna Wikström; https://gamerstogether.cz/en/mafia-the-old-country-beginners-guide
- **[ймовірно]** Повна карта відкривається клавішею `M`/«Map/Objectives»; маркер цілі оновлюється, карта може бути **контекстуальною** (локальна замість глобальної в певних зонах/інтер'єрах). Гравці мусять покладатися на ланцюг місій + візуальні орієнтири (church tower, вивіски, перехрестя) як «ментальну сітку».
  Джерело: https://umatechnology.org/mafia-the-old-country-does-not-have-an-open-world-map-2 (низькоякісне джерело — ставитися обережно)
- **[підтверджено]** Оновлення Journal додало описи глав і видимість записів між проходженнями — тобто «цілі/історія» живуть у журналі, а не в постійному HUD-трекері.
  Джерело: patch notes

**Патерн:** навігація = **маркер цілі + diegetic-знаки + повна карта + ланцюг місій**; постійної мінімапи немає навмисно. Це найбільш «не-GTA» рішення гри і головний урок для ATOF.

### 1.3 Підказки та взаємодія

- **[підтверджено]** Patch notes: «Improved how interaction icons look and behave during story missions» — тобто підказки — це **іконки**, контекстні для сюжетних місій.
  Джерело: patch notes
- **[підтверджено]** Схема керування має **Primary interact / Secondary interact** (`E` / `Y` на PC за гайдом), а також `Ping HUD` (`TAB`). Підказки мають бути прив'язані до поточного контексту (пішки / авто / кінь / дуель — чотири окремі схеми керування).
  Джерела: https://www.magicgameworld.com/mafia-the-old-country-controls-guide-pc-xbox-ps5-keybinds , https://www.spottis.com/games/mafia-the-old-country-controls
- **[підтверджено]** У ** дуелях ножів** (boss fights) дії (`Strike`, `Thrust`, `Slash`, `Parry`, `Dodge`) **постійно виведені на HUD** — бо бійці не повинні згадувати керування, а мають залишатися зануреними в дуель. Це приклад того, коли HUD *свідомо не ховається*.
  Джерело: портфоліо Anna Wikström (розділ Knife Duels / Boss fights)
- **[підтверджено]** Туторіали вбудовані в історію: малі (під час гри, ненав'язливі) + великі (з картинками й текстом). 
  Джерело: портфоліо Anna Wikström (FTUE)

**Патерн:** підказка = іконка/гліф + дієслово, реагує на контекст і пріоритет; у «навчальних»/дуельних сценах стає постійною.

### 1.4 Меню та цілі

- **[підтверджено]** Усі екрани кастомізації (Wardrobe / Garage / Stable / Weapon Locker) і **Store** використовують **однакову структуру меню** — щоб гравець фокусувався на 3D-об'єкті в центрі, а не вчив новий інтерфейс. Сторінка магазину перевикористовує layout/взаємодію/код/зображення кастомізаційних екранів. Pause-меню переупорядковане «future-proof» для додавання нових пунктів; блокування опцій реалізоване в Unreal.
  Джерело: портфоліо Anna Wikström
- **[підтверджено]** **Rosary page** — екран підсилень (Medallions і Beads); для розрізнення типів створені **прості іконки**, а саму чотку розміщено на тлі, щоб гравець бачив, яку частину змінює. 
  Джерело: портфоліо Anna Wikström
- **[підтверджено]** Міні-ігри мають власні компактні HUD: Photography, Safe Cracking (введення коду), Choking (таймер + тапання), Car Cranking; для **перегонів** (авто й кінь) створено **спільний UI**, щоб не вчити новий HUD для кожного типу.
  Джерело: портфоліо Anna Wikström

**Патерн:** один універсальний «каркас» меню на всі екрани (економіка/кастомізація), іконки для типів, background-об'єкт як частина меню, спільний HUD для споріднених режимів.

### 1.5 Розшук / поліція — **мало даних, позначено непевним**

- **[непевно]** На відміну від GTA, Mafia: TOC, схоже, **не має класичної системи «зірок розшуку» 1–5**. У грі є переслідування поліцією/владою та механіки «instinct», але публічні джерела, які б описували лічильник розшуку з зірками, відсутні. Покладатися на це не варто.
- **[підтверджено]**(Colorblind/доступність): можна змінювати **колір головного маркера цілі**; є режими для дейтеранопії/протанопії/тританомії; **немає high-contrast режиму**; є субтитри з налаштуванням розміру/кольору/прозорості тла, **HUD Elements Scale**, Simplified Struggle. 
  Джерела: https://caniplaythat.com/2025/08/29/mafia-the-old-country-accessibility-review , https://mafia.2k.com/the-old-country/faq/
- **[ймовірно]** Налаштування «Messaggi»/HUD scale і colorblind для UI означають, що критичні стани (здоров'я, небезпека) мають дублюватися не лише кольором — але офіційного підтвердження «не-колірного» кодування для розшуку немає.

**Патерн (обережний висновок):** система небезпеки в Mafia: TOC подана *мінімально* (іконки/стан здоров'я, «just enough»), а не як яскравий GTA-лічильник; доступність вирішується через масштаб HUD і колір маркера, а не через багату систему попереджень.

### 1.6 Водіння

- **[підтверджено]** Специфічний HUD водія: швидкість у **км/год** (безпечний діапазон ~60–90), механічна коробка (Manual Shifting) і Simulation Driving, вибір камери (з 2025 — **First-Person Driving Camera**), `Look Back`, клаксон, ручне гальмо. Керування під час водіння адаптоване (L1 — дістати/вистрілити, auto-lock цілі).
  Джерела: https://game8.co/games/Mafia-The-Old-Country/archives/543995 , patch notes від 20 листопада 2025, accessibility review
- **[підтверджено]** Навігація під час водіння — diegetic дорожні знаки (див. 1.2) + маркер цілі; **спільний HUD** для авто- та кінних перегонів.
  Джерело: портфоліо Anna Wikström

---

## 2. Що адаптувати в ATOF

| Патерн Mafia: TOC | Що взяти для ATOF (2D top-down pygame) | Що НЕ брати |
|---|---|---|
| Контекстний HUD + «Ping to reveal», опція «менше індикаторів» | Режим **«Immersive HUD»**: більшість елементів приховані, показати на 2–3 с клавішею; у налаштуваннях — «HUD density: Full / Contextual / Minimal» | Не прибирати повністю vitals у постійному режимі — у ATOF це потрібно для читабельності |
| Іконки замість тексту, універсальна структура меню | Довести іконкову мову до спільного «panel primitive» у всіх меню (гараж, скриня, магазин, телефон) | Не перевантажувати 2D-іконками там, де ASCII/текст поки читається гірше |
| Diegetic дорожні знаки замість мінімапи | **Залишити мінімапу** (вона вже є), але додати edge-стрілку + «затримку» GPS-маркера, як у Mafia — напрямок завжди видимий | Не копіювати повну відмову від мінімапи: ATOF — відкритий світ, і це наштовхує на помилки згідно зі Steam-дискусією |
| Постійний HUD у дуелях/туторіалах | У ATOF-боях/завданнях робити підказки керування **стійкими**, а не миготливими | — |
|Colorblind marker color + HUD scale | Додати колір маркера цілі, що налаштовується, і масштабування HUD (уже частково є через Inter-шрифт) | Не покладатися лише на колір (у Mafia бракує high-contrast — не повторювати цю ваду) |
| Спільний HUD для споріднених режимів | Уніфікувати speedometer/водійські підказки для авто і (якщо буде) вершника | — |

**Головний висновок для ATOF:** Mafia: TOC показує протилежну до GTA крайність — «прибрати мінімапу і ховати HUD». Для ATOF правильна не копія, а **компроміс**: зберегти навігаційний радар GTA-стилю, але запозичити у Mafia *керовану контекстність*, *іконкову мову*, *diegetic-напрямок* і *налаштування щільності HUD* — те, що вже частково описане в `docs/gta_ui_research.md` та `docs/ui_best_practices_atof.md`.

---

## 3. Конкретні рекомендації з посиланням на `engine.py`

> Код **не змінювався**; нижче — напрями для майбутньої реалізації.

### 3.1 `draw_gta_minimap(...)` (рядок ~2872) — контекстність і напрямок

- Вже є: круглий радар, кліп по колу, кешований фон (`_get_minimap_background`), clamp-камера, GPS-маркер **на краю** (`_minimap_gps_position`), окремі дуги health/hunger, glass-frame. Це сильна база.
- Додати **режим «Immersive»**: параметр `opacity`/`visible`, керований станом HUD; за замовчуванням 1.0, у режимі Mafia-style — 0.0 з плавним поверненням на `Ping` (2–3 с). Використати вже наявний патерн alpha-поверхонь із `draw_interaction_prompt`.
- Посилити **diegetic-напрямок**: коли GPS-ціль за межею радара, окрім існуючого `_draw_gps_marker` на краю, додати **стрілку/конус** (не лише колір) і відстань (`_format_gps_distance` уже є) — це роль дорожніх знаків Mafia у 2D.
- Додати **символні blips** (різні силуети для house / gunshop / garage / місії) замість/`ordered` з поточними кружечками — Mafia робить ставку на іконки. Підтримати `mission_markers`, що вже передається в функцію.
- Налаштування **колору маркера цілі** (colorblind) — у `_draw_gps_marker` і blip-палітрі винести кольори в токени, а не хардкодити `(255, 112, 0)`.

### 3.2 `draw_interaction_prompt(...)` (рядок ~4319) — іконка + дієслово + пріоритет

- Вже є glass-панель з keycap, `alpha`-fade (`pygame.SRCALPHA`, `set_alpha`) — ідеальний каркас. 
- Стандартизувати формат як у Mafia: **гліф/іконка + коротке дієслово** (`[E] Увійти`, `[F] Взяти`), а не довгі рядки. Підтримати **Primary / Secondary** варіанти (як `E`/`Y`) через пріоритет у `PromptState`.
- Додати **менеджер підказок** із пріоритетом і демпфуванням (не показувати кілька одночасно; nearest-first), щоб уникнути «prompt spam». Використати вже наявний `alpha` для 150–250 мс fade (рекомендація з `docs/ui_best_practices_atof.md`, розд. 3.5).
- **Блоковані стани** (`Не вистачає ₭`, `Інвентар повний`) — окремий стиль (приглушений keycap + іконка блокування), не лише червоний колір.
- У бойових/дуельних сценах робити підказку **стійкою** (приклад ножових дуелів Mafia).

### 3.3 `full_screen_map(...)` (рядок ~4128) — спільна символіка й доступність

- Вже є zoom (колесо), панорамування, встановлення/скидання GPS (`G`/`H`/клік/delete), `mission_markers`. 
- **Уніфікувати symbology** з `draw_gta_minimap`: ті самі кольори/іконки house/gunshop/objective, інакше гравець перевчається (у Mafia всі меню мають одну структуру саме з цієї причини).
- Додати **легенду** (іконка → назва) на повній карті — це компенсує відсутність текстових підказок у diegetic-стилі Mafia.
- Зробити маркер цілі **перебарвлюваним** (colorblind) і додати опцію «контекстуальний zoom/локальна карта» за прикладом Mafia, якщо це доречно до сюжету.
- Зберегти звуковий фідбек (`play_menu_sound("click")`) як приклад «кожна дія = відгук».

### 3.4 `WantedLevel` (рядок ~1280) та `draw_player_status` (рядок ~2799) — системна читабельність

- **[непевно]** Mafia TOC не має GTA-подібних «зірок» — тому не копіювати її «відсутність системи», а зробити **власну** систему розшуку зрозумілою: залишити 0–5, але додати іконки/силуети замість ASCII `"* "` у `draw_player_status` (зараз `stars = "* " * wanted_level`), який важко читати.
- Показувати розшук **контекстно**: якщо `level == 0` — не малювати рядок взагалі (у Mafia приховано, поки не потрібно); з'являти з пульсацією/іконкою при підвищенні — це дух «just enough + right time».
- Використати `escape_timer` для **візуального таймера заспокоєння** (кільце/прогрес), як у GTA VI-репортажів про «evidence/search state» — гравець має розуміти *чому* і *скільки ще*.
- Дублювати стан **не кольором**: форма зірок + кількість + короткий текст (`Розшук 3/5`), сумісно з рекомендацією accessibility з `docs/ui_best_practices_atof.md` (розд. 3.8).
- Врахувати, що у Mafia бракує high-contrast режиму — у ATOF передбачити його заздалегідь у токенах.

### 3.5 Наскрізне (підтримано обома попередніми документами)

- Винести в один модуль **UI-токени**: кольори semantic (friendly/objective/danger/wanted), розміри, motion-тривалості (120–250 мс), повторно використати `get_house_icon` і glass-panel з `draw_interaction_prompt`.
- Кешувати статичні поверхні (уже робиться для мінімапи/шрифтів) — не створювати `SRCALPHA` щокадр.
- Локалізація EN/UA/RU/ES/DE/FR: короткі verb-first рядки, auto-width панелей (у `draw_interaction_prompt` ширина вже залежить від тексту).

---

## 4. Джерела

1. Anna Wikström — Mafia: The Old Country (портфоліо UI-дизайнерки): https://www.annawikstrom.com/mafia-theoldcountry
2. 2K — Patch Notes (Contextual HUD, Cinema Siciliano, Classic Difficulty, Free Ride): https://mafia.2k.com/the-old-country/patch-notes ; https://support.2k.com/hc/en-us/articles/46412050778003
3. 2K — FAQ (accessibility, Navigation Signage): https://mafia.2k.com/the-old-country/faq/
4. Can I Play That? — accessibility review (colorblind, HUD scale, knife durability counter): https://caniplaythat.com/2025/08/29/mafia-the-old-country-accessibility-review
5. PCGamingWiki — Mafia: The Old Country (HUD/colorblind settings): https://www.pcgamingwiki.com/wiki/Mafia:_The_Old_Country
6. Game8 — Driving Guide / Controls / Best Settings: https://game8.co/games/Mafia-The-Old-Country/archives/543995 , .../542950 , .../542204
7. Spottis — Controls (4 схеми: on foot/vehicle/horse/duel): https://www.spottis.com/games/mafia-the-old-country-controls
8. Magic Game World — Controls Guide (PC keybinds): https://www.magicgameworld.com/mafia-the-old-country-controls-guide-pc-xbox-ps5-keybinds
9. Steam Discussions — «Why no mini-map on the HUD anymore?»: https://steamcommunity.com/app/1941540/discussions/0/596283752196503433
10. UMATechnology — «Does Not Have An Open-World Map» (низька надійність, використано обережно): https://umatechnology.org/mafia-the-old-country-does-not-have-an-open-world-map-2
11. Локальні: `docs/gta_ui_research.md`, `docs/ui_best_practices_atof.md`, `engine.py` (draw_gta_minimap ~2872, draw_interaction_prompt ~4319, full_screen_map ~4128, WantedLevel ~1280, draw_player_status ~2799).

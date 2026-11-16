# UI Mafia III — дослідження та рекомендації для ATOF

**Дата:** 2026-11-16  
**Агент:** 5 із 14 (дослідження без змін коду)  
**Сфера:** HUD, мінімапа/GPS, підказки, меню, цілі/mission tracker, розшук/поліція, водіння.  
**Метод:** веб-пошук/вибірковий веб-фетч (головним чином Mafia III, частково Mafia: Definitive Edition як еволюція тих самих рішень) + аналіз репозиторію ATOF (`engine.py`, `docs/gta_ui_research.md`, `docs/ui_best_practices_atof.md`).  
**Примітка:** Mafia III (2016) і Mafia: Definitive Edition (2020) — це різні ігри; DE додав HUD-опції, яких не було в оригіналі. Нижче це розрізнено. Джерела й оцінки зібрані з відкритих обговорень/оглядів, тому сприймати їх як *спостережувані/репортовані* патерни, а не як офіційну специфікацію 2K.

---

## 1. Ключові патерни UI Mafia III

### 1.1. HUD та розкладка
- Оригінальний Mafia III мав щільний, «жорстко вмонтований» HUD: смужки здоров'я/боєприпасів, **великий блок «CURRENT OBJECTIVE» у верхньому лівому куті**, мінімапу з GPS, спідометр та індикатор розшуку. Гравці масово скаржилися, що блок цілі «займає ~15% екрана й постійно затемнює кут», і просили можливість його вимкнути (Reddit r/Mafia3, NexusMods «HUD Begone — Radar Removed»).
- IGN-огляд прямо зазначав: «the interface might not have been a joy to work with» — тобто естетика й читабельність інтерфейсу були слабким місцем попри сильну подачу світу/радіо.
- **Еволюція в DE:** у першому оновленні додали кастомні HUD-опції — вмикати/вимикати in-world маркер головної цілі, маркери ворогів на мінімапі, turn-by-turn підказки та мінімап-GPS, а також «Minimal HUD mode», що приховував мінімапу, спідометр і текст цілі (Wccftech, 2K). Оновлення до 10-ї річниці Mafia III обіцяло «UI clarity and consistency across menus and HUD elements» (GamingTrend).
- **Урок:** навіть у реалістичній грі гравці цінують *можливість прибрати* постійні елементи; «тихий» HUD за замовчуванням + перемикачі — безпечніший вибір, ніж нав'язаний щільний HUD.

### 1.2. Мінімапа та навігація (найсильніша сторона патерну)
- У Mafia III **дві системи навігації**: (1) звичайна мінімапа з лінією маршруту; (2) **diegetic in-world GPS** — чорні дорожні знаки зі стрілками з'являються прямо у світі на кожному перехресті, підказуючи поворот (ResetEra «Mafia III In-World GPS System is Amazing», скріншоти J3Bxq9A/xqnHtsZ/Y6k1yCn).
- Спільнота назвала це «найкращим GPS в open-world грі»: менше дивишся на мінімапу, більше — на дорогу/довкілля; «I end up spending more time enjoying the environments than looking at the mini-map». Водночас частина гравців відзначала *надмірність*: мати і знаки, і лінію на мінімапі одночасно — дублювання («feels redundant while also having the path on the mini-map»).
- **Урок:** навігаційний сигнал може бути винесений у світ і бути *контекстним* (з'являтися лише там, де потрібен поворот), але він має не конфліктувати/не дублювати HUD-маршрут без можливості вибору. Для 2D top-down це означає «тонкий» маршрут на радарі + дискретні вказівники при досягненні поворотної точки, а не постійний яскравий шлейф.

### 1.3. Цілі / mission tracker
- «CURRENT OBJECTIVE» — постійний блок уверху, який критикували за розмір і за те, що завжди затемнює кут; у DE маркер цілі у світі став перемикачем.
- Місії Mafia III побудовані навколо району (district): звільнення районів, боротьба з ворожими угрупованнями; головна ціль подається і текстом, і маркером у світі, і на карті.
- **Урок:** тримати **одну активну ціль**, компактно, з перемикачем і з узгодженим маркером на мапі/у світі; не робити великий постійний блок.

### 1.4. Розшук / поліція
- Попри відсутність класичних GTA-зірок у деяких описах, у грі є механіка **notoriety/heat** (поліційна увага, прив'язана до району): скоєння злочинів підвищує увагу, поліція реагує, «зняти» увагу можна (втеча, зміна авто/одягу тощо). Deadeye-подібні мініігри (наприклад, crowbar lock) залежать від HUD, і мод, який прибирає радар, ламає цю мінігру (NexusMods-коментарі) — ознака, що HUD був тісно інтегрований у геймплей.
- **Урок (порівняння з GTA VI, див. `gta_ui_research.md`):** сучасний тренд — показувати *стан системи* (напр.: переслідують / просто шукають / увага спадає), а не лише число. Для ATOF це ключове: `WantedLevel` вже має `escape_timer` і `nearby_police`, але HUD показує лише зірки текстом.

### 1.5. Водіння
- Спідометр + радіо (музика Mafia III — окрема сильна риса, яку хвалять навіть критики гри). У меню опцій можна вибрати **normal vs simulation driving mode** (Fandom, Gameplay Mechanics in Mafia III).
- Під час водіння задіюється in-world GPS (п. 1.2), тож основна увага — на дорозі.
- **Урок:** спідометр має бути «підручним», але не домінувати; режим водіння й навігація — окремі перемикачі.

### 1.6. Підказки та меню
- Скарги на надлишок маркерів взаємодії: «pretty much anything that you can interact with has a hud marker on it, be it a door, including all car doors, guns on the…» (Steam Discussions). Тобто треба **пріоритизувати**: показувати найближчу/найважливішу дію, а не все.
- Меню/інтерфейс Mafia III критикували за незручність; DE виправив «clarity and consistency across menus and HUD elements».
- **Урок:** один компонент підказки з пріоритетом і плавним fade + єдина мова панелей у всіх меню.

---

## 2. Що адаптувати в ATOF

| Патерн Mafia III | Чому цінно для ATOF (2D top-down pygame) | Як адаптувати |
|---|---|---|
| Diegetic GPS / контекстні дорожні знаки | Зменшує потребу дивитися на мінімапу; економлять центр екрана | Замість 3D-знаків — легкі «edge-стрілки» на радарі + рідкісні вказівники повороту у світі при наближенні до цілі |
| Перемикачі HUD-елементів (DE) | Гравці хочуть прибрати постійний objective block | Додати перемикачі: «показувати ціль», «маркери ворогів», «GPS-лінію», «мінімальний HUD» |
| Компактна, одна активна ціль | Менше когнітивного навантаження; уникнути «15% екрана» скарг | Один chip цілі з відстанню/іконкою, а не великий блок |
| Стан розшуку, а не лише число | Пояснює *чому* переслідують і *коли* відстане | Розширити `WantedLevel` у HUD: іконка стану (переслідування / пошук / затухання) + лічильник часу втечі |
| Пріоритет підказок | Уникнути спаму маркерів («все has a marker») | Одна підказка з пріоритетом/найблизкістю + fade (вже частково є в ATOF) |
| Єдина мова меню (DE clarity fix) | Менше вивчень, консистентність | Використати вже наявні `_cached_ui_font`, скляні панелі, orange accent у всіх меню |
| Спідометр як «підручний» індикатор | Водіння — важлива частина геймплею | Залишити поруч із радаром (вже зроблено), додати стан уваги поліції поруч |

**Чого НЕ копіювати:** щільний постійний «CURRENT OBJECTIVE» блок, дублювання маршруту одночасно і знаками, і яскравою лінією без опції вибору, залежність критичних мініігор від HUD (MOD-проблема) — у ATOF підказки мають мати HUD-фолбек.

---

## 3. Конкретні рекомендації з посиланням на `engine.py`

> Усі посилання — на поточний стан файлу `/home/atom/Завантажене/проекти/ATOF/engine.py`. Код не змінювався.

### 3.1. `draw_gta_minimap(...)` (рядок 2872)
Поточні можливості: круглий радар із clamp-камерою, `preserve_aspect`, `zoom`, кешований фон (`_get_minimap_background`), маркер гравця, house icon, `_draw_gps_marker` на краю радара (рядки 2968–2979), окремі дуги здоров'я/голоду (3015–3060), frosted-glass шар (3062–3072), hook `mission_markers` через `ui_story` (3082–3102), відстань над радаром (3131–3137).

Рекомендації:
1. **Додати стан розшуку в/навколо радара.** Використати дані `WantedLevel` (див. 3.4) для пульсації зовнішнього кільця/arc: наприклад, змінити колір `rim lights` (рядки 3009–3012) і додати тонкий black/red search-arc поверх звичайних ліній. Це дасть «system legibility» за мотивами Mafia III notoriety та GTA VI heat.
2. **Контекстний GPS замість постійної яскравої лінії.** `_draw_gps_marker` (2969–2979) уже показує ціль на краю — додати *рідкісну* стрілку-поворот, яка з'являється лише коли напрямок до цілі змінився на ≥~30°, і зникає (TTL), замість того щоб постійно світити маркер. Менше дублювання — прямий урок критики GPS у Mafia III.
3. **Вороги/поліція — як окремі blips з формою, а не лише кольором.** У `mission_markers` hook (3082) додати blips поліції з унікальною silhouette (напр. щит/синій ромб) і легенду у full map; це відповідає DE-опції «enemy markers on/off».
4. **Мінімальний HUD-режим.** Огорнути малювання дуг (3015–3060), frosted-шару (3062–3072) і distance-тексту (3131) у прапорець `hud_mode`, щоб за бажання лишався лише circular radar — це точна адаптація DE «Minimal HUD mode».
5. **Зберегти продуктивність:** наявний `_get_minimap_background` і `SRCALPHA`-поверхні вже є правильним напрямком; нові ефекти робити на кешованих surface-ах, не створювати щокадрово (див. `ui_best_practices_atof.md` §6).

### 3.2. `draw_interaction_prompt(...)` (рядок 4319)
Поточні можливості: скляна панель lower-left з keycap, `alpha` fade (4321–4377), orange accent (4358, 4363), повертає `panel, key_rect, label_rect`.

Рекомендації:
1. **Пріоритет/черга підказок.** Зробити тонкий PromptState (не змінюючи самого draw): `{key, verb, priority, ttl, alpha}`; викликати `draw_interaction_prompt` лише для найпріоритетнішої/найближчої дії. Прямий антидот до скарги «все has a hud marker» у Mafia III.
2. **Плавний fade вже підтримується** — використати `alpha` (4341–4376) з dt-based інтерполяцією 150–250 мс (див. приклад у `gta_ui_research.md` §6.2).
3. **Стани available/blocked.** Додати варіант із приглушеним стилем для «Не вистачає ₭ / Інвентар повний» (уникає логіки Mafia III, де HUD-маркер обіцяв дію, яку не можна виконати).
4. **Зв'язати з keybinds** — підпис keygen уже приймається як рядок; брати його зі settings/controls, як рекомендовано в `ui_best_practices_atof.md` §3.5.

### 3.3. `full_screen_map(...)` (рядок 4128)
Поточні можливості: zoom колесом (4170–4172), pan WASD (4204–4207), клік — set destination, ПКМ/DELETE — clear (4173–4192), гарячі G/H (4193–4198), house/gunshop/player/GPS маркери (4230–4262), `mission_markers` hook (4264), hints bar (4288–4309), distance (4280–4286).

Рекомендації:
1. **Легенда маркерів.** На базові іконки (будинок, G, гараж, GPS) додати компактну легенду в куті — у Mafia III DE саме «clarity and consistency» була головним виправленням. Використати `_cached_ui_font` і ті самі кольори, що й у радарі (напр. orange `255,112,0` з `_draw_gps_marker`, 2826).
2. **Синхронізація symbology з мінімапою.** Наразі `draw_gta_minimap` і `full_screen_map` мають окремі шляхи малювання маркерів — винести спільні кольори/форми в константи, щоб «map = minimap = objective» (принцип з обох docs).
3. **Підказки при set/clear.** Уже є `play_menu_sound("click")` (4183, 4186, 4192…) — додати короткий візуальний toast/спалах маркера для підтвердження, не збільшуючи hints bar.
4. **«Маршрут лише за потреби».** Замість постійно видимого GPS-маркера — показувати маршрут/лінію лише коли до цілі < певного порогу (або за окремим перемикачем) — урок подвійної навігації Mafia III.

### 3.4. `WantedLevel` (рядок 1280) + HUD-відображення
Поточні можливості: `level` 0–5, `raise_level`, `escape_timer = 1800 + level*600` (1285–1287), `update` зменшує таймер, але **не зменшує, якщо `nearby_police=True`** (1289–1296), `clear`. Відображення — у `draw_player_status` (2799–2814) як текст `Wanted: * * * - -` у верхньому лівому куті.

Рекомендації:
1. **Показувати стан, а не лише зірки.** Використати вже наявні поля: якщо `nearby_police` → стан «переслідують/поліція поруч»; інакше якщо `escape_timer > 0` → «йде пошук, залишилось N с»; це зробить system legibility як у Mafia III notoriety / GTA VI heat (див. `gta_ui_research.md` §3).
2. **Візуальний прогрес утечі.** Малювати тонку progress-arc/bar,
   що спадає разом із `escape_timer`; колір/форма + іконка, а не тільки текст (accessibility — `ui_best_practices_atof.md` §3.8).
3. **Не покладатися на '*'/'-'.** Поточний текстовий рядок (2811) важко читати «з погляду»; замінити на 5 чітких іконок-зірок (заповнені/порожні) на скляній плашці — консистентно зі стилем `draw_interaction_prompt`.
4. **Пульс/фlash при підвищенні.** Подія `raise_level` (1285) може запускати короткий (≤250 мс) спалах HUD — але з опцією «reduce motion» згідно з best practices.
5. **Поліція на радарі.** Підключити `npc_cars` з `is_police` (у `engine.py` логіка на 4540–4571) як blips у `draw_gta_minimap` (3.1.3) — тоді гравець бачить і причину розшуку, і шлях утечі.

---

## 4. Пріоритетний список (для АТОF)

| Пріоритет | Дія | Функція в engine.py |
|---|---|---|
| P0 | Стан розшуку (іконка + таймер утечі) замість текстових зірок | `WantedLevel` (1280), `draw_player_status` (2799), `draw_gta_minimap` (2872) |
| P0 | Одна підказка з пріоритетом + fade | `draw_interaction_prompt` (4319) |
| P0 | Перемикач «мінімальний HUD» / видимість цілі | `draw_gta_minimap` (2872) |
| P1 | Контекстна стрілка повороту замість постійного маркера | `draw_gta_minimap` (2872), `_draw_gps_marker` (2823) |
| P1 | Легенда та єдина символіка маркерів | `full_screen_map` (4128), `draw_gta_minimap` (2872) |
| P1 | Поліція-blips на радарі | `draw_gta_minimap` (2872) + `is_police` (4540+) |
| P2 | Компактний objective chip + toast про зміну цілі | UI-шар (new), `ui_story` hook (3082, 4264) |
| P2 | Візуальне підтвердження set/clear GPS | `full_screen_map` (4128) |

---

## 5. Джерела

- ResetEra — «Mafia III In-World "GPS" System is Amazing» (дві системи навігації; знаки-стрілки на перехрестях; цитати гравців): https://www.resetera.com/threads/mafia-iii-in-world-gps-system-is-amazing.231679/
- Wccftech — «Mafia Definitive Edition First Update Adds Custom HUD Options…» (перемикачі маркера цілі/ворогів/GPS, Minimal HUD, Noir Mode): https://wccftech.com/mafia-definitive-edition-first-update-adds-custom-hud-options-noir-mode-free-ride-content-and-more/
- 2K — офіційний список оновлення DE: https://mafia.2k.com/news/mafia-definitive-edition-update-new-features/
- GamingTrend — Mafia III 10th anniversary: «UI clarity and consistency across menus and HUD elements»: https://gamingtrend.com/news/mafia-iii-celebrates-its-10th-anniversary-with-current-gen-updates/
- Reddit r/Mafia3 — скарги на «CURRENT OBJECTIVE» box і бажання HUD-опцій: https://www.reddit.com/r/Mafia3/comments/56ayzf/can_we_have_hud_options_please/ · https://www.reddit.com/r/Mafia3/comments/56fcm9/this_game_desperately_needs_more_hud_options_here/
- Steam Discussions — надлишок HUD-маркерів у Mafia III: https://steamcommunity.com/app/360430/discussions/0/343788552534770798/
- NexusMods — «HUD Begone — Radar Removed at Mafia III» (залежність crowbar-мінігри від HUD): https://www.nexusmods.com/mafia3/mods/29
- Mafia Wiki (Fandom) — «Gameplay Mechanics in Mafia III» (normal/simulation driving mode): https://mafiagame.fandom.com/wiki/Gameplay_Mechanics_in_Mafia_III
- IGN — Mafia 3 Review (зауваження щодо інтерфейсу): https://www.ign.com/articles/2016/10/11/mafia-3-review
- Medium / Super Jump — «Mafia: Definitive Edition's Clever Navigation System»: https://medium.com/super-jump/mafia-definitive-editions-clever-navigation-system-772d9785f2ab
- Game UI Design (YouTube) — «Mafia's Environmental Navigation System»: https://www.youtube.com/watch?v=pNEJwVUfJIk
- Внутрішні документи ATOF: `docs/gta_ui_research.md`, `docs/ui_best_practices_atof.md`; код: `engine.py` (зазначені рядки).

---

*Звіт підготовлено в межах дослідження: код не змінено, комітів не створено.*

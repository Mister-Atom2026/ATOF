"""Tutorial state/progression helpers extracted from the engine runtime.

These helpers are intentionally data/logic-focused so the open-world loop can own
scene-specific side effects while tutorial definitions and completion rules live
in a dedicated module.
"""

from __future__ import annotations

from copy import deepcopy


def _english_steps():
    return [
        (
            "Movement & HUD",
            "Move around and learn the basics.",
            "WASD/arrows: move. Shift: sprint. Watch HUD: health, hunger, wanted, minimap, money (₭).",
        ),
        (
            "House & interaction",
            "Leave the house and explore the city.",
            "E: interact/enter/exit. Use E at the house door to go outside, then come back in.",
        ),
        (
            "Sleep, save & hunger",
            "Learn survival basics inside the house.",
            "E/T by the bed: sleep and save (+income days apply). Open fridge with E and eat to restore hunger.",
        ),
        (
            "Phone & map",
            "Use the phone and the full map.",
            "P/M: phone (apps/info). Tab: full map, K: quick locations, J: journal. On map: LMB set GPS, G gun shop, H home, RMB/Backspace/Delete clear.",
        ),
        (
            "Garage & your car",
            "Use the garage and your main vehicle.",
            "At garage E: open menu, take/store car, upgrades. Trunk (E at rear) opens on your main car and stolen cars you hijacked.",
        ),
        (
            "Driving controls",
            "Drive and test vehicle controls.",
            "F: enter/exit. W/S: accelerate/brake/reverse. A/D: steer. Space: handbrake. H: headlights. E: horn (while driving).",
        ),
        (
            "Steal & repair",
            "Steal an NPC car and learn repair.",
            "F near an NPC car to steal it. If damaged/broken, hold R to repair. Wanted level can rise for crimes.",
        ),
        (
            "Gun shop & ammo",
            "Visit the gun shop and buy ammo.",
            "Find gun shop (G on map). Enter with E, at counter E browse/buy ammo for owned firearms (₭).",
        ),
        (
            "Weapons & combat",
            "Use the weapon wheel, shoot and reload.",
            "MMB: weapon wheel (2 firearms, knife, unarmed). LMB: shoot/melee. R: reload. Knife works in close range.",
        ),
        (
            "Storage & trunk",
            "Store items in nightstand and car trunk.",
            "House nightstand (E): move weapons (7 slots). Car trunk (E at rear of main/stolen car): store/take items.",
        ),
        (
            "Economy & wanted",
            "Understand money and wanted mechanics.",
            "Currency: krotiks (₭). Shop gives +100 ₭ per in-game day. Crimes raise wanted level; police may chase.",
        ),
        (
            "Complete",
            "Tutorial complete — all core mechanics covered.",
            "You can keep exploring. Enter: finish tutorial, N: skip step, Tab: map, Esc: menu.",
        ),
    ]


TUTORIAL_STEPS_BY_LANGUAGE = {
    "English": _english_steps(),
    "Українська": [
        ("Рух і HUD", "Рухайтесь та ознайомтесь з інтерфейсом.", "WASD/стрілки: рух. Shift: біг. HUD: здоров’я, голод, розшук, мінімапа, гроші (₭)."),
        ("Дім і взаємодія", "Вийдіть із дому та поверніться.", "E: взаємодія/вхід/вихід. Натисніть E біля дверей, щоб вийти надвір і зайти назад."),
        ("Сон, збереження, голод", "Базові механіки виживання вдома.", "E/T біля ліжка: сон і збереження (+дохід за дні). Холодильник (E): їжа відновлює голод."),
        ("Телефон і карта", "Користуйтесь телефоном і мапою.", "P/M: телефон. Tab: повна мапа, K: швидкі точки, J: журнал. На мапі: ЛКМ — точка GPS, G — збройова, H — дім, ПКМ/Backspace/Delete — очистити."),
        ("Гараж і авто", "Користуйтесь гаражем і своїм авто.", "Біля гаража E: меню, взяти/поставити авто, апгрейди. Багажник (E ззаду) — у вашого основного та викрадених вами авто."),
        ("Керування авто", "Керуйте автомобілем.", "F: сісти/вийти. W/S: газ/гальмо/задній хід. A/D: кермо. Space: ручник. H: фари. E: сигнал (за кермом)."),
        ("Викрадення й ремонт", "Викрадіть авто та дізнайтесь про ремонт.", "F біля NPC-авто — викрасти. Якщо пошкоджене, тримайте R для ремонту. Злочини піднімають розшук."),
        ("Збройова й патрони", "Відвідайте збройову та купіть патрони.", "Знайдіть збройову (G на мапі). E — увійти, біля прилавку E — купити патрони для наявної зброї (₭)."),
        ("Зброя та бій", "Колесо зброї, стрільба, перезарядка.", "Середня кнопка миші: колесо (2 вогнепальні, ніж, без зброї). ЛКМ: вогонь/удар ножем. R: перезарядка."),
        ("Сховище й багажник", "Тумбочка вдома та багажник авто.", "Тумбочка (E): переносіть зброю (7 слотів). Багажник (E ззаду основного/викраденого авто): зберігайте речі."),
        ("Економіка й розшук", "Гроші та рівень розшуку.", "Валюта: кротики (₭). Магазин дає +100 ₭ за ігровий день. Злочини піднімають розшук — поліція може переслідувати."),
        ("Завершено", "Навчання завершено — основні механіки пройдено.", "Можете продовжити дослідження. Enter: завершити, N: пропустити крок, Tab: мапа, Esc: меню."),
    ],
    "Русский": [
        ("Движение и HUD", "Двигайтесь и изучите интерфейс.", "WASD/стрелки: движение. Shift: бег. HUD: здоровье, голод, розыск, миникарта, деньги (₭)."),
        ("Дом и взаимодействие", "Выйдите из дома и вернитесь.", "E: взаимодействие/вход/выход. Нажмите E у двери, чтобы выйти и зайти обратно."),
        ("Сон, сохранение, голод", "Основы выживания дома.", "E/T у кровати: сон и сохранение (+доход за дни). Холодильник (E): еда восстанавливает голод."),
        ("Телефон и карта", "Используйте телефон и карту.", "P/M: телефон. Tab: карта, K: быстрые точки, J: журнал. На карте: ЛКМ — точка GPS, G — оружейный, H — дом, ПКМ/Backspace/Delete — очистить."),
        ("Гараж и авто", "Используйте гараж и своё авто.", "У гаража E: меню, взять/поставить авто, улучшения. Багажник (E сзади) — у основного и угнанных вами авто."),
        ("Управление авто", "Управляйте автомобилем.", "F: сесть/выйти. W/S: газ/тормоз/задний ход. A/D: руль. Space: ручник. H: фары. E: сигнал (за рулём)."),
        ("Угон и ремонт", "Угоните авто и узнайте о ремонте.", "F рядом с NPC-авто — угнать. Если повреждено, удерживайте R для ремонта. Преступления повышают розыск."),
        ("Оружейный и патроны", "Посетите оружейный магазин и купите патроны.", "Найдите магазин (G на карте). E — войти, у прилавка E — купить патроны (₭)."),
        ("Оружие и бой", "Колесо оружия, стрельба, перезарядка.", "Средняя кнопка мыши: колесо. ЛКМ: огонь/удар ножом. R: перезарядка."),
        ("Хранилище и багажник", "Тумбочка дома и багажник авто.", "Тумбочка (E): оружие (7 слотов). Багажник (E сзади основного/угнанного авто): хранение вещей."),
        ("Экономика и розыск", "Деньги и уровень розыска.", "Валюта: кротики (₭). Магазин даёт +100 ₭ за игровой день. Преступления повышают розыск."),
        ("Готово", "Обучение завершено — основные механики пройдены.", "Можно продолжить исследование. Enter: завершить, N: пропустить шаг, Tab: карта, Esc: меню."),
    ],
    "Español": [
        ("Movimiento y HUD", "Muévete y conoce la interfaz.", "WASD/flechas: mover. Shift: correr. HUD: salud, hambre, búsqueda, minimapa, dinero (₭)."),
        ("Casa e interacción", "Sal de la casa y vuelve a entrar.", "E: interactuar/entrar/salir. Pulsa E en la puerta para salir y volver."),
        ("Dormir, guardar y hambre", "Supervivencia básica en casa.", "E/T junto a la cama: dormir y guardar. Nevera (E): comer restaura el hambre."),
        ("Teléfono y mapa", "Usa el teléfono y el mapa.", "P/M: teléfono. Tab: mapa, K: puntos rápidos, J: diario. En mapa: clic izq. GPS, G armería, H casa, clic der./Backspace/Borrar limpiar."),
        ("Garaje y tu coche", "Usa el garaje y tu vehículo principal.", "En el garaje E: menú, sacar/guardar, mejoras. Maletero (E atrás) en tu coche principal y robados."),
        ("Conducir", "Prueba los controles del vehículo.", "F: entrar/salir. W/S: acelerar/frenar/marcha atrás. A/D: girar. Espacio: freno de mano. H: faros. E: bocina (conduciendo)."),
        ("Robar y reparar", "Roba un coche y aprende a reparar.", "F cerca de un coche NPC para robarlo. Si está dañado, mantén R para reparar. Los delitos suben la búsqueda."),
        ("Armería y munición", "Visita la armería y compra munición.", "Encuentra la armería (G en mapa). E para entrar, en mostrador E para comprar munición (₭)."),
        ("Armas y combate", "Rueda de armas, disparar y recargar.", "Botón central: rueda. Clic izq.: disparar/cuchillo. R: recargar."),
        ("Almacenamiento y maletero", "Mesita y maletero del coche.", "Mesita (E): guarda armas (7). Maletero (E atrás del coche principal/robado): guardar/sacar."),
        ("Economía y búsqueda", "Dinero y nivel de búsqueda.", "Moneda: krotiks (₭). La tienda da +100 ₭ por día. Los delitos aumentan la búsqueda."),
        ("Listo", "Tutorial completado — mecánicas principales cubiertas.", "Puedes seguir explorando. Enter: terminar, N: saltar paso, Tab: mapa, Esc: menú."),
    ],
    "Deutsch": [
        ("Bewegung & HUD", "Bewege dich und lerne die Oberfläche kennen.", "WASD/Pfeile: bewegen. Shift: sprinten. HUD: Leben, Hunger, Fahndung, Minikarte, Geld (₭)."),
        ("Haus & Interaktion", "Verlasse das Haus und kehre zurück.", "E: interagieren/rein/raus. Drücke E an der Tür zum Verlassen und Eintreten."),
        ("Schlafen, Speichern, Hunger", "Überlebensgrundlagen im Haus.", "E/T am Bett: schlafen und speichern. Kühlschrank (E): Essen stellt Hunger wieder her."),
        ("Telefon & Karte", "Nutze Telefon und Karte.", "P/M: Telefon. Tab: Karte, K: Schnellpunkte, J: Journal. Auf Karte: Linksklick GPS, G Waffenladen, H Haus, Rechtsklick/Backspace/Entf löschen."),
        ("Garage & Auto", "Nutze Garage und dein Hauptfahrzeug.", "Bei Garage E: Menü, nehmen/parken, Upgrades. Kofferraum (E hinten) bei Haupt- und gestohlenen Autos."),
        ("Fahren", "Teste die Fahrzeugsteuerung.", "F: ein-/aussteigen. W/S: Gas/Bremse/Rückwärts. A/D: lenken. Leertaste: Handbremse. H: Scheinwerfer. E: Hupe (beim Fahren)."),
        ("Stehlen & Reparieren", "Stiehl ein Auto und lerne Reparatur.", "F nahe NPC-Auto zum Stehlen. Bei Schaden R halten zum Reparieren. Verbrechen erhöhen Fahndung."),
        ("Waffenladen & Munition", "Besuche den Waffenladen und kaufe Munition.", "Waffenladen finden (G auf Karte). E hinein, am Tresen E Munition kaufen (₭)."),
        ("Waffen & Kampf", "Waffenrad, Schießen, Nachladen.", "Mittlere Maustaste: Rad. Linksklick: schießen/Messer. R: nachladen."),
        ("Lager & Kofferraum", "Nachttisch und Kofferraum.", "Nachttisch (E): Waffen lagern (7). Kofferraum (E hinten am Haupt/gestohlenen Auto)."),
        ("Wirtschaft & Fahndung", "Geld und Fahndungsstufe.", "Währung: Krotiks (₭). Laden gibt +100 ₭ pro Spieltag. Verbrechen erhöhen Fahndung."),
        ("Fertig", "Tutorial abgeschlossen — Kernmechaniken erklärt.", "Weiter erkunden. Enter: beenden, N: Schritt überspringen, Tab: Karte, Esc: Menü."),
    ],
    "Français": [
        ("Déplacement & HUD", "Déplacez-vous et découvrez l'interface.", "WASD/flèches : bouger. Maj : sprinter. HUD : santé, faim, recherche, minicarte, argent (₭)."),
        ("Maison & interaction", "Sortez de la maison et revenez.", "E : interagir/entrer/sortir. Appuyez sur E à la porte pour sortir puis rentrer."),
        ("Dormir, sauvegarder, faim", "Bases de survie dans la maison.", "E/T près du lit : dormir et sauvegarder. Frigo (E) : manger restaure la faim."),
        ("Téléphone & carte", "Utilisez le téléphone et la carte.", "P/M : téléphone. Tab : carte, K : points rapides, J : journal. Sur la carte : clic gauche GPS, G armurerie, H maison, clic droit/Retour/Suppr effacer."),
        ("Garage & voiture", "Utilisez le garage et votre voiture principale.", "Au garage E : menu, prendre/ranger, améliorations. Coffre (E arrière) sur voiture principale et volée."),
        ("Conduite", "Testez les commandes du véhicule.", "F : entrer/sortir. W/S : accélérer/freiner/marche arrière. A/D : tourner. Espace : frein à main. H : phares. E : klaxon (en conduisant)."),
        ("Vol & réparation", "Volez une voiture et apprenez la réparation.", "F près d'une voiture PNJ pour la voler. Si endommagée, maintenir R pour réparer. Les crimes augmentent la recherche."),
        ("Armurerie & munitions", "Visitez l'armurerie et achetez des munitions.", "Trouvez l'armurerie (G sur carte). E pour entrer, au comptoir E pour acheter des munitions (₭)."),
        ("Armes & combat", "Roue des armes, tirer, recharger.", "Bouton central : roue. Clic gauche : tirer/couteau. R : recharger."),
        ("Rangement & coffre", "Table de chevet et coffre.", "Table de chevet (E) : ranger armes (7). Coffre (E arrière voiture principale/volée)."),
        ("Économie & recherche", "Argent et niveau de recherche.", "Monnaie : krotiks (₭). Le magasin donne +100 ₭ par jour. Les crimes augmentent la recherche."),
        ("Terminé", "Tutoriel terminé — mécaniques principales couvertes.", "Vous pouvez continuer. Entrée : terminer, N : passer, Tab : carte, Échap : menu."),
    ],
}


def get_tutorial_steps(language: str):
    steps = TUTORIAL_STEPS_BY_LANGUAGE.get(language)
    if steps is None:
        steps = TUTORIAL_STEPS_BY_LANGUAGE["English"]
    return deepcopy(steps)


def create_tutorial_state(language: str):
    return {
        "active": True,
        "steps": get_tutorial_steps(language),
        "index": 0,
        "done_timer": 0.0,
        "step_done_flash": 0.0,
        "moved": 0.0,
        "left_house": False,
        "returned_house": False,
        "slept_or_saved": False,
        "fridge_used": False,
        "phone_opened": False,
        "map_opened": False,
        "map_marker_set": False,
        "entered_car": False,
        "drove": False,
        "exited_car": False,
        "horn_used": False,
        "stole_car": False,
        "repaired_car": False,
        "visited_gunshop": False,
        "bought_ammo": False,
        "opened_wheel": False,
        "fired": False,
        "reloaded": False,
        "nightstand_used": False,
        "trunk_used": False,
        "garage_used": False,
        "upgraded_car": False,
        "visited_target": False,
        "last_pos": None,
        "completed": False,
        "tab_held": False,
        "initialized_step": -1,
        "was_in_car": False,
        "prev_wheel_open": False,
        "prev_ammo": 0,
        "prev_reserve": 0,
        "prev_money": 0,
        "prev_game_state": "HOUSE",
    }


def tutorial_step_completed(tutorial) -> bool:
    if not tutorial:
        return True
    i = tutorial.get("index", 0)
    if i == 0:
        return bool(tutorial.get("moved", 0) > 220)
    if i == 1:
        return bool(tutorial.get("left_house")) and bool(tutorial.get("returned_house"))
    if i == 2:
        return bool(tutorial.get("fridge_used")) or bool(tutorial.get("slept_or_saved"))
    if i == 3:
        return bool(tutorial.get("phone_opened")) and bool(tutorial.get("map_opened"))
    if i == 4:
        return bool(tutorial.get("garage_used")) or bool(tutorial.get("trunk_used")) or bool(tutorial.get("entered_car"))
    if i == 5:
        return bool(tutorial.get("drove")) and bool(tutorial.get("entered_car"))
    if i == 6:
        return bool(tutorial.get("stole_car")) or bool(tutorial.get("repaired_car")) or bool(tutorial.get("horn_used"))
    if i == 7:
        return bool(tutorial.get("visited_gunshop")) or bool(tutorial.get("bought_ammo"))
    if i == 8:
        return bool(tutorial.get("opened_wheel")) and (bool(tutorial.get("fired")) or bool(tutorial.get("reloaded")))
    if i == 9:
        return bool(tutorial.get("nightstand_used")) and bool(tutorial.get("trunk_used"))
    if i == 10:
        # informational but requires some world interaction awareness
        return bool(tutorial.get("map_opened")) or bool(tutorial.get("drove")) or bool(tutorial.get("visited_gunshop"))
    if i == 11:
        return bool(tutorial.get("completed", False))
    return False

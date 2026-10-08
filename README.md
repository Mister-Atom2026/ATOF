# ATOF
Game About Mister Atom

## Version 0.7.0 RC 1 — "Story Foundations"

- Fixed type hints in traffic.py (get_traffic_car_image and get_police_car_image now return Optional[pygame.Surface]).
- Refactored player status UI: health bar now appears above the speedometer position, ammo and wanted status moved to bottom-right corner.
- Updated version to 0.7.0-rc.1.

## Version 0.7.0 Beta 2 — "Story Foundations"

- Increased traffic count from 11 to 18 vehicles.
- Moved HOUSE_SLEEP_SPOT and HOUSE_SLEEP_RADIUS from engine.py to constants.py.
- Refactored menu music loading into load_and_play_menu_music() function.
- Updated version to 0.7.0-beta.2.

## Version 0.7.0 Alpha 2 — “Story Foundations”

- Splits **Play** into **Continue Story** and **Choose Chapter**.
- Adds an engine-owned chapter registry and a chapter picker that shows only each available chapter's number and title.
- Starting a selected chapter begins a fresh run; continuing loads the saved chapter, with older saves defaulting to Chapter 1.

## Version 0.7.0 Beta 1 — “Story Foundations”

- Adds car theft with fleeing drivers, armed police response, a wanted level, and honor/respect consequences.
- Adds player health, ammo, and a mouse-wheel weapon selector for unarmed, pistol, knife, and shotgun.
- Moves weapon inventory, firing, projectile collision, health, wanted status, and reputation primitives into the engine.

## Version 0.7.0 Alpha 1 — “Story Foundations”

- Adds engine-owned frame timing, camera transforms, scene lifecycle, and ordered render layers for reusable chapter runtime.
- Centralizes shared image caching, chapter resource preparation, navigation, and house-player behavior behind the engine API.
- Keeps chapter-one world content and existing save-state identifiers intact while preparing the runtime for future story chapters.

## Version 0.6.2 Release — “Driver Inferno”

- Removes automatic night headlights; headlights now turn on only when manually toggled with **H** while driving.

## Version 0.6.1 Release — “Driver Inferno”

- Replaces normal-based, mass-weighted collision response with a simple speed-scaled bounce.
- Makes collision damage increase with impact speed and prevents rebound from pushing the car into the obstacle.
- Renders two distinct headlight beams after the night tint and clips each beam at collision-mask obstacles.

## Version 0.6.0 RC 1 — “Driver Inferno”

- Restarts the car horn on every press and briefly yields nearby traffic without changing its routes.
- Fixes manual headlight toggling and clips headlight beams at collision-mask obstacles.
- Consolidates chapter resource loading and shared sleep-spot handling in the engine.
- Removes the obsolete root-level `Додай` file.

## Version 0.6.0 Beta 2 — “Driver Inferno”

- Shows control keys in their English/US-layout form in every supported language.
- Fixes PyCharm type warnings in vehicle collision and rebound calculations.

## Version 0.6.0 Beta 1 — “Driver Inferno”

- Cycles the in-car radio through Midnight FM, Freeway Radio, and radio off using **,** (previous) and **.** (next).
- Keeps **V** for pausing/resuming playback; all six supported languages show the same English key labels.

## Version 0.6.0 Alpha 2 — “Driver Inferno”

- Expands the in-car radio to two named stations with four downloaded songs across ambient and road-trip playlists.
- Uses **V** to pause/resume at the same point and **C** to switch stations; each track keeps its own playback position, and playlists advance automatically.
- Translates radio status and controls into all six supported languages.

## Version 0.6.0 Alpha 1 — “Driver Inferno”

- Adds an in-car radio toggle on V, with a bundled looping CC0 track and localized on-screen status in all six supported languages.
- Improves crash response: impact damage and rebound now depend on relative closing speed, contact direction, and vehicle mass.
- Gives existing vehicles distinct handling: the player Tornado is faster and more slippery, regular traffic is slower and heavier, and police cars are faster pursuit vehicles.

## Version 0.5.0 Release — “(NOT) Sad City”

- Keeps the GPS destination marker visible on the minimap edge when the destination is outside the radar view.
- Fixes false vehicle collisions with road markings and accounts for the rotated shapes of cars.
- Moves the indoor spawn and sleep/save point to the bed at house coordinates (147, 156).
- Translates the in-game Video settings tab in all six supported languages.
- Adds the horn on E and manual headlights on H; headlights also turn on automatically at night, and brake lights brighten while braking.
- Shows the current FPS in the F3 debug overlay.
- Includes the Alpha 2 driving, terrain, sleep-save, map, lighting, and personal-record features.

## Previous version: 0.5.0 Beta 2 — “(NOT) Sad City”

- Beta 2 added the minimap, collision, bed-save, in-game Video translation, vehicle lights and horn, and debug FPS fixes.

## Previous version: 0.5.0 Beta 1 — “(NOT) Sad City”

- Restricts sleeping and saving to the house; the sleep prompt is localized in every supported language.
- Saves and restores the indoor player position when continuing from a sleep save.
- Removes the sleep interaction from the city and keeps house entry/exit controls separate from sleeping.
- Keeps gameplay and interface prompts translated into English, Ukrainian, Russian, Spanish, German, and French.

## Previous version: 0.5.0 Alpha 2 — “(NOT) Sad City”

- Adjusts vehicle grip for asphalt, dirt, and grass; wet patches on the map reduce grip and acceleration.
- Adds a spacebar handbrake for tight turns and longer drifts.
- Adds a translated sleep-and-save interaction; sleeping fades the screen, advances the clock by nine in-game hours, and saves the player's and car's state.
- Resumes from the sleep save and smoothly transitions lighting through dawn and dusk.
- Opens the full map centered on the player's current position.
- Tracks personal records for top speed, longest drift, and longest distance without a crash.
- Keeps the staged acceleration and high-speed turn speed loss from Alpha 1.

## Previous version: 0.5.0 Alpha 1

- Strengthens drifting progressively as speed rises.
- Reduces speed during turns only from 100 km/h.
- Tunes acceleration to reach 70 km/h quickly, 90 km/h more gradually, and 120 km/h more slowly.
- Makes the GPS destination marker on the radar larger and easier to distinguish with a dark outline, orange body, and white center.
- Displays GPS distance in meters and kilometers, with map prompts translated in all supported languages.

## Previous version: 0.4.2 — “Taxi Ride”

- Adds an English release title, updated release metadata, and the full 0.4.2 changelog for the public GitHub release.
- Refines the GPS marker: the map keeps only the destination point, removes the distance line, and uses a bright orange point that is easier to see.
- Adds set/clear marker sounds for the destination point and keeps marker actions consistent in both the minimap and the full-screen map.
- Boosts the drift feel on turns: it now starts at 30 km/h instead of 40, produces a stronger slide, and reduces speed during cornering.
- Keeps the settings and translations fully aligned across the supported languages and fixes the remaining UI/marker visual issues in the map screens.

## Previous version: 0.4.1 Release Candidate 1

- Adds a GPS destination marker on the Tab map, live straight-line distance, and controls to move or clear the marker.
- Removes the unused NEAT training script, model, and runtime loader; traffic now follows its built-in routes.
- Fixes PyCharm type warnings in traffic and settings normalization and marks intentional repeated menu patterns.
- Beta 1 fixed crash sounds for every collision and oversized rotated 2107 collision boxes.
- Alpha 2 added high-speed drifting when turning above 40 km/h, with visible tire marks.
- Alpha 1 added a **Settings** app to the in-game phone, with five saved phone colors, and the **Nayra Studio** settings credit.

## Previous tagged version: 0.0.4 — “Talking Beaver!”

This is a major update for ATOF.

- Adds Spanish, German, and French translations for menus, gameplay, phone, settings, and statistics.
- Adds last-session statistics for balance, time, treasures found, money earned, and money spent; the main menu opens them from **Additional Content**.
- Adds a resizable window with selectable display resolutions and a configurable FPS limit in the **Video** settings tab. The title-bar square maximizes the window; the FPS limit does not change the monitor's refresh rate.
- Saves video settings in `config.json` and displays the game version in the window title.

## Previous version: 0.0.3

- Adds separate volume controls for music, NPCs, crashes, buttons, and footsteps, including in the pause menu.
- Saves audio, language, and key settings in `config.json`, validates saved values, and reads the previous music-volume setting.
- Fixes player collision checks at map boundaries and makes game assets load from the project directory.
- Adds translated audio-setting labels and clearer volume controls in English, Ukrainian, and Russian.

## Previous version: 0.0.2

- Adds roaming police traffic with collision-aware patrol and pursuit behavior.
- Loads the supplied traffic brain into traffic and police at runtime; police use it for steering while keeping their own patrol and pursuit behavior. The game does not run training.
- Uses physical letter-key positions for movement and in-game shortcuts on any keyboard layout; arrow keys remain supported.
- Includes English, Ukrainian, and Russian text for the menus, repair prompt, exit confirmation, and phone banking screen.
- Plays a soft sound when navigating menus and a click sound when selecting options.

## Languages

The game includes English, Ukrainian, Russian, Spanish, German, and French text.
The main menu's **Additional Content** page shows statistics from the last session.

## Menu sound credits

- Hover sound: [Minimalist Button Hover Sound Effect by Lesiakower](https://pixabay.com/sound-effects/film-special-effects-minimalist-button-hover-sound-effect-399749/)
- Click sound: [UI Click Soft by SoundShelfStudio](https://pixabay.com/sound-effects/technology-ui-click-soft-512213/)

Both effects were shortened/volume-adjusted and converted for in-game use under the [Pixabay Content License](https://pixabay.com/service/license-summary/).

## Radio music credit

- “Crystal Cave (song18)” by [Cynic Project](https://cynicmusic.com/), downloaded from [OpenGameArt.org](https://opengameart.org/content/crystal-cave-song18). The track is marked [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) by its uploader. It is looped in-game; credit is included in appreciation of the creator.
- “Observing the Star” by yd, downloaded from [OpenGameArt.org](https://opengameart.org/content/another-space-background-track), marked CC0 1.0.
- “Freeway Fumes” and “Detour” by [Zane Little Music](https://zanelittle.com/), downloaded from [OpenGameArt.org](https://opengameart.org/content/freeway-fumes) and [OpenGameArt.org](https://opengameart.org/content/detour), both marked CC0 1.0.

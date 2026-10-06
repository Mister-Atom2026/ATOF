# ATOF
Game About Mister Atom

## Version 0.5.0 Alpha 2 — “(NOT) Sad City”

- Adjusts vehicle grip for asphalt, dirt, and grass; wet patches on the map reduce grip and acceleration.
- Adds a spacebar handbrake for tight turns and longer drifts.
- Adds a translated sleep-and-save interaction near the starting point; sleeping fades the screen, advances the clock by nine in-game hours, and saves the player's and car's state.
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

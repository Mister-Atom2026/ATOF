# ATOF
Game About Mister Atom

## Version 0.4.1 Release Candidate 1 — In development

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

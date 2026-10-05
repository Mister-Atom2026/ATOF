# ATOF
Game About Mister Atom

## Version 0.0.3

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

## Menu sound credits

- Hover sound: [Minimalist Button Hover Sound Effect by Lesiakower](https://pixabay.com/sound-effects/film-special-effects-minimalist-button-hover-sound-effect-399749/)
- Click sound: [UI Click Soft by SoundShelfStudio](https://pixabay.com/sound-effects/technology-ui-click-soft-512213/)

Both effects were shortened/volume-adjusted and converted for in-game use under the [Pixabay Content License](https://pixabay.com/service/license-summary/).

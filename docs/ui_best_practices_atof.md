# ATOF — Modern 2D Game UI Best Practices & Recommendations

> Complements: [`docs/alpha4_ui_research.md`](alpha4_ui_research.md) (GTA/modern references, Inter font, Alpha 4 plan)  
> Target: **Pygame, 2D, performance-conscious, cross-platform**  
> Scope: HUD readability, weapon/quick-select wheel, objective/mission tracking, map markers/navigation, prompts, menus, notifications, accessibility, and UI "feel" (animation/feedback/glassmorphism in 2D)

---

## 1. Executive summary

ATOF already has strong foundations for a modern 2D UI: contextual HUD, minimap/radar, weapon wheel, interaction prompts, phone/map, storage menus, settings, and an integrated tutorial. The next gains come less from adding more UI and more from **clarity, consistency, timing, and feedback**:

- **Show less, mean more:** keep only urgent/frequent state persistent; reveal everything else contextually.
- **One visual system:** unify panels, typography, iconography, color semantics, spacing, motion, and prompt language across HUD, menus, map, and phone.
- **Readability under stress:** prioritize contrast, hierarchy, and fixed placement over decoration.
- **Feel through response, not noise:** fast input feedback, short eased animations, and subtle state transitions outperform heavy effects.
- **Cheap "premium" look:** fake glass/blur with layered translucent surfaces and cached assets; reserve real blur and per-frame effects for rare/static cases.

This document turns modern patterns (GTA V/VI-style minimalism, Hades/Dead Cells readability, Destiny/Forza/Cyberpunk presentation cues, Dead Space-style diegetic inspiration) into **practical, prioritized Pygame guidance** for ATOF.

---

## 2. ATOF context and constraints

**Current signals from the repo (as of Alpha 4 + WIP notes):**
- Open-world 2D Pygame game (`engine.py`-centric runtime), fixed base resolution logic, Linux/macOS/Windows target.
- Existing systems: `draw_gta_minimap` (glass radar + HP/hunger arcs), `WeaponWheel` (MMB radial, `atan2` sectors), contextual `draw_interaction_prompt`, phone/map with GPS markers (`G` gun shop, `H` home), garage/trunk/nightstand/gun-shop menus, tutorial, settings/controls rebinding, 6-language localization (EN/UA/RU/ES/DE/FR).
- Currency/economy shown as **₭ (KRO)**; save/state and tutorial hooks already track many player actions.
- Bundled **Inter** font (OFL) is the right direction for consistent cross-platform rendering.

**Design constraints:**
- **Performance:** avoid per-frame expensive blits/effects on large surfaces; cache fonts, text, panels, gradients, masks, and static HUD chrome.
- **Legibility:** UI must read over bright/dark/busy map scenes and at distance/scaled window sizes.
- **Localization:** strings vary in length (DE/FR/RU/UA often longer); layouts must tolerate expansion.
- **Controller/keyboard parity later:** patterns should not depend solely on mouse hover precision.
- **Accessibility:** color must not be the only signal; provide scalable/readable text and motion/feedback controls.

---

## 3. Patterns, examples, and why they work

### 3.1 HUD readability

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Glance-budget HUD** (few persistent elements, fixed positions) | *Dead Cells*, *Hades*, GTA V contextual HUD | Players read HUD in split seconds during motion/combat; fewer elements = faster parsing and less occlusion | Keep radar + vital state + critical combat context persistent; move non-urgent info to contextual/phone |
| **Contextual reveal** (show ammo/interaction/threat only when relevant) | *Red Dead Redemption 2*, *Dead Space*, modern GTA behavior | Reduces clutter; appearance itself communicates relevance | Show ammo/reload prompts on weapon draw/fire/reload/low ammo; hide when unarmed/idle as appropriate |
| **Strong hierarchy & contrast** (value > label, critical > secondary) | *Hades* boon/sidebar discipline, *Forza Horizon* typography | Pre-attentive reading: shape/size/contrast register before text | Emphasize HP danger, low hunger, wanted/threat, and active objective cues over decorative labels |
| **Backplates/outlined text** over variable backgrounds | Common AAA/indie practice; Game UI readability guidance | Guarantees contrast on any map/background | Use subtle dark glass backplates or text shadow/outline for all floating HUD text |
| **State change > static numbers** (bars, deltas, pulses, warning states) | *Hades* clear combat feedback, fighting games/ARPGs | Motion/color+shape changes are noticed faster than rereading values | Smooth HP/hunger interpolation, brief damage/heal flash, low-state pulse (subtle, rate-limited) |

**Practical rules for ATOF:** critical info near established attention zones (radar/vitals cluster and combat context), consistent anchors, no text baked into noisy backgrounds without a plate, and "danger" communicated by **shape/icon/animation + color**.

### 3.2 Weapon / quick-select wheel

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Radial selection via direction (`atan2`) + deadzone** | GTA weapon wheel, console radial menus, many action games | Directional flick/muscle memory is faster than list scanning; low cognitive load | ATOF already uses `atan2` + `wheel_slots` + MMB — preserve logic, refine feel/clarity |
| **Time dilation or strong focus dim while open** | GTA/action RPG radials | Buys decision time and isolates menu from world noise | Optional slight world dim/overlay; consider gentle slowdown later if gameplay allows (not required now) |
| **Active wedge + center detail panel** | GTA V, *Destiny*-style clarity | Confirms selection and shows consequences (weapon/ammo/type) without reading all wedges | Center: icon/name, ammo mag/reserve, slot/type; active wedge clearly highlighted |
| **Bounded item count (roughly 4–8 fast picks)** | Radial UX guidance | Too many wedges hurts speed/accuracy | Current 4-slot structure is ideal; future expansion should use paging/categories, not crowding |
| **Immediate, unambiguous commit/cancel feedback** | Modern action UIs | Prevents mis-selection frustration | Sound/visual tick on hover-change (rate-limited), clear close/confirm behavior, highlight snap |

**Why this fits Pygame:** wheel geometry, wedge highlight, and labels are cheap to draw each open-frame; pre-render icons/labels and cache the dim/backdrop surface.

### 3.3 Objective / mission tracking

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Single active objective + optional substeps** | GTA, Ubisoft-style trackers, *Hades* goal clarity | Limits working memory; players always know "what now" | **Later (story/quest UI):** compact tracker (1 primary, 1–2 substeps max) |
| **Diegetic/world reinforcement** (marker + distance + landmark) | Open-world games, waypoint/nav systems | Connects abstract goal to world space | Reuse/extend GPS marker + minimap edge indicator + contextual distance text |
| **Progress feedback on completion/change** | RPG/action quest UX | Confirms advancement and rewards attention | **Later:** short toast/check animation, objective text strike/advance transition |
| **Journal/log is secondary; tracker is immediate** | Most modern quest systems | Avoids forcing menu dives mid-play | **Later:** phone/log for full quest list, HUD for current step only |

### 3.4 Map markers / navigation

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Clear marker taxonomy (player, objective, POI, custom)** | GTA, open-world standards | Different shapes/icons beat color-only distinctions and speed scanning | Distinguish home, gun shop, garage, custom GPS, quest markers with unique silhouettes + legend in map |
| **On-edge/off-screen indicator for active destination** | GTA/RPG minimaps | Preserves spatial awareness when target is outside radar | ATOF already benefits here conceptually; ensure active GPS destination clamps to radar edge with direction cue |
| **Minimal minimap, richer full map** | *Dead Cells* (map on demand), open-world games | Right info density for context | Keep radar uncluttered (threats/destination/POIs only); full map gets filters/shortcuts/legend |
| **Fast set/clear affordances** | ATOF `G`/`H`/click shortcuts are a good start | Low friction navigation encourages exploration/use | Keep shortcuts visible in map hint bar; add consistent audio/visual confirmation on set/clear |

### 3.5 Prompts (interaction / controls)

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Verb-first contextual prompts: `[KEY] Action`** | Most modern games, platform UX conventions | Recognition over recall; minimal reading | Standardize format everywhere (enter, talk, loot, trunk, buy, sleep, repair) |
| **Proximity + priority + fade** | Clean immersive UIs | Prevents prompt spam and flicker | Show nearest/highest-priority interactable; smooth fade in/out (already aligned with WIP polish) |
| **Input-glyph correctness** | Cross-platform titles, rebinding-aware UIs | Avoids wrong/misleading controls | Drive prompt labels from current bindings/settings; reflect rebound keys immediately |
| **Stateful prompt variants** (available/blocked/cost) | RPG/shop interactions | Communicates affordance before failure | e.g. "Not enough ₭", "Inventory full", "Need owned firearm" with muted/blocked styling, not just color |

### 3.6 Menus

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Calm layout, strong focus state, shallow depth** | *Forza Horizon* flow, Nintendo/modern settings UX | Reduces navigation errors and cognitive load | Consistent focus ring/highlight, clear selected row/card, predictable back/cancel |
| **Card/list hybrid for inventories/storage** | RPG/storage UIs, modern inventory screens | Icons speed recognition; lists aid comparison | Trunk/nightstand/gun shop: icon + name + qty/ammo/price + clear transfer affordance |
| **Immediate, reversible where safe** | Good settings/inventory practice | Builds trust and speed | Preview/apply patterns, confirmations for destructive actions, clear capacity/limits feedback |
| **Shared component language** (panel, header, tabs, rows, buttons) | Destiny/Cyberpunk-styled cohesion | Consistency lowers learning cost | Reuse one "glass panel" primitive and spacing/type scale across all menus/phone panels |

### 3.7 Notifications / toasts

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Priority tiers (critical/modal > important toast > ambient hint)** | HUD design best practices | Prevents low-value messages from hiding urgent info | e.g. damage/wanted/mission-critical vs pickup/income/save confirmation vs subtle hints |
| **Short-lived, stack-limited, non-overlapping core HUD** | *Hades* restraint, modern action HUDs | Avoids "Christmas tree" and missed events | Cap concurrent toasts, queue/coalesce repeats (e.g. ammo pickups), auto-dismiss 2–4s |
| **Readable placement and motion** | Toast/feed UX | Motion draws eye; bad placement obscures gameplay | Anchor away from minimap center/reticle-critical area; slide+fade 120–220ms, respect reduced motion |
| **Icon + short text (+ number)** | Loot/XP/save feedback patterns | Faster than sentences | "₭ +100 (daily income)", "Saved", "Magazine full", "Low fuel/hunger" style brevity |

### 3.8 Accessibility

| Pattern | Good examples | Why it works | ATOF fit |
|---|---|---|---|
| **Text scale, HUD scale, contrast-safe defaults** | *Dead Cells* options, platform accessibility expectations | Supports distance/vision/handheld variance | Add UI/HUD/text scale options; maintain 4.5:1 target for body text where feasible |
| **Redundant coding (not color-only)** | WCAG/game accessibility guidance | Essential for color vision differences and busy scenes | Pair HP/hunger/wanted/blocked states with icons, labels, fill shape, pattern, or animation |
| **Reduce motion / shake / flash controls** | *Dead Cells*, *Hades*-adjacent expectations, modern titles | Comfort and photosensitivity safety | Toggles for HUD pulses, screen shake, camera/UI motion intensity, flashing effects |
| **Rebinding + clear input prompts + hold/toggle options** | Cross-platform standards | Accommodates motor/access needs and preferences | ATOF already has rebinding/conflict handling — extend to prompt display and interaction modes |
| **Timing tolerance** | Accessible design guidance | Not everyone reads/reacts at same speed | Avoid critical info only in fast-disappearing toasts; keep important prompts persistent while valid |

### 3.9 "Feel": animation, feedback, glassmorphism in 2D (Pygame)

| Technique | Good examples / inspiration | Why it works | Performance-conscious Pygame approach |
|---|---|---|---|
| **Fast feedback (input acknowledgement)** | Core game-feel principle (~instant response) | Removes uncertainty | State change on same frame/event: highlight, press tint, sound hook, cursor/prompt change |
| **Short eased transitions (120–300ms)** | *Forza Horizon* smoothness, modern UI motion | Communicates continuity without sluggishness | Use `dt` + easing (ease-out for enter, ease-in for exit); animate offsets/alpha/scale factors, not expensive filters |
| **Micro-juice with restraint** (pulse on low HP, tick on wheel move, bar trail) | *Hades* combat readability, ARPG feedback | Adds salience and polish | Cap frequency/amplitude; disable or soften under "reduced motion" |
| **"Fake glass" (frosted look without real-time blur)** | Common 2D trick, Cyberpunk/Destiny-inspired translucency | Premium depth cue at low cost | `SRCALPHA` panel + dark tint + 1px light rim + soft highlight gradient/noise texture + optional cached blurred backdrop snapshot when menu opens (not every frame) |
| **Layered glow/highlight** | Sci-fi/neon refs (*Cyberpunk 2077*, *Destiny*) used sparingly | Focus and atmosphere | 1–2 pre-rendered glow sprites or expanded alpha rects for active elements only; avoid full-screen shaders unless already in pipeline |

---

## 4. Cross-cutting design system recommendations for ATOF

1. **Tokens (single source of truth):** define palette (base/surface/text/accent/semantic), radii, border widths, spacing scale, shadow/glow strengths, and motion durations/easings in code/constants.
2. **Typography scale:** use bundled Inter weights consistently (e.g. Regular body, Medium labels, SemiBold values, Bold headers/prompts) with fixed sizes per role; pre-render/cache static labels.
3. **Icon/marker grammar:** consistent stroke/fill weight and silhouettes for weapon types, POIs, states, and controls; never rely on hue alone.
4. **Panel primitive:** one reusable glass-panel renderer (background, blur-fake layers, rim, optional corner accents) used by radar/prompt/menu/phone where appropriate.
5. **Localization-safe layout:** auto-width/padding for prompts and menu rows, max widths + ellipsis/wrap rules for long strings, test DE/FR/RU/UA.
6. **Audio-visual pairing:** pair key UI events (prompt appear, confirm, error, wheel tick, map marker set, notification) with subtle sounds at consistent volumes.

---

## 5. Prioritized roadmap (Pygame, 2D)

### Adopt now (high value, low/medium cost, fits Alpha 4/WIP direction)

| Priority | Recommendation | Rationale | Effort | Notes |
|---|---|---|---|---|
| **P0** | **Unify UI primitives & tokens** (colors, spacing, type roles, panel/prompt styles) | Biggest consistency/readability win across HUD, prompts, menus | M | Build on existing Inter + glass radar/prompt work |
| **P0** | **HUD hierarchy pass**: fixed anchors, backplates for text, emphasize critical states (low HP/hunger, wanted/threat) with shape+animation+color | Improves glanceability under combat/motion | S–M | Keep current info set; mostly presentation/state rules |
| **P0** | **Prompt system polish**: standardized `[Binding] Verb` from live keybinds, priority/nearest selection, fade in/out, blocked-state variants | Clear affordances; already partially implemented | S–M | Must handle rebinding and localization length |
| **P1** | **Weapon wheel feel/clarity pass** (keep logic): stronger active wedge, center ammo/type info, hover tick (rate-limited), dim backdrop, cached assets | Fast, high-impact UX improvement | S | No algorithm change (`atan2`, slots, MMB) |
| **P1** | **Notification/toast framework (lightweight)**: queue, priority, stack cap, coalesce, timed fade; icon+short text | Needed for save/income/pickup/warning feedback without clutter | M | Integrate with existing events (save, +₭/day, low ammo, etc.) |
| **P1** | **Performance hygiene**: cache rendered text/surfaces, precompute gradients/panels, avoid per-frame allocations/real blur in gameplay HUD | Protects FPS as UI grows | S–M | Profile hotspots in `engine.py` render paths |
| **P1** | **Basic accessibility toggles**: reduce HUD motion/pulses, subtitle/prompt readability options hooks, color-safe state cues audit | Low-cost inclusivity and comfort | S–M | Align with existing settings structure |

### Adopt next (medium effort, strong UX payoff)

| Priority | Recommendation | Rationale | Effort | Notes |
|---|---|---|---|---|
| **P2** | **Map/navigation clarity upgrade**: marker taxonomy/legend, active-destination edge indicator, clearer POI icons, consistent set/clear feedback | Makes open-world navigation effortless | M | Extend current `G`/`H` + custom marker flow |
| **P2** | **Menu convergence** (garage, trunk, nightstand, gun shop, phone/settings): shared components, focus states, clearer transfer/buy feedback, capacity/cost blockers | Reduces learning friction and visual drift | M | Preserve game logic; refactor presentation layer incrementally |
| **P2** | **HUD/map scale & layout options** (small/medium/large, safe margins) | Readability across displays/window sizes | M | Useful before deeper accessibility pass |
| **P2** | **Richer combat/readability feedback**: hit/damage direction cues, low-ammo/reload prominence, wanted-state clarity | Improves moment-to-moment understanding | M | Keep subtle and contextual |

### Adopt later (higher complexity / depends on systems)

| Priority | Recommendation | Rationale | Effort | Notes |
|---|---|---|---|---|
| **P3** | **Story/quest UI (objective tracker + journal/log in phone)** | Becomes valuable once authored missions/quests expand (`open_world.py` story/side content) | M–L | HUD: 1 active objective + distance/state; Phone: full log, categories, tracked quest selection |
| **P3** | **World/diegetic hints where cheap** (in-world markers, contextual icons over interactables/NPCs with distance culling) | Immersion and spatial clarity | M | Must not hurt performance/readability; keep optional/fallback HUD prompts |
| **P3** | **Advanced accessibility**: full text scaling, high-contrast theme, color remapping presets, hold/toggle alternatives, aim/interaction assists as needed | Broader accessibility coverage | M–L | Build on P1 toggles/settings architecture |
| **P3** | **Shader/post-process polish (optional)**: lightweight vignette/noise/bloom in menus or special states via existing/optional GPU path | Extra atmosphere | M–L | Only if performance budget allows; keep fallback to cached 2D "fake" effects |
| **P3** | **Controller/gamepad-first navigation & glyph set** | Important for broader input support, but larger UX/test pass | M–L | Requires focus graph, virtual cursor/radial behavior tuning, glyph assets |

---

## 6. Pygame implementation notes (performance-conscious)

- **Surface caching:** pre-render static HUD chrome, panel backgrounds, icons, and frequently used text (`font.render(..., True)` once, reuse). Re-render only on value/text change.
- **Dirty/static layers:** if parts of HUD are stable, draw them to cached surfaces and composite; avoid rebuilding complex alpha stacks every frame.
- **"Glass" cheaply:** compose with semi-transparent fills, gradients, 1px rims, and highlight sprites. If a blur is desired, capture/downscale background **once on open** for menus/overlays rather than per-frame.
- **Alpha discipline:** minimize large per-frame `SRCALPHA` overdraw; prefer opaque/blitted cached composites where possible.
- **Animation:** time-based (`dt`) interpolation/easing for bars, fades, slides; clamp and snap small deltas to avoid jitter.
- **Event/rate limiting:** wheel hover ticks, notifications, and pulses should be throttled/debounced; coalesce repeated events.
- **Culling:** skip drawing off-screen markers/effects; for radar/minimap, render to a dedicated surface/mask and blit once.
- **Text/locale:** avoid dynamic layout thrash each frame; measure wrapped/localized strings on change, not continuously.
- **Profiling mindset:** when adding polish, measure frame time impact of new alpha blends, blurs, and text renders on worst-case busy scenes.

---

## 7. Suggested success metrics (playtest/QA)

- **Readability:** player can report HP/hunger/active prompt/destination at a glance without stopping.
- **Navigation:** time-to-set-and-follow destination (map/radar) is low and error-free.
- **Wheel speed/accuracy:** weapon selection completes quickly with few mis-picks.
- **Noise level:** no overlapping prompts/toasts obscuring critical combat/map info in busy moments.
- **Accessibility:** UI remains usable with reduced motion and under longer localized strings; critical states understandable without color.
- **Performance:** stable target FPS in worst-case scenes after UI changes.

---

## 8. References and inspiration (examples)

- **GTA V (and GTA-style patterns):** contextual/minimal HUD, weapon wheel, map/navigation clarity, strong iconography and feedback loops.
- **Hades / Hades II:** disciplined glance budget, readable combat UI, strong feedback, boon/panel hierarchy (and lessons on text-size/accessibility tradeoffs).
- **Dead Cells:** minimal in-action HUD, scalable HUD/accessibility options, high-contrast readability.
- **Dead Space:** diegetic immersion and feedback integration (useful inspiration for 2D diegetic cues, applied selectively).
- **Destiny / Forza Horizon / Cyberpunk 2077 / Watch Dogs:** visual language references (sci-fi rings/glow, typographic clarity/spacing, neon accents, graphic motifs) — adapt subtly to ATOF's 2D style.
- **General guidance:** W3C/WCAG contrast principles, Game Accessibility Guidelines, Nielsen Norman visibility/feedback heuristics, and HUD/menu readability patterns (contrast on worst-case backgrounds, persistent-core vs contextual elements, <~100ms feedback perception targets).

---

## 9. Immediate next steps for ATOF (actionable)

1. **Codify UI tokens + panel/prompt primitives** and apply to radar, prompts, wheel overlay, and one menu as a template.
2. **Implement a small toast/notification manager** and wire first events: save complete, daily **+100 ₭** income, low ammo/reload needed, blocked interactions.
3. **Polish weapon wheel presentation** (center info, active wedge, dim, cached assets) without changing selection logic.
4. **Run a readability/localization pass** over HUD/prompts/menus in EN/UA/RU/ES/DE/FR and over worst-case bright/dark scenes.
5. **Add "Reduce motion" + HUD pulse intensity settings** and audit non-color state indicators.
6. **Plan quest/objective UI hooks now** (data/events for active objective, marker type, completion) so story/quest UI can land cleanly later.

*This document is intended as a living guide: update it as ATOF's UI systems (notifications, quest tracker, accessibility options) are implemented and playtested.*
# Graphics Upgrade Spec: SNES-Style Presentation

**Goal:** move from flat-color placeholder tiles ("Atari") to 16-bit-era
("SNES") presentation at the game's native 240x160, without breaking the
Raspberry Pi 4 performance budget (30 FPS min, spec 2.2).

**Principles**
1. **Palette discipline.** SNES look comes from consistent, limited palettes
   (4-6 shades per material), not from more colors. All art must draw from
   `PALETTES` in `src/world/gfx.py`.
2. **Shading and depth.** Every surface gets a light source (top-left):
   a highlight edge, a mid tone, and a dark edge. No flat fills.
3. **Dithering.** 2-3 shade transitions use sparse checker dithering —
   the cheap trick that reads as "16-bit" instantly.
4. **Animation.** Map sprites get 2-frame walk cycles; battle monsters get
   idle bob; water/ambient tiles get a 2-frame shimmer. No >2-frame loops
   (perf).
5. **Readability at 240x160.** Silhouettes first: distinct shapes per tile
   type so an 8-year-old can tell grass, tall grass, road, and solid tiles
   apart at a glance. Contrast beats detail.
6. **No checked-in binary assets in Phase 1.** All art stays procedural
   (`src/world/gfx.py`) so it renders on any machine. Real pixel-art PNGs
   are Phase 3 and MUST ship with an `assets/` fallback if missing.

**Phases**

- **Phase 1 — Procedural facelift (this PR):** shared palette module; rebuilt
  tile renderers (trees with trunk+canopy shading, dithered grass tufts,
  tall grass with motion lines, road with pebbles+edges, buildings with
  roofline/door/shadow); player sprite with 4-direction facing and 2-frame
  walk cycle; battle monsters redrawn larger with outline, shading, and
  idle bob; HP bars with bevel.
- **Phase 2 — Ambient life:** water tiles, animated flowers/NPC idle
  frames, warp-door glow, battle background gradients per zone type,
  screen-wipe transitions between zones.
- **Phase 3 — Real pixel art:** hire/generate 16x16 map tiles, 16x16 hero
  sheet, 32x32 (scaled 2x in battle) monster sheets; loader prefers
  `assets/tiles/*.png` and falls back to procedural; menu art + title logo.
- **Phase 4 — Polish:** shadows under entities, weather (leaves/embers),
  day/night tint per play time, CRT scanline toggle in Options.

**Performance rule:** every procedural surface is rendered once and cached
(`Tileset` cache pattern). Animated tiles cache both frames. Target: no
per-frame `pygame.draw` on the map path beyond blits.

**Acceptance**
- Visual: no flat single-color tiles remain; every tile has >=3 shades;
  player walks with visible animation; battle monsters are recognizable
  by silhouette and color.
- Perf: headless render loop stays under the 33ms/60-frame budget test.
- Tests: palette compliance test (every tile uses only palette colors),
  cache-hit test, walk-animation frame test.

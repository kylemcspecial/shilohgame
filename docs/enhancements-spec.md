# Enhancement Spec: Area Leaders, Badges, Puzzles, and Enjoyability Wins

Status: PROPOSED — next-step additions after Milestone 8 and the PR #19 polish pass.
Audience: Shiloh, age 8. Difficulty target: moderate challenge with clear signposting.

Calibration baseline (existing game):
- Regular trainers: Pineroot Scout L6–7, Forager L10–11, Climber L16–17, Glade Warden L26–27
- Emmett arc: L4–5, L14–15, L24–25
- Zones: Hunter's Rest (home), Whispering Pines, Pineroot Crossing, Mossy Hollow,
  Thornwood Ridge, Fernfall, Thornwick, Emberfern Glade

## 1. Area Leaders + Badges

### Concept
Each questing zone gets one Leader: a themed boss trainer who physically guards the
zone's exit doors. Beating them awards a Badge and unseals the gate to the next zone.
This gives every area a clear goal and makes zone progression feel earned.

### The Seven Leaders
| # | Zone | Leader | Theme / Team | Badge | Team levels* |
|---|------|--------|--------------|-------|--------------|
| 1 | whispering_pines | Warden Fenwick | Leaf (mossrat, fernpup, chirrel) | Pine Badge | 8–9 |
| 2 | pineroot_crossing | Chief Boulder | Stone (pebblet, cragmite, barkshell) | Stone Badge | 12–13 |
| 3 | mossy_hollow | Forager-Mother Ivy | Water/Leaf (dewvole, petalfin, marshpaw) | Fern Badge | 16–17 |
| 4 | thornwood_ridge | Climber Rex | Storm/Frost (sparkit, sleetfox, hailhawk) | Gale Badge | 20–21 |
| 5 | fernfall | Mayor Hazel | Mixed (fernfox, riverfin, bramblecat) | Bloom Badge | 24–25 |
| 6 | mossy_hollow_gate (Thornwick) | Gatekeeper Bram | Ember/Stone (kindlekit, cinderpy, granitewyrm) | Thorn Badge | 28–30 |
| 7 | emberfern_glade | Champion Pyra | Ember + ace (flarehound, smokeyote, infernox) | Ember Crown | 33–35 |

*Levels sit ~2–3 above the zone's strongest regular trainer and ~1–2 above the
matching Emmett fight, so each Leader is a real step up but never a wall.
An 8-year-old with a full party and potions in the Bag can win with type matchups.

### Mechanics
- **Gate sealing (no-badge gating).** Each zone's exit doors to the NEXT zone in the
  chain stay sealed until that zone's Leader is defeated. Stepping on a sealed door
  shows a flash: "The gate is sealed! Defeat Warden Fenwick first!" Side doors
  (back toward earlier zones) always work, so the player can never get trapped.
- **Leaders stand next to their gate** (trainer marker in leader colors with a small
  badge icon), talk-to-battle like Emmett (never ambushed). Losing just sends you to
  the lodge as usual — retry any time.
- **Badge rewards.** Each badge pays 3× the leader's coin reward, plus one unlock:
  - Pine Badge: Stout Trap unlocks at the shop
  - Stone Badge: Medium Potions stocked
  - Fern Badge: party storage accessible from the pause menu
  - Gale Badge: High Trap unlocks
  - Bloom Badge: rare berry patches appear (see §3.1)
  - Thorn Badge: Ultra Trap unlocks
  - Ember Crown: postgame — all Leaders rebattleable with stronger L45+ teams
- **Badge case.** Trainer Card gains a badge strip (7 slots, filled icons as earned).
- **Leader rematch (post-badge).** Beaten Leaders can be rebattled after the normal
  5-minute trainer cooldown, with teams scaled +3 levels. Good XP for grinding.

### Data schema
```json
// trainers.json additions per leader
"fenwick": {
  "name": "Warden Fenwick", "zone": "whispering_pines",
  "x": 9, "y": 11, "leader": true, "badge": "pine",
  "badge_name": "Pine Badge", "gate_zones": ["pineroot_crossing"],
  "intro": "None pass the pines without the Pine Badge!",
  "defeat": "The forest whispers your name now.",
  "reward": 120, "team": [ {"species": "mossrat", "level": 8}, ... ]
}
```
Save format: `badges: ["pine", ...]` added to the save dict (version bump 1 → 2,
old saves load with an empty badge list).

### Tests
- Gate: walking a sealed exit shows the flash and does NOT warp; after the badge it warps.
- Back-doors always warp regardless of badges (no trapping).
- Badge persistence: save/load round-trips badges; v1 saves load as badge-less.
- Trainer Card renders 7 badge slots, filled in earn order.
- Leader data validity: every leader has badge fields and a gate_zones target.

## 2. Zone Puzzles

Kid-friendly, no fail states that lose progress — failing just resets the puzzle.

### 2.1 Boulder Switch (Pineroot Crossing, guards Chief Boulder's gym)
Three boulders in a yard; slide them (walk into one to push it one tile) onto three
switch plates. All three lit → the gym door opens. Boulders can't be pushed into
trees/water; if one gets stuck, press X on it to reset the yard.

### 2.2 Stepping Stones (Mossy Hollow, before Forager-Mother Ivy)
A stream crossing where stones light up in a sequence shown by a friendly frog NPC
("watch my dance!"). Step the stones in the memorized order; a wrong step splashes you
back to the bank (no damage). Sequence length 4 → 5 after first success for replays.

### 2.3 Riddle Stones (Thornwood Ridge)
Three carved stones ask one question each; answers are hinted by NPCs in Fernfall and
by the Trainer Card stats (e.g. "How many badges does the young hunter carry?").
All three correct opens the shortcut ridge path (skips the tall-grass gauntlet).

### 2.4 Lantern Puzzle (Thornwick, before Gatekeeper Bram)
Four lanterns; stepping a lantern toggles it AND its neighbors (classic lights-out,
2×2 grid). All four lit → gate opens. Any state is solvable; a reset tile nearby.

### Implementation notes
- Puzzles live in `src/world/puzzles.py` with a tiny state per zone in the save
  (`puzzle_state: {"boulder": {"solved": true, ...}}`).
- Solved puzzles stay solved for the run (a solved gate is a normal door).
- A short jingle plays on solve (audio system already exists).

### Tests
- Each puzzle: solvable from its initial state, reset works, solved state persists
  in save/load, and solving opens the linked door/gate.

## 3. Smaller Enjoyability Wins

### 3.1 Regrowing berry patches
- 2–3 sparkling berry plants per forest zone; interact to pick 1–3 berries.
- Regrow after 10 minutes of playtime (per patch, persisted in save).
- Bloom Badge doubles yield. Encourages revisiting old zones for Bag supplies.

### 3.2 Rival rematches (Emmett arc extension)
- After each badge, Emmett appears in the next town with a stronger team and new
  dialogue; three extra fights (L10, L20, L30) bridging the existing three.
- Same `requires_defeat` chaining the arc already uses.

### 3.3 Shiny monsters
- 1-in-50 wild encounters spawn with a golden sparkle palette variant (+10% stats).
- Name shows a ★ (e.g. "★ Mossrat"); the catch jingle plays a special sparkle sting.
- Persists in party/storage/saves like any monster.

### 3.4 Day/night cycle
- 12-minute day/night (visual tint via a fullscreen overlay, no asset changes).
- Night (last 4 minutes) adds frost/storm species to encounter tables at low weight.
- Toggle in Options if the tint is unwanted; default on. No Pi perf cost (one blit).

## 4. Milestones

1. **M9 — Area Leaders + Badges** (§1): leaders, gating, badge case, save bump. Largest win; do first.
2. **M10 — Puzzles** (§2): one puzzle per zone, in the order Crossing → Hollow → Ridge → Thornwick.
3. **M11 — World liveliness** (§3): berry patches, Emmett rematches, shinies, day/night.

Each milestone is its own PR-sized chunk with tests; §1 and §2 are independent of
each other except that puzzle gates sit *before* leader gates in the same zones.

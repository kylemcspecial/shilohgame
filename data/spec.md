\# Fierce Monster Hunter: Game Specification

\*\*Version:\*\* 0.1 (draft for agentic coding handoff)
\*\*Target player:\*\* Shiloh, age 8
\*\*Platform:\*\* Raspberry Pi 4, ARM64 Linux (Twister OS)
\*\*Style:\*\* Retro 2D top-down RPG, inspired by Pokémon Red/Blue/Sapphire and SNES/Game Boy era visuals

\---

\## 1. Overview

Fierce Monster Hunter is a monster-catching RPG. The player explores forest zones and towns, randomly encounters fierce monsters, battles them and NPC trainers, catches monsters with traps, and grows a team of monsters that gain levels, learn moves, and evolve. There is no fixed ending. Gameplay loops endlessly, with a light story arc about outdoing the player's brother, Emmett.

\### Design Pillars
1\. \*\*Challenging but fair.\*\* Battles should take thought. Losing is normal and never punishing beyond a short trip home.
2\. \*\*Endless loop.\*\* There is always a stronger monster, a rarer trap, or a tougher trainer to chase.
3\. \*\*Age-appropriate.\*\* Monsters are fierce but cartoonish. No gore, no death, no real-world violence.
4\. \*\*Light on the hardware.\*\* Must run smoothly on a Raspberry Pi 4 with a small footprint.

\---

\## 2. Technical Requirements

\### 2.1 Stack
\- \*\*Language:\*\* Python 3.9+ (system Python on Twister OS, or a bundled venv)
\- \*\*Engine:\*\* pygame-ce (preferred) or pygame
\- \*\*Data:\*\* JSON for monsters, moves, types, zones, trainers, items, and dialogue
\- \*\*Saves:\*\* JSON files, human-readable, stored in a user data directory
\- \*\*No internet connection required.\*\* Fully offline.
\- \*\*No heavy engines\*\* (no Unity, Godot, or Electron)

\### 2.2 Performance Targets (Pi 4)
\- Steady 30 FPS minimum (60 FPS nice to have)
\- Startup under 5 seconds
\- Total install size under 100 MB including assets
\- RAM use under 300 MB during play
\- Load times between zones under 2 seconds

\### 2.3 Display & Rendering
\- Internal resolution \*\*240×160\*\* (Game Boy Advance style), scaled up to the screen with integer scaling for crisp pixels
\- Fallback: windowed mode at 2× or 3× scale
\- Fullscreen toggle (F11)
\- Tile size 16×16 px; sprites 32×32 px for monsters in battle, 16×16 px on the map

\### 2.4 Audio
\- Chiptune-style music and sound effects (royalty-free or generated)
\- Music and SFX volume settings
\- Game must still be fully playable with audio off

\### 2.5 Input
\- \*\*Keyboard:\*\* Arrow keys to move, Z to confirm, X to cancel, Enter for menu, Esc to pause
\- \*\*Gamepad:\*\* Standard USB or Bluetooth controllers supported via pygame joystick API
\- All menus navigable with either input

\---

\## 3. World & Locations

\### 3.1 Structure
\- \*\*Home Base:\*\* The starting village, "Hunter's Rest." Contains the player's house, the monster storage box, the Healing Lodge, and the Trap Shop. Players can always return here.
\- \*\*Forest Zones (minimum 4):\*\*
  - Whispering Pines (starter forest, easy monsters)
  - Mossy Hollow (mid-tier, damp and dark)
  - Thornwood Ridge (hilly, tougher monsters)
  - Emberfern Glade (late-game, rare monsters)
\- \*\*Towns (minimum 3):\*\* Each has a Healing Lodge, Trap Shop, and at least one battle NPC. Towns link to forest zones.
\- \*\*Connections:\*\* Walking off the edge of a forest or town moves to the next area. No loading screen longer than 2 seconds.

\### 3.2 Wild Encounters
\- Tall grass tiles trigger random encounters (roughly 1 in 8 steps, tuned during playtesting)
\- Each zone has its own encounter table with weights, so rare monsters appear less often
\- Encounter level is based on the zone and the player's average party level
\- Monsters can flee from battle (chance based on speed difference)

\### 3.3 NPCs
\- \*\*Trainers:\*\* Stand in set spots and challenge the player to battle when the player walks near them. Each trainer has a team, a short intro line, and a defeat line. Trainers can be battled again after a short cooldown.
\- \*\*Townsfolk:\*\* Give hints, flavor text, and tips about traps and types. No battles.
\- \*\*Healer:\*\* In every Healing Lodge. Fully restores the party and saves the game for free.
\- \*\*Trap Seller:\*\* Sells traps and healing items for coins earned in battle.

\---

\## 4. Monsters

\### 4.1 Roster
\- \*\*Total:\*\* 40 to 60 unique fierce monsters in the base game
\- Each has: name, type(s), base stats, rarity tier, evolution info, sprite, and a move list
\- Naming should be fun and fierce, for example Thornbear, Fangmoth, Stonewyrm, Ember Lynx

\### 4.2 Stats
\- \*\*HP:\*\* Health points. Monster faints at 0.
\- \*\*Attack:\*\* Power of offensive moves
\- \*\*Defense:\*\* Reduces damage from offensive moves
\- \*\*Speed:\*\* Decides turn order. Also affects flee chance.
\- \*\*Special:\*\* Power of special moves (optional split for depth)

\### 4.3 Rarity Tiers
| Tier | Name | Encounter Frequency | Catch Difficulty |
|------|------|--------------------|------------------|
| 1 | Common | High | Easy |
| 2 | Uncommon | Medium | Moderate |
| 3 | Rare | Low | Hard |
| 4 | Legendary | Very rare (scripted or boss) | Very hard |

\### 4.4 Types
Use 6 to 8 forest-themed types with simple advantages and disadvantages, similar to Pokémon:

\- \*\*Leaf\*\* beats Stone and Water
\- \*\*Ember\*\* beats Leaf and Frost
\- \*\*Water\*\* beats Ember and Stone
\- \*\*Stone\*\* beats Ember and Storm
\- \*\*Storm\*\* beats Water and Leaf
\- \*\*Frost\*\* beats Leaf and Storm
\- \*\*Shadow\*\* (optional) is strong against Leaf and Ember, weak to Storm

Neutral matchups deal normal damage. Super effective deals 2×. Not very effective deals 0.5×.

\### 4.5 Evolution
\- Monsters evolve at set levels (for example, level 16 and level 32)
\- Some evolutions trigger on defeating a certain number of monsters or on an item (optional)
\- Evolved forms gain new stats, a new sprite, and sometimes a new type
\- Evolution screen plays a short animation (under 3 seconds, no flashing effects)

\---

\## 5. Moves

\### 5.1 Move Categories
\- \*\*Offensive:\*\* Deals damage. Has power, accuracy, type, and PP.
\- \*\*Defensive:\*\* Raises Defense, lowers the enemy's Attack, or heals a small amount of HP.
\- \*\*Status (light):\*\* Causes simple effects such as a slowdown or a damage-over-time effect. Short duration, cleared after battle.

\### 5.2 Starting Moves
\- Every monster starts with \*\*1 offensive move and 1 defensive move\*\*
\- Starting moves are fixed per species

\### 5.3 Learning Moves
\- Each species has a \*\*move pool\*\* of 6 to 12 moves
\- At set levels, the monster learns a new move from its pool
\- If the monster already knows 4 moves, the player chooses which move to forget
\- Maximum of 4 moves known at once

\### 5.4 Move Count
\- Monsters can know up to 4 moves
\- Each move has PP (3 to 15 uses). PP restores at the Healing Lodge.

\---

\## 6. Battle System

\### 6.1 Format
\- \*\*Turn-based\*\*, one monster per side (singles only in v1)
\- Battles start with an intro animation under 2 seconds
\- Each turn, the player picks: \*\*Fight, Bag (items), Switch, Catch, Run\*\*

\### 6.2 Turn Order
\- Higher Speed goes first
\- Ties are broken randomly
\- Using an item or switching always goes before the enemy attack

\### 6.3 Damage Formula (simplified)
\`\`\`
damage = ((2 × level / 5 + 2) × power × attack / defense) / 50 + 2
damage × type_multiplier × random(0.85 to 1.0)
\`\`\`
Keep values small and readable. Show the damage number and a short "It's super effective!" or "It's not very effective..." message.

\### 6.4 Fainting
\- When a monster reaches 0 HP, it faints
\- Fainted monsters are \*\*not lost\*\*. They are healed back to full HP at any Healing Lodge.
\- If all party monsters faint, the player is sent back to the nearest Healing Lodge, and coins are reduced slightly
\- Fainting never causes permanent loss

\### 6.5 Experience & Leveling
\- Defeating or catching a monster gives experience points (XP) to the active monster
\- Monsters level up from 1 to 50 (v1 cap, expandable)
\- Player also levels up from battles, unlocking better trap tiers and zones
\- Experience scales with the defeated monster's level and rarity

\### 6.6 Running
\- Running from a trainer battle is not allowed
\- Running from a wild battle succeeds based on Speed comparison and a random roll

\---

\## 7. Catching Monsters

\### 7.1 Core Rule
\- Monsters can only be caught \*\*after they are weakened\*\*
\- Catching is allowed only when the wild monster's HP is at or below \*\*50%\*\* (tunable)
\- Attempting to catch above the threshold shows a message like "It's too strong to catch yet!" and wastes the turn

\### 7.2 Trap Tiers
| Trap | Unlock | Base Catch Bonus | Cost |
|------|--------|------------------|------|
| Basic Trap | Start | 1.0× | 20 coins |
| Stout Trap | Player level 10 | 1.5× | 60 coins |
| High Trap | Player level 25 | 2.0× | 150 coins |
| Ultra Trap | Player level 40 | 3.0× | 400 coins |

\### 7.3 Catch Chance Formula
Keep it readable for the player. Suggested approach:
\`\`\`
catch_chance = base_rate × trap_bonus × (1 - current_HP / max_HP) × rarity_modifier × level_modifier
\`\`\`
\- Rarity modifier: Common 1.0, Uncommon 0.7, Rare 0.4, Legendary 0.15
\- Level modifier: reduced for monsters much higher level than the player's best monster
\- Clamp the final chance between 5% and 95% so catching is always possible but never guaranteed

\### 7.4 Feedback
\- Trap animation (shake or wobble, under 2 seconds)
\- Success: "Gotcha! \[Monster\] was caught!" with a short jingle
\- Failure: "Oh no! It broke free!" and the monster gets a turn

\---

\## 8. Party, Storage & Items

\### 8.1 Party
\- Player carries up to \*\*6 monsters\*\* in the party
\- Extra monsters go to \*\*storage\*\* at home base (unlimited)
\- Monsters can be swapped in the menu outside battle

\### 8.2 Items
\- \*\*Potions:\*\* Restore HP (small, medium, large)
\- \*\*Revive Herb:\*\* Brings a fainted monster back at half HP (optional)
\- \*\*Traps:\*\* Basic, Stout, High, Ultra
\- \*\*Berries:\*\* Restore PP
\- \*\*Key Items:\*\* Quest or unlock items, never used up

\### 8.3 Coins
\- Earned from trainer battles and wild battles
\- Spent at the Trap Shop and item shops

\---

\## 9. Progression Loop (Endless Play)

\### 9.1 Story Arc (Light)
\- The player's brother Emmett has been hunting monsters longer. The player wants to be better than him.
\- Emmett appears at key points (home base, first town, first zone clear) and gives a short rivalry challenge that gets harder each time.
\- Emmett is never a villain. He is a friendly rival.

\### 9.2 Endless Loop
\- After the Emmett arc milestones are reached, the game continues indefinitely
\- \*\*Monster Gym Leader style trainers\*\* appear in each zone, with teams that scale with player level
\- \*\*Weekly Challenge\*\* style rotating trainers in home base (optional, based on in-game time)
\- \*\*Rare monster hunts:\*\* Legendaries and rare variants spawn with a low chance every time
\- \*\*Level cap\*\* and \*\*Hall of Fame\*\* style leaderboard for total monsters caught and battles won (local only)

\### 9.3 Difficulty Scaling
\- Wild and trainer monster levels scale with the player's average party level
\- Trainer teams get tougher as the player progresses through zones
\- Difficulty never becomes unfair. Enemy level never exceeds the player's highest level plus 5.

\---

\## 10. Save System

\- \*\*Save points:\*\* Healing Lodge (always available) and the player's bedroom at home base
\- \*\*Auto-save\*\* when entering home base and after each gym-style trainer win
\- \*\*Three save slots\*\*
\- Save file includes: player position, party, storage, items, coins, trainer defeat flags, zone progress, play time
\- Save files stored as JSON in the user's data folder
\- Corrupted save detection: show a message and offer to start a new save rather than crashing

\---

\## 11. Menus & UI

\- \*\*Main menu:\*\* New Game, Continue, Options, Quit
\- \*\*Pause menu:\*\* Monsters (party), Bag, Trainer Card, Save, Options, Exit
\- \*\*Trainer card:\*\* Name, play time, monsters caught, battles won, coins
\- \*\*Options:\*\* Music volume, SFX volume, text speed, fullscreen, controls
\- \*\*Text speed:\*\* Slow, Normal, Fast
\- All text readable at 240×160 internal resolution. Use a pixel font with at least 8 px letter height.

\---

\## 12. Content Guidelines (Age-Appropriate)

\- Monsters can be fierce, growl, and look intimidating, but they are never gruesome
\- No blood, gore, or visible injury. Fainting shows a simple "X" or spin-out animation.
\- Trap language: "catch," "gotcha," "broke free." No "kill" or "death."
\- Villains are not used. Trainers are friendly competitors.
\- Dialogue stays positive, encouraging, and simple
\- No real-world brands, real people, or outside copyrighted characters

\---

\## 13. Project Structure (suggested)

\`\`\`
fierce-monster-hunter/
├── main.py
├── requirements.txt
├── README.md
├── src/
│   ├── engine/         # game loop, scenes, input, audio
│   ├── world/          # maps, tiles, NPCs, encounters
│   ├── battle/         # battle logic, damage, catch
│   ├── monsters/       # monster class, leveling, evolution
│   ├── ui/             # menus, dialogue, HUD
│   └── save/           # save/load JSON
├── data/
│   ├── monsters.json
│   ├── moves.json
│   ├── types.json
│   ├── zones.json
│   ├── trainers.json
│   └── items.json
├── assets/
│   ├── sprites/
│   ├── tiles/
│   ├── maps/
│   ├── fonts/
│   └── audio/
└── tests/
\`\`\`

\---

\## 14. Build Milestones

1\. \*\*Milestone 1:\*\* Window, scaling, input, and a walkable tile map at home base
2\. \*\*Milestone 2:\*\* Random encounters in Whispering Pines and a basic battle (Fight and Run)
3\. \*\*Milestone 3:\*\* Catching with traps and the catch formula
4\. \*\*Milestone 4:\*\* Leveling, learning moves, party, and storage
5\. \*\*Milestone 5:\*\* Healing Lodge, fainting, and save/load (three slots)
6\. \*\*Milestone 6:\*\* Trainers, Emmett arc, and the remaining forest zones and towns
7\. \*\*Milestone 7:\*\* Evolution, types, full monster roster, and endless loop features
8\. \*\*Milestone 8:\*\* Audio, polish, Pi 4 performance tuning, and playtest with Shiloh

\---

\## 15. Acceptance Criteria (Summary)

\- Game launches on a Raspberry Pi 4 running Twister OS with no crashes in a 30-minute session
\- Player can start a new game, catch a monster, level it up, learn a new move, and evolve it
\- Fainted monsters are healed at a Healing Lodge with no loss
\- Catching is blocked above the HP threshold and works below it
\- Save and load work across all three slots, including after closing and reopening the game
\- Total monster roster is 40+ with working evolution chains
\- Frame rate stays at or above 30 FPS during battles and exploration
\- Content passes the age-appropriate guidelines in Section 12

\---

\## 16. Open Questions (for later decisions)

\- Exact monster names, sprites, and type chart values (can be generated in milestone 7)
\- Whether to add a second playable character or keep one player
\- Whether to include a simple map overlay or minimap
\- Final catch formula tuning after playtesting with Shiloh
\- Whether Emmett's rival battles should show his team or stay mysterious

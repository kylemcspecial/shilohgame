# Fierce Monster Hunter

A retro 2D top-down monster-catching RPG for an 8-year-old hunter.
Built with Python + pygame-ce. Target platform: Raspberry Pi 4 (Twister OS).

## Run

```bash
pip install -r requirements.txt
python main.py
```

- Arrows / WASD: move
- Z / Space: confirm
- X / Backspace: cancel
- Enter: menu, Esc: pause
- F11: fullscreen toggle
- Gamepads supported via the pygame joystick API

## Status

- [x] Milestone 1: Window, integer scaling, input, walkable home base (Hunter's Rest)
- [x] Milestone 2: Random encounters in Whispering Pines + basic battle
- [x] Milestone 3: Catching with traps
- [x] Milestone 4: Leveling, moves, party, storage
- [x] Milestone 5: Healing Lodge, fainting, save/load
- [x] Milestone 6: Trainers, Emmett arc, zones and towns
- [x] Milestone 7: Evolution, types, full roster, endless loop
- [ ] Milestone 8: Audio, polish, Pi 4 tuning

## Layout

```
main.py          entry point
src/engine/      game loop, scenes, input
src/world/       maps, tiles, movement
data/            JSON game data (zones, monsters, ...)
tests/           unit tests
```

# Fierce Monster Hunter

A retro 2D top-down monster-catching RPG for an 8-year-old hunter.
Built with Python + pygame-ce. Target platform: Raspberry Pi 4 (Twister OS).

## Run

Quick start:

```bash
pip install -r requirements.txt
python main.py
```

## Install on Raspberry Pi (recommended)

One-time setup on the Pi (Twister OS / Raspberry Pi OS):

```bash
./install-pi.sh
```

This creates a dedicated virtual environment, installs pygame-ce and numpy,
generates the game icon, and adds a launcher — find the game under
**Menu > Games > Fierce Monster Hunter**, plus a shortcut on the desktop.
Saves live in `~/.local/share/fierce-monster-hunter/saves` and are untouched
by `./install-pi.sh --uninstall`.

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
- [x] Milestone 8: Audio, polish, Pi 4 tuning

## Layout

```
main.py          entry point
src/engine/      game loop, scenes, input
src/world/       maps, tiles, movement
data/            JSON game data (zones, monsters, ...)
tests/           unit tests
```

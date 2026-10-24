# Fierce Monster Hunter

A retro 2D top-down monster-catching RPG for an 8-year-old hunter.
Built with Python + pygame-ce. Target platform: Raspberry Pi 4 (Twister OS).

## Install on Raspberry Pi

One-time setup on the Pi (Twister OS / Raspberry Pi OS) — **use this, not pip**:

```bash
sudo apt install -y python3-venv   # only if the installer says it's missing
bash install-pi.sh
```

The installer creates a dedicated virtual environment (so no PEP 668
"externally managed environment" errors), installs pygame-ce and numpy,
generates the game icon, and adds a launcher — find the game under
**Menu > Games > Fierce Monster Hunter**, plus a shortcut on the desktop.
Saves live in `~/.local/share/fierce-monster-hunter/saves` and are untouched
by `bash install-pi.sh --uninstall`.

### Troubleshooting

- **"externally managed environment" from pip**: Raspberry Pi OS (Bookworm+)
marks the system Python as externally managed. Don't install system-wide —
run `bash install-pi.sh` (or `--break-system-packages` only as a last resort).
- **"unsupported file given on command line" or `$'\r': command not found`**:
the script file was mangled in transit (CRLF line endings). Fix with
`sed -i 's/\r$//' install-pi.sh && bash install-pi.sh`, or re-clone:
`git clone https://github.com/kylemcspecial/shilohgame.git && cd shilohgame`.
- **venv creation fails**: `sudo apt install -y python3-venv`, then rerun the
installer.

## Run (other systems)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
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
- [x] Milestone 8: Audio, polish, Pi 4 tuning

## Layout

```
main.py          entry point
src/engine/      game loop, scenes, input
src/world/       maps, tiles, movement
data/            JSON game data (zones, monsters, ...)
tests/           unit tests
```

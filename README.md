# Fierce Monster Hunter

A retro 2D top-down monster-catching RPG for an 8-year-old hunter.
Built with Python + pygame-ce. Target platform: Raspberry Pi 4 (Twister OS).

## Install on Raspberry Pi — one command

Copy-paste this whole line on the Pi (Twister OS / Raspberry Pi OS):

```bash
git clone https://github.com/kylemcspecial/shilohgame.git && cd shilohgame && bash install
```

That's the entire setup. It clones the game, makes sure `python3-venv`
is installed (asking for sudo only if needed), creates a dedicated virtual
environment (so no PEP 668 "externally managed environment" errors), pulls
pygame-ce and numpy, generates the icon, and puts **Fierce Monster Hunter**
on the desktop and under **Menu > Games**. From then on, Shiloh just clicks
the icon.

To remove it later: `bash install --uninstall` (saves are kept in
`~/.local/share/fierce-monster-hunter/saves`).

### Troubleshooting

- **"externally managed environment" from pip**: Raspberry Pi OS (Bookworm+)
marks the system Python as externally managed. Don't install system-wide —
`bash install` uses its own venv.
- **"unsupported file given on command line" or `$'\r': command not found`**:
the script was mangled in transit (CRLF line endings — shouldn't happen via
git clone). Fix with `sed -i 's/\r$//' install && bash install`.
- **venv creation fails**: the installer tries to install `python3-venv`
itself; if sudo wasn't available, run `sudo apt install -y python3-venv`
and rerun `bash install`.

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

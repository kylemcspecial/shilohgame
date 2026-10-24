#!/usr/bin/env bash
# Fierce Monster Hunter — Raspberry Pi installer.
#
# Sets up a dedicated venv, installs pygame-ce + numpy, generates the icon,
# and adds a desktop launcher so the game starts with one click.
#
# Usage:  ./install-pi.sh [--uninstall]
set -euo pipefail

GAME_NAME="Fierce Monster Hunter"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fierce-monster-hunter"
ICON_PATH="$SCRIPT_DIR/assets/icon.png"
DESKTOP_FILE="$HOME/.local/share/applications/fierce-monster-hunter.desktop"

say() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

uninstall() {
  say "Removing desktop launcher and venv (game data in '$DATA_DIR' is kept)"
  rm -f "$DESKTOP_FILE" "$DESKTOP_DIR/fierce-monster-hunter.desktop"
  rm -rf "$VENV_DIR"
  say "Uninstalled. Saves stay in '$DATA_DIR' — delete that folder to remove them."
  exit 0
}

[[ "${1:-}" == "--uninstall" ]] && uninstall
[[ -f "$SCRIPT_DIR/main.py" ]] || die "run this from the game folder (main.py not found)"

say "Checking Python 3.9+"
command -v python3 >/dev/null || die "python3 not found"
PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
  || die "Python 3.9+ required (found $PYV)"

if [[ ! -d "$VENV_DIR" ]]; then
  say "Creating virtual environment ($VENV_DIR)"
  python3 -m venv "$VENV_DIR" || die "venv creation failed —install python3-venv: sudo apt install python3-venv"
fi

say "Installing dependencies (pygame-ce, numpy)"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1 || true
"$VENV_DIR/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt" \
  || die "pip install failed —check network, then rerun"

if [[ ! -f "$ICON_PATH" ]]; then
  say "Generating icon"
  "$VENV_DIR/bin/python" "$SCRIPT_DIR/make_icon.py" >/dev/null
fi
[[ -f "$ICON_PATH" ]] || die "icon generation failed"

say "Creating desktop launcher"
mkdir -p "$HOME/.local/share/applications"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$GAME_NAME
Comment=Fierce monster-catching RPG
Exec=$VENV_DIR/bin/python $SCRIPT_DIR/main.py
Icon=$ICON_PATH
Terminal=false
Categories=Game;
EOF
chmod +x "$DESKTOP_FILE"

# copy to the desktop too, if it exists
if [[ -d "$DESKTOP_DIR" ]]; then
  cp "$DESKTOP_FILE" "$DESKTOP_DIR/fierce-monster-hunter.desktop"
fi

# refresh the menu cache if the helper is available
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" || true

say "Smoke test: importing the game"
"$VENV_DIR/bin/python" -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); import src.engine.game" \
  || die "game import failed —please report this"

cat <<DONE

Install complete!
  Launch:   Menu > Games > $GAME_NAME
  Terminal: $VENV_DIR/bin/python $SCRIPT_DIR/main.py
  Saves:    $DATA_DIR/saves
  Uninstall: ./install-pi.sh --uninstall

DONE

"""Exercise installer prerequisite handling without sudo or package downloads."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize("missing_ensurepip", [False, True])
def test_installer_checks_ensurepip(tmp_path, missing_ensurepip):
    project = tmp_path / "game"
    project.mkdir()
    shutil.copyfile(Path(__file__).resolve().parents[1] / "install", project / "install")
    (project / "main.py").touch()
    (project / "requirements.txt").touch()
    (project / "assets").mkdir()
    (project / "assets/icon.png").touch()
    home = tmp_path / "home"
    home.mkdir()
    commands = tmp_path / "bin"
    commands.mkdir()
    # Simulate Debian: import venv works, but ensurepip may be absent.
    scripts = {
        "python3": '''#!/bin/bash
set -eu
if [[ "$1" == "-c" ]]; then
  if [[ "$2" == *ensurepip* && "$MISSING_ENSUREPIP" == 1 && ! -f "$INSTALL_STATE" ]]; then
    exit 1
  fi
  exit 0
fi
if [[ "$1" == "-m" && "$2" == venv ]]; then
  if [[ "$MISSING_ENSUREPIP" == 1 && ! -f "$INSTALL_STATE" ]]; then
    echo 'ensurepip unavailable' >&2
    exit 1
  fi
  mkdir -p "$3/bin"
  for tool in python pip; do
    printf '#!/bin/bash\\nexit 0\\n' > "$3/bin/$tool"
    chmod +x "$3/bin/$tool"
  done
  exit 0
fi
exit 1
''',
        "sudo": '''#!/bin/bash
set -eu
printf '%s\\n' "$*" >> "$INSTALL_LOG"
[[ "$*" != 'apt-get install -y python3-venv' ]] || touch "$INSTALL_STATE"
''',
        "update-desktop-database": "#!/bin/bash\nexit 0\n",
    }
    for name, script in scripts.items():
        path = commands / name
        path.write_text(script)
        path.chmod(0o755)
    log = tmp_path / "sudo.log"
    environment = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}",
                       HOME=str(home), XDG_DESKTOP_DIR=str(home / "Desktop"),
                       MISSING_ENSUREPIP=str(int(missing_ensurepip)),
                       INSTALL_STATE=str(tmp_path / "installed"), INSTALL_LOG=str(log))
    result = subprocess.run(["bash", str(project / "install")], env=environment,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    if missing_ensurepip:
        assert log.read_text().splitlines() == [
            "apt-get update -qq", "apt-get install -y python3-venv"]
    else:
        assert not log.exists()
    assert (home / ".local/share/applications/fierce-monster-hunter.desktop").exists()

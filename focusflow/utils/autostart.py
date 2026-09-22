"""
Linux XDG Autostart Manager for FocusFlow.
Manages ~/.config/autostart/focusflow.desktop.
"""

import sys
import shutil
from pathlib import Path

from focusflow.config import APP_NAME, APP_DESCRIPTION, XDG_CONFIG_HOME, ICON_PATH

AUTOSTART_DIR = XDG_CONFIG_HOME / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "focusflow.desktop"


def is_autostart_enabled() -> bool:
    """Check if the autostart .desktop entry exists."""
    return AUTOSTART_FILE.exists()


def enable_autostart(app_command: str = "focusflow") -> bool:
    """Create ~/.config/autostart/focusflow.desktop."""
    try:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        # Find path to python launcher if focusflow command is not installed system-wide
        exec_cmd = shutil.which("focusflow") or f"{sys.executable} -m focusflow.app"

        content = f"""[Desktop Entry]
Type=Application
Version=1.0
Name={APP_NAME}
Comment={APP_DESCRIPTION}
Exec={exec_cmd}
Icon={ICON_PATH}
Terminal=false
Categories=Utility;Productivity;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
        AUTOSTART_FILE.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False


def disable_autostart() -> bool:
    """Remove ~/.config/autostart/focusflow.desktop."""
    try:
        if AUTOSTART_FILE.exists():
            AUTOSTART_FILE.unlink()
        return True
    except Exception:
        return False

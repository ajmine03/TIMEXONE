"""
FocusFlow Configuration and Constants.
Centralizes paths, default values, and application metadata.
"""

from pathlib import Path
import os
import sys

# Application Metadata
APP_NAME = "FocusFlow"
APP_ID = "org.focusflow.FocusFlow"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Native Linux Pomodoro, Todo & Productivity Tracker"

# XDG Standard Base Directories
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

APP_CONFIG_DIR = XDG_CONFIG_HOME / "focusflow"
APP_DATA_DIR = XDG_DATA_HOME / "focusflow"

# Ensure runtime directories exist
APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database file location
DEFAULT_DB_PATH = APP_DATA_DIR / "focusflow.db"

# Assets Directory
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_PATH = ASSETS_DIR / "focusflow.svg"
CHIME_PATH = ASSETS_DIR / "chime.wav"

# Default Timer Durations (in seconds)
DEFAULT_FOCUS_DURATION = 25 * 60       # 25 minutes
DEFAULT_SHORT_BREAK = 5 * 60          # 5 minutes
DEFAULT_LONG_BREAK = 15 * 60          # 15 minutes
DEFAULT_LONG_BREAK_INTERVAL = 4       # Pomodoros before long break

# Productivity Defaults
DEFAULT_DAILY_GOAL_SECONDS = 2 * 3600 # 2 hours
DEFAULT_IDLE_THRESHOLD_SECONDS = 5 * 60 # 5 minutes

# Default Preferences
DEFAULT_PREFERENCES = {
    "focus_duration": DEFAULT_FOCUS_DURATION,
    "short_break": DEFAULT_SHORT_BREAK,
    "long_break": DEFAULT_LONG_BREAK,
    "long_break_interval": DEFAULT_LONG_BREAK_INTERVAL,
    "auto_start_breaks": True,
    "auto_start_focus": False,
    "notifications_enabled": True,
    "sound_enabled": True,
    "theme": "system",                 # 'dark', 'light', 'system'
    "floating_opacity": 0.95,
    "floating_always_on_top": True,
    "floating_auto_show": True,
    "floating_compact": False,
    "floating_x": 100,
    "floating_y": 100,
    "floating_width": 260,
    "floating_height": 140,
    "daily_goal_seconds": DEFAULT_DAILY_GOAL_SECONDS,
    "idle_threshold_seconds": DEFAULT_IDLE_THRESHOLD_SECONDS,
    "idle_action": "ask",              # 'ask', 'pause', 'ignore'
    "autostart_enabled": False,
    "first_run_completed": False,
}

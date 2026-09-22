#!/usr/bin/env python3
"""
FocusFlow Launcher.
Executes the native Linux Pomodoro, Todo & Productivity Tracker.
"""

import sys
import os

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focusflow.app import main

if __name__ == "__main__":
    sys.exit(main())

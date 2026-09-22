"""
Privacy-Safe System Idle Detection and Focus Tracking for FocusFlow.
Detects user inactivity on Linux desktops via XScreenSaver or DBus without surveillance.
"""

import os
import sys
import ctypes
import logging
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from focusflow.db.repository import Repository
from focusflow.core.timer import PomodoroEngine, TimerState

logger = logging.getLogger(__name__)


class XScreenSaverInfo(ctypes.Structure):
    _fields_ = [
        ("window", ctypes.c_ulong),
        ("state", ctypes.c_int),
        ("kind", ctypes.c_int),
        ("til_or_since", ctypes.c_ulong),
        ("idle", ctypes.c_ulong),
        ("eventMask", ctypes.c_ulong),
    ]


class IdleDetector(QObject):
    """Detects system-wide user inactivity using standard Linux APIs."""

    idle_threshold_exceeded = pyqtSignal(int)  # idle_seconds
    returned_from_idle = pyqtSignal(int)       # past_idle_seconds

    def __init__(self, repository: Repository, engine: PomodoroEngine, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.engine = engine

        self._is_idle = False
        self._idle_seconds_accumulated = 0

        self._x11_display = None
        self._xss_lib = None
        self._x11_lib = None
        self._xss_info = None
        self._is_x11_available = False

        self._init_x11()

    def _init_x11(self):
        """Try loading libX11 and libXss for idle queries."""
        try:
            if not os.environ.get("DISPLAY"):
                return

            self._x11_lib = ctypes.cdll.LoadLibrary("libX11.so.6")
            self._xss_lib = ctypes.cdll.LoadLibrary("libXss.so.1")

            self._x11_lib.XOpenDisplay.restype = ctypes.c_void_p
            self._x11_lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
            self._x11_lib.XDefaultRootWindow.restype = ctypes.c_ulong
            self._x11_lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]

            self._xss_lib.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)
            self._xss_lib.XScreenSaverQueryInfo.restype = ctypes.c_int
            self._xss_lib.XScreenSaverQueryInfo.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.POINTER(XScreenSaverInfo),
            ]

            display_str = os.environ.get("DISPLAY", ":0").encode("utf-8")
            self._x11_display = self._x11_lib.XOpenDisplay(display_str)
            if self._x11_display:
                self._xss_info = self._xss_lib.XScreenSaverAllocInfo()
                self._is_x11_available = True
        except Exception as e:
            logger.debug("X11 Idle detection unavailable: %s", e)
            self._is_x11_available = False

    def get_idle_seconds(self) -> Optional[int]:
        """Returns the number of seconds the system has been idle, or None."""
        # 1. Try X11 / XScreenSaver
        if self._is_x11_available and self._x11_display and self._xss_info:
            try:
                root_win = self._x11_lib.XDefaultRootWindow(self._x11_display)
                res = self._xss_lib.XScreenSaverQueryInfo(self._x11_display, root_win, self._xss_info)
                if res:
                    return int(self._xss_info.contents.idle / 1000)
            except Exception:
                pass

        # 2. Try DBus ScreenSaver if available
        try:
            import dbus
            bus = dbus.SessionBus()
            ss_obj = bus.get_object("org.freedesktop.ScreenSaver", "/ScreenSaver")
            ss_iface = dbus.Interface(ss_obj, "org.freedesktop.ScreenSaver")
            idle_sec = ss_iface.GetSessionIdleTime()
            return int(idle_sec)
        except Exception:
            pass

        return None

    def check_idle(self):
        """Called once every heartbeat tick."""
        if not self.engine.state.is_focus:
            if self._is_idle:
                self._is_idle = False
                self._idle_seconds_accumulated = 0
            return

        idle_sec = self.get_idle_seconds()
        if idle_sec is None:
            return

        threshold = int(self.repo.get_preference("idle_threshold_seconds", 300))

        if idle_sec >= threshold:
            if not self._is_idle:
                self._is_idle = True
                self._idle_seconds_accumulated = idle_sec
                action = self.repo.get_preference("idle_action", "ask")
                if action == "pause":
                    self.engine.pause()
                self.idle_threshold_exceeded.emit(idle_sec)
            else:
                self._idle_seconds_accumulated = max(self._idle_seconds_accumulated, idle_sec)
        else:
            if self._is_idle:
                past_idle = self._idle_seconds_accumulated
                self._is_idle = False
                self._idle_seconds_accumulated = 0
                self.returned_from_idle.emit(past_idle)

"""
Native Linux desktop notification service for FocusFlow.
Uses DBus org.freedesktop.Notifications, notify-send, or Qt fallback.
"""

import shutil
import subprocess
import logging
from typing import Optional

from focusflow.config import APP_NAME, ICON_PATH
from focusflow.utils.sound import SoundPlayer

logger = logging.getLogger(__name__)


class NotificationService:
    """Dispatches native desktop notifications with optional audio alerts."""

    def __init__(self, sound_player: Optional[SoundPlayer] = None):
        self.sound = sound_player if sound_player else SoundPlayer()
        self.notify_send_bin = shutil.which("notify-send")
        self._dbus_notify = None
        self._init_dbus()

    def _init_dbus(self):
        """Attempt to initialize direct DBus notification interface."""
        try:
            import dbus
            bus = dbus.SessionBus()
            notify_obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
            self._dbus_notify = dbus.Interface(notify_obj, "org.freedesktop.Notifications")
        except Exception:
            self._dbus_notify = None

    def send_notification(
        self,
        title: str,
        message: str,
        urgency: str = "normal",  # 'low', 'normal', 'critical'
        play_sound: bool = True,
    ):
        """Deliver a desktop notification and trigger sound."""
        if play_sound:
            self.sound.play_chime()

        # Try DBus first
        if self._dbus_notify:
            try:
                # org.freedesktop.Notifications.Notify(app_name, replaces_id, app_icon, summary, body, actions, hints, timeout)
                hints = {"urgency": 2 if urgency == "critical" else 1}
                self._dbus_notify.Notify(
                    APP_NAME,
                    0,
                    str(ICON_PATH) if ICON_PATH.exists() else "alarm",
                    title,
                    message,
                    [],
                    hints,
                    6000,
                )
                return
            except Exception as e:
                logger.debug("DBus Notify failed: %s", e)

        # Fallback to notify-send
        if self.notify_send_bin:
            try:
                cmd = [
                    self.notify_send_bin,
                    "-a", APP_NAME,
                    "-u", urgency,
                ]
                if ICON_PATH.exists():
                    cmd.extend(["-i", str(ICON_PATH)])
                cmd.extend([title, message])
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception as e:
                logger.debug("notify-send failed: %s", e)

        logger.info("Notification: [%s] %s", title, message)

    def notify_pomodoro_completed(self, task_title: Optional[str] = None, duration_mins: int = 25):
        msg = f"You completed a {duration_mins}-minute focus session!"
        if task_title:
            msg = f"You completed {duration_mins} minutes focused on: {task_title}"
        self.send_notification("Pomodoro Complete! 🎯", msg, urgency="normal")

    def notify_break_started(self, break_type: str = "short", duration_mins: int = 5):
        label = "Short Break" if break_type == "short" else "Long Break"
        msg = f"Take a restful {duration_mins}-minute break. Step away from the screen!"
        self.send_notification(f"Time for a {label} ☕", msg, urgency="normal")

    def notify_break_completed(self):
        msg = "Ready to start another productive focus session?"
        self.send_notification("Break Finished! 🚀", msg, urgency="normal")

    def notify_daily_goal_reached(self, goal_hours: float):
        msg = f"Congratulations! You've achieved your daily focus goal of {goal_hours:.1f} hours."
        self.send_notification("Daily Goal Reached! 🏆", msg, urgency="normal")

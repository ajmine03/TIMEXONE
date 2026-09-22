"""
Pomodoro Timer Engine for FocusFlow.
Drift-free, timestamp-based state machine with pause/resume, break cycling,
session persistence, and event callbacks.
"""

import time
import math
import logging
from enum import Enum
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

from focusflow.config import (
    DEFAULT_FOCUS_DURATION,
    DEFAULT_SHORT_BREAK,
    DEFAULT_LONG_BREAK,
    DEFAULT_LONG_BREAK_INTERVAL,
)
from focusflow.db.repository import Repository, PomodoroSession

logger = logging.getLogger(__name__)


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING_FOCUS = "running_focus"
    PAUSED_FOCUS = "paused_focus"
    RUNNING_SHORT_BREAK = "running_short_break"
    PAUSED_SHORT_BREAK = "paused_short_break"
    RUNNING_LONG_BREAK = "running_long_break"
    PAUSED_LONG_BREAK = "paused_long_break"

    @property
    def is_running(self) -> bool:
        return self in (
            TimerState.RUNNING_FOCUS,
            TimerState.RUNNING_SHORT_BREAK,
            TimerState.RUNNING_LONG_BREAK,
        )

    @property
    def is_paused(self) -> bool:
        return self in (
            TimerState.PAUSED_FOCUS,
            TimerState.PAUSED_SHORT_BREAK,
            TimerState.PAUSED_LONG_BREAK,
        )

    @property
    def is_break(self) -> bool:
        return self in (
            TimerState.RUNNING_SHORT_BREAK,
            TimerState.PAUSED_SHORT_BREAK,
            TimerState.RUNNING_LONG_BREAK,
            TimerState.PAUSED_LONG_BREAK,
        )

    @property
    def is_focus(self) -> bool:
        return self in (TimerState.RUNNING_FOCUS, TimerState.PAUSED_FOCUS)


class PomodoroEngine:
    """Drift-free, accurate Pomodoro timer state machine."""

    def __init__(
        self,
        repository: Optional[Repository] = None,
        focus_duration: int = DEFAULT_FOCUS_DURATION,
        short_break_duration: int = DEFAULT_SHORT_BREAK,
        long_break_duration: int = DEFAULT_LONG_BREAK,
        long_break_interval: int = DEFAULT_LONG_BREAK_INTERVAL,
        auto_start_breaks: bool = True,
        auto_start_focus: bool = False,
    ):
        self.repo = repository
        self.focus_duration = focus_duration
        self.short_break_duration = short_break_duration
        self.long_break_duration = long_break_duration
        self.long_break_interval = long_break_interval
        self.auto_start_breaks = auto_start_breaks
        self.auto_start_focus = auto_start_focus

        self.state = TimerState.IDLE
        self.active_task_id: Optional[str] = None
        self.completed_cycles_today: int = 0

        # Timing variables
        self.total_duration: int = self.focus_duration
        self.remaining_seconds: int = self.focus_duration
        self._target_monotonic: float = 0.0
        self._session_start_wall: Optional[datetime] = None
        self._elapsed_in_session: int = 0

        # Observers / Callbacks
        self._on_tick_callbacks: List[Callable[[int, int, float], None]] = []
        self._on_state_changed_callbacks: List[Callable[[TimerState], None]] = []
        self._on_completed_callbacks: List[Callable[[TimerState, Optional[str]], None]] = []

    # -------------------------------------------------------------------------
    # Callback Registration
    # -------------------------------------------------------------------------
    def subscribe_tick(self, cb: Callable[[int, int, float], None]):
        """Callback signature: cb(remaining_seconds, total_duration, progress_fraction)"""
        self._on_tick_callbacks.append(cb)

    def subscribe_state_changed(self, cb: Callable[[TimerState], None]):
        """Callback signature: cb(new_state)"""
        self._on_state_changed_callbacks.append(cb)

    def subscribe_completed(self, cb: Callable[[TimerState, Optional[str]], None]):
        """Callback signature: cb(completed_state, task_id)"""
        self._on_completed_callbacks.append(cb)

    def _notify_tick(self):
        fraction = 1.0 - (self.remaining_seconds / max(1, self.total_duration))
        progress = max(0.0, min(1.0, fraction))
        for cb in self._on_tick_callbacks:
            try:
                cb(self.remaining_seconds, self.total_duration, progress)
            except Exception as e:
                logger.error("Error in tick callback: %s", e)

    def _set_state(self, new_state: TimerState):
        if self.state != new_state:
            self.state = new_state
            for cb in self._on_state_changed_callbacks:
                try:
                    cb(new_state)
                except Exception as e:
                    logger.error("Error in state_changed callback: %s", e)

    # -------------------------------------------------------------------------
    # Timer Controls
    # -------------------------------------------------------------------------
    def start(self, task_id: Optional[str] = None):
        """Start a focus session or resume."""
        if self.state == TimerState.IDLE:
            if task_id is not None:
                self.active_task_id = task_id
            self.total_duration = self.focus_duration
            self.remaining_seconds = self.focus_duration
            self._session_start_wall = datetime.now()
            self._target_monotonic = time.monotonic() + self.remaining_seconds
            self._elapsed_in_session = 0
            self._set_state(TimerState.RUNNING_FOCUS)
            self._notify_tick()
        elif self.state.is_paused:
            self.resume()

    def pause(self):
        """Pause the running timer."""
        if not self.state.is_running:
            return

        # Calculate exact remaining seconds before pausing
        now_mono = time.monotonic()
        self.remaining_seconds = max(0, int(math.ceil(self._target_monotonic - now_mono)))
        self._elapsed_in_session = self.total_duration - self.remaining_seconds

        if self.state == TimerState.RUNNING_FOCUS:
            self._set_state(TimerState.PAUSED_FOCUS)
        elif self.state == TimerState.RUNNING_SHORT_BREAK:
            self._set_state(TimerState.PAUSED_SHORT_BREAK)
        elif self.state == TimerState.RUNNING_LONG_BREAK:
            self._set_state(TimerState.PAUSED_LONG_BREAK)

        self._notify_tick()

    def resume(self):
        """Resume a paused timer without drift."""
        if not self.state.is_paused:
            return

        self._target_monotonic = time.monotonic() + self.remaining_seconds

        if self.state == TimerState.PAUSED_FOCUS:
            self._set_state(TimerState.RUNNING_FOCUS)
        elif self.state == TimerState.PAUSED_SHORT_BREAK:
            self._set_state(TimerState.RUNNING_SHORT_BREAK)
        elif self.state == TimerState.PAUSED_LONG_BREAK:
            self._set_state(TimerState.RUNNING_LONG_BREAK)

        self._notify_tick()

    def toggle_play_pause(self):
        """Convenience method to toggle play/pause."""
        if self.state.is_running:
            self.pause()
        elif self.state.is_paused:
            self.resume()
        elif self.state == TimerState.IDLE:
            self.start()

    def stop(self, save_interrupted: bool = True):
        """Stop current session and reset to idle."""
        if self.state == TimerState.IDLE:
            return

        prev_state = self.state
        # Record session if it was focus and had significant duration (> 15 seconds)
        if save_interrupted and prev_state.is_focus and self._session_start_wall:
            elapsed = self.total_duration - self.remaining_seconds
            if elapsed >= 15 and self.repo:
                now_wall = datetime.now()
                self.repo.record_session(
                    task_id=self.active_task_id,
                    session_type="focus",
                    start_time=self._session_start_wall.isoformat(),
                    end_time=now_wall.isoformat(),
                    duration_seconds=elapsed,
                    status="interrupted",
                )

        self.remaining_seconds = self.focus_duration
        self.total_duration = self.focus_duration
        self._session_start_wall = None
        self._elapsed_in_session = 0
        self._set_state(TimerState.IDLE)
        self._notify_tick()

    def restart(self):
        """Restart current session from beginning."""
        if self.state.is_focus:
            self.total_duration = self.focus_duration
            self.remaining_seconds = self.focus_duration
            self._session_start_wall = datetime.now()
            self._target_monotonic = time.monotonic() + self.remaining_seconds
            self._set_state(TimerState.RUNNING_FOCUS)
        elif self.state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK):
            self.total_duration = self.short_break_duration
            self.remaining_seconds = self.short_break_duration
            self._session_start_wall = datetime.now()
            self._target_monotonic = time.monotonic() + self.remaining_seconds
            self._set_state(TimerState.RUNNING_SHORT_BREAK)
        elif self.state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
            self.total_duration = self.long_break_duration
            self.remaining_seconds = self.long_break_duration
            self._session_start_wall = datetime.now()
            self._target_monotonic = time.monotonic() + self.remaining_seconds
            self._set_state(TimerState.RUNNING_LONG_BREAK)
        else:
            self.start()
        self._notify_tick()

    def skip(self):
        """Skip current session to the next phase in the cycle."""
        if self.state.is_focus:
            self._transition_to_break()
        elif self.state.is_break:
            self._transition_to_focus()
        else:
            self.start()

    # -------------------------------------------------------------------------
    # Tick Update (Called once per second by UI/Timer thread)
    # -------------------------------------------------------------------------
    def tick(self):
        """
        Calculates exact remaining time from target monotonic clock.
        Ensures drift-free accuracy across sleep/delays.
        """
        if not self.state.is_running:
            return

        now_mono = time.monotonic()
        remaining = int(math.ceil(self._target_monotonic - now_mono))

        if remaining <= 0:
            self.remaining_seconds = 0
            self._notify_tick()
            self._handle_completed()
        else:
            self.remaining_seconds = remaining
            self._notify_tick()

    def _handle_completed(self):
        """Handles expiration of a timer session."""
        finished_state = self.state
        finished_task_id = self.active_task_id

        if finished_state == TimerState.RUNNING_FOCUS:
            self.completed_cycles_today += 1
            if self._session_start_wall and self.repo:
                now_wall = datetime.now()
                self.repo.record_session(
                    task_id=self.active_task_id,
                    session_type="focus",
                    start_time=self._session_start_wall.isoformat(),
                    end_time=now_wall.isoformat(),
                    duration_seconds=self.total_duration,
                    status="completed",
                )

            # Fire completion callbacks
            for cb in self._on_completed_callbacks:
                try:
                    cb(finished_state, finished_task_id)
                except Exception as e:
                    logger.error("Error in completed callback: %s", e)

            # Move to break
            self._transition_to_break()

        elif finished_state in (TimerState.RUNNING_SHORT_BREAK, TimerState.RUNNING_LONG_BREAK):
            break_type = "short_break" if finished_state == TimerState.RUNNING_SHORT_BREAK else "long_break"
            if self._session_start_wall and self.repo:
                now_wall = datetime.now()
                self.repo.record_session(
                    task_id=None,
                    session_type=break_type,
                    start_time=self._session_start_wall.isoformat(),
                    end_time=now_wall.isoformat(),
                    duration_seconds=self.total_duration,
                    status="completed",
                )

            # Fire completion callbacks
            for cb in self._on_completed_callbacks:
                try:
                    cb(finished_state, None)
                except Exception as e:
                    logger.error("Error in completed callback: %s", e)

            # Move to focus
            self._transition_to_focus()

    def _transition_to_break(self):
        """Determine whether short break or long break and set state."""
        is_long = (self.completed_cycles_today % self.long_break_interval == 0) and (self.completed_cycles_today > 0)
        dur = self.long_break_duration if is_long else self.short_break_duration
        target_state = TimerState.RUNNING_LONG_BREAK if is_long else TimerState.RUNNING_SHORT_BREAK
        paused_state = TimerState.PAUSED_LONG_BREAK if is_long else TimerState.PAUSED_SHORT_BREAK

        self.total_duration = dur
        self.remaining_seconds = dur
        self._session_start_wall = datetime.now()
        self._target_monotonic = time.monotonic() + dur

        if self.auto_start_breaks:
            self._set_state(target_state)
        else:
            self._set_state(paused_state)

        self._notify_tick()

    def _transition_to_focus(self):
        """Transition from break to focus."""
        self.total_duration = self.focus_duration
        self.remaining_seconds = self.focus_duration
        self._session_start_wall = datetime.now()
        self._target_monotonic = time.monotonic() + self.focus_duration

        if self.auto_start_focus:
            self._set_state(TimerState.RUNNING_FOCUS)
        else:
            self._set_state(TimerState.PAUSED_FOCUS)

        self._notify_tick()

    def set_active_task(self, task_id: Optional[str]):
        """Set the active task for the upcoming or running focus session."""
        self.active_task_id = task_id

    def update_durations(
        self,
        focus_duration: Optional[int] = None,
        short_break: Optional[int] = None,
        long_break: Optional[int] = None,
        interval: Optional[int] = None,
    ):
        """Update durations from settings."""
        if focus_duration is not None:
            self.focus_duration = focus_duration
        if short_break is not None:
            self.short_break_duration = short_break
        if long_break is not None:
            self.long_break_duration = long_break
        if interval is not None:
            self.long_break_interval = interval

        # If currently idle, reset remaining seconds to new focus duration
        if self.state == TimerState.IDLE:
            self.total_duration = self.focus_duration
            self.remaining_seconds = self.focus_duration
            self._notify_tick()

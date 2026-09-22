# Development Log: FocusFlow

This document tracks the chronological engineering progress, completed milestones, git commits, architectural decisions, and testing milestones of **FocusFlow** — a native Linux Pomodoro, Todo, and Productivity Tracker application.

---

## Milestone 1: Project Initialization & Repository Setup

### Date: 2026-09-22

### Completed
- Selected technology stack: Python 3.13 + PyQt6 + SQLite (ideal for Linux desktop integration, native Freedesktop system tray, multi-monitor floating always-on-top window, low RAM ~40MB, and Debian packaging).
- Initialized project directory structure:
  - `focusflow/` (core engine, database persistence, modern UI views, components, system utilities)
  - `tests/` (unit testing suite)
  - `packaging/debian/` (Debian packaging specifications)
  - `assets/` (scalable app logo and notification audio)
- Created `.gitignore` ignoring virtual environments, test caches, local SQLite databases, and packaging build artifacts.
- Created `LICENSE` (MIT).
- Designed vector application icon `assets/focusflow.svg`.
- Synthesized soft dual-tone notification chime `assets/chime.wav` using harmonic wave synthesis.

### Git Commits
- `chore: initialize project structure, assets, and git development tracking`

### Next Planned Milestone
- Implement SQLite persistence layer with schema migrations (`focusflow/db/`).

---

## Milestone 2: SQLite Database & Schema Migrations

### Date: 2026-09-22

### Completed
- Implemented `focusflow/db/schema.py`:
  - Defined initial schema v1 with version tracking table `schema_migrations`.
  - Tables: `tasks`, `pomodoro_sessions`, `daily_statistics`, `application_usage`, `preferences`.
  - Created composite indexes on status, due date, priority, date, and task relationships.
- Implemented `focusflow/db/database.py`:
  - WAL journal mode, PRAGMA foreign keys, and synchronous NORMAL.
  - Thread-safe local connection management with re-entrant transactions.
  - Automatic `PRAGMA integrity_check` on open with backup/recovery for corrupt DB files.
- Implemented `focusflow/db/repository.py`:
  - Typed dataclasses: `Task`, `PomodoroSession`, `DailyStats`.
  - Complete Task CRUD operations with multi-criteria filtering and flexible sorting.
  - Session recording with automatic daily rollups and task pomodoro increments.
  - Streak computation, time distribution analysis (Morning, Afternoon, Evening).
  - Key-value preferences store with default fallback mapping.
- Added comprehensive unit tests in `tests/test_database.py` (4/4 tests passing).

### Git Commits
- `feat(db): implement SQLite persistence layer with schema migrations`

### Next Planned Milestone
- Implement drift-free Pomodoro timer engine (`focusflow/core/timer.py`).

---

## Milestone 3: Drift-Free Pomodoro Timer Engine

### Date: 2026-09-22

### Completed
- Implemented `focusflow/core/timer.py`:
  - Defined explicit states via `TimerState` enum (`IDLE`, `RUNNING_FOCUS`, `PAUSED_FOCUS`, `RUNNING_SHORT_BREAK`, `PAUSED_SHORT_BREAK`, `RUNNING_LONG_BREAK`, `PAUSED_LONG_BREAK`).
  - Implemented drift-free monotonic clock arithmetic (`time.monotonic()` target timestamps) with zero cumulative drift even across system sleep or thread stalls.
  - Implemented controls: `start()`, `pause()`, `resume()`, `toggle_play_pause()`, `stop()`, `restart()`, and `skip()`.
  - Automatic session logging with interruption detection (> 15s recorded as interrupted on manual stop).
  - Configurable cycle transitions: auto-start breaks, long break triggering every N cycles, and task pomodoro increments.
  - Event observer pattern for tick updates, state changes, and session completions.
- Created `tests/test_timer.py` covering state transitions, break cycles, pause/resume, and clock drift resilience (5/5 tests passing).

### Git Commits
- `feat(timer): implement drift-free pomodoro timer engine with session recovery`

### Next Planned Milestone
- Implement Task Manager service and validation (`focusflow/core/task_manager.py`).

---

## Milestone 4: Persistent Task Management System

### Date: 2026-09-22

### Completed
- Implemented `focusflow/core/task_manager.py`:
  - Validated task attributes: title presence, priority (`low`, `medium`, `high`), ISO-8601 date parsing.
  - CRUD operations and completion toggling with automatic completion timestamp management.
  - Multi-mode filtering: All, Today, Upcoming, Completed, and High Priority.
  - Sorting support: Created date (desc/asc), due date, priority, and remaining pomodoros.
  - Aggregate tag discovery across all tasks.
  - Observer subscriber pattern to automatically synchronize UI elements when tasks mutate.
- Created `tests/test_tasks.py` verifying validation, completion toggles, tag aggregation, and filtered queries (4/4 tests passing).

### Git Commits
- `feat(tasks): implement persistent task management system`

### Next Planned Milestone
- Implement Linux Desktop Notifications, Audio Chime Player, and System Tray (`focusflow/ui/notifications.py`, `focusflow/utils/sound.py`, `focusflow/ui/tray.py`).

---

## Milestone 5: Desktop Notifications, Audio Chime & System Tray

### Date: 2026-09-22

### Completed
- Implemented `focusflow/utils/sound.py`:
  - Multi-backend non-blocking sound player with automatic detection of `pw-play` (PipeWire), `paplay` (PulseAudio), and `aplay` (ALSA).
  - Background worker thread to prevent UI micro-stutters during sound playback.
- Implemented `focusflow/ui/notifications.py`:
  - DBus native integration via `org.freedesktop.Notifications`.
  - Seamless fallback to `notify-send` with custom application icon and urgency levels.
  - Predefined notification triggers: Pomodoro complete, Break started, Break finished, and Daily goal reached.
- Implemented `focusflow/ui/tray.py`:
  - `QSystemTrayIcon` integrated with desktop environments (Plasma, GNOME, XFCE).
  - Dynamic context menu displaying active task, live countdown timer, and session state.
  - Interactive controls: Start/Pause/Resume, Stop, Toggle Floating Timer, Open Dashboard, Settings, and Quit.
- Verified offscreen instantiation and signal routing.

### Git Commits
- `feat(tray): implement system tray integration, audio alerts, and desktop notifications`

### Next Planned Milestone
- Implement Modern Linux Desktop UI, Styles, and Productivity Dashboard (`focusflow/ui/`).

---

## Milestone 6: Modern Linux Desktop UI & Productivity Dashboard

### Date: 2026-09-22

### Completed
- Implemented `focusflow/ui/styles.py`:
  - Native Linux dark and light themes (GNOME Adwaita & KDE Breeze inspired color tokens).
  - Modern typography, rounded cards, subtle border contrasts, accessible status indicators.
- Implemented `focusflow/ui/components/timer_display.py`:
  - Antialiased `QPainter` circular progress ring with gradient fills.
  - State-aware badge pills (`FOCUS`, `SHORT BREAK`, `LONG BREAK`, `PAUSED`).
  - Crisp typography scaling dynamically with window size.
- Implemented `focusflow/ui/dashboard_view.py`:
  - Real-time productivity metrics: Today's Focused Time, Completed Pomodoros, Remaining Tasks, Daily Streak.
  - Active task selector dropdown linked to Pomodoro sessions.
  - Responsive action controls: Start/Pause, Stop, Skip, and Restart.
- Implemented `focusflow/ui/tasks_view.py`:
  - Full task management interface with filter pills (All, Today, Upcoming, High Priority, Completed).
  - Search bar and sorting by newest, oldest, priority, due date, and remaining pomodoros.
  - Rich task cards with completion checkbox, priority color badges, pomodoro progress (`🍅 3/5`), due dates, and tags.
  - Interactive Add/Edit Task modal dialog with validation.
  - Direct "Focus" action button to bind any task instantly to the active timer.
- Implemented `focusflow/ui/main_window.py`:
  - Sidebar navigation host with `QStackedWidget`.
  - Keyboard shortcuts: `Ctrl+Alt+Space` (play/pause), `Ctrl+Alt+S` (stop), `Ctrl+Alt+F` (floating timer), `Ctrl+Alt+N` (new task).
  - Graceful minimize-to-tray on close when timer is running.

### Git Commits
- `feat(ui): implement modern Linux desktop dashboard and task manager UI`

### Next Planned Milestone
- Implement Always-On-Top Draggable Floating Timer Widget (`focusflow/ui/floating_timer.py`).

---

## Milestone 7: Always-On-Top Draggable Floating Timer Widget

### Date: 2026-09-22

### Completed
- Implemented `focusflow/ui/floating_timer.py`:
  - Utilized `WindowStaysOnTopHint | FramelessWindowHint | Tool` for distraction-free floating over all Linux desktop windows.
  - Smooth mouse drag-to-move across monitors with persistence of window coordinates (`floating_x`, `floating_y`).
  - Dynamic opacity control (from 50% to 100% translucent background).
  - Compact micro-widget mode toggle (`150x68` minimal bar vs `220x140` standard card).
  - Live state badges, active task name clipping, and direct Play/Pause/Stop/Skip actions.
  - Multi-window signal synchronization with `MainWindow` and `SystemTrayManager`.

### Git Commits
- `feat(floating): create always-on-top draggable floating timer widget`

### Next Planned Milestone
- Implement Productivity Statistics, Charts, and Analytics (`focusflow/ui/components/charts.py`, `focusflow/ui/stats_view.py`).

---

## Milestone 8: Productivity Statistics, Analytics & Visual Charts

### Date: 2026-09-22

### Completed
- Implemented `focusflow/ui/components/charts.py`:
  - `WeeklyBarChart`: antialiased `QPainter` 7-day vector bar chart with dynamic scaling, rounded bars, values, and weekday labels.
  - `TimeDistributionBar`: tri-color stacked progress bar for Morning, Afternoon, and Evening focus breakdown with an interactive legend.
- Implemented `focusflow/ui/stats_view.py`:
  - Period switcher (Last 7 Days vs Last 30 Days).
  - Metric summary cards: Total Focus Time, Completed Pomodoros, Tasks Completed, and Daily Average.
  - Productivity Insights section showing most productive day, longest single focus block, and total interruption count.
- Created `tests/test_statistics.py` verifying date range zero-filling and time-of-day bucketing (2/2 tests passing).

### Git Commits
- `feat(stats): add daily, weekly, and monthly productivity visual analytics`

### Next Planned Milestone
- Implement Settings, Autostart, Reminders & First-Run Wizard (`focusflow/ui/settings_view.py`, `focusflow/ui/wizard.py`, `focusflow/utils/autostart.py`, `focusflow/core/reminders.py`).

---

## Milestone 9: Settings, Autostart, Reminders & First-Run Wizard

### Date: 2026-09-22

### Completed
- Implemented `focusflow/utils/autostart.py`:
  - Standard XDG autostart file generation at `~/.config/autostart/focusflow.desktop`.
  - Detection, enabling, and disabling routines for seamless user login launching.
- Implemented `focusflow/core/reminders.py`:
  - Periodic goal tracking service verifying daily focus hours and triggering notifications on goal achievement.
- Implemented `focusflow/ui/wizard.py`:
  - 4-step onboarding wizard for first launches: Welcome, Pomodoro duration selector, daily focus goal configuration, and autostart toggle.
  - No account creation or cloud requirement.
- Implemented `focusflow/ui/settings_view.py`:
  - Comprehensive configuration tabs: Timer durations (focus, short break, long break, intervals), auto-start toggles, notification/sound preferences with test buttons, theme switching (Dark/Light), daily targets, and floating timer behavior.
  - Direct parameter synchronization with `PomodoroEngine`.

### Git Commits
- `feat(settings): add comprehensive settings, autostart, and first-run wizard`

### Next Planned Milestone
- Implement Privacy-Safe Idle Detection & Session Tracking (`focusflow/core/tracker.py`).

---

## Milestone 10: Privacy-Safe Idle Detection & Tracking

### Date: 2026-09-22

### Completed
- Implemented `focusflow/core/tracker.py`:
  - Non-invasive user inactivity detection using Linux `libX11` / `libXss.so.1` (`XScreenSaverQueryInfo`) and Freedesktop DBus ScreenSaver fallback.
  - Zero surveillance: no keylogging, no screenshotting, no browser monitoring, and no clipboard snooping.
  - Configurable inactivity threshold and action handler (`pause`, `ask`, `continue`).
  - Graceful tolerance for missing display or sandboxed permissions.
- Created `tests/test_idle_detector.py` validating automated pause behavior on inactivity threshold breaches (2/2 tests passing).

### Git Commits
- `feat(tracking): implement privacy-focused idle and session tracking`

### Next Planned Milestone
- Implement CSV & JSON Data Export / Import and Database Backup (`focusflow/utils/export_import.py`).

---

## Milestone 11: Data Export, Import & Backup

### Date: 2026-09-22

### Completed
- Implemented `focusflow/utils/export_import.py`:
  - CSV export for recorded Pomodoro sessions (`focus_sessions.csv`) with task metadata and duration.
  - CSV export for all tasks (`tasks.csv`) with status, priorities, tags, and progress metrics.
  - Complete JSON backup and restore with deduplication on task and session UUIDs.
  - Local database snapshot backup utility (`focusflow_backup_YYYYMMDD_HHMMSS.db`).
- Created `tests/test_export_import.py` validating full JSON round-trip serialization and database backup generation (2/2 tests passing).

### Git Commits
- `feat(data): implement CSV and JSON export, import, and backup utilities`

### Next Planned Milestone
- Implement Main Application Orchestrator and Comprehensive Verification (`focusflow/app.py`, `run.py`).

---

## Milestone 12: Main Application Orchestrator & Multi-Window Coordination

### Date: 2026-09-22

### Completed
- Implemented `focusflow/app.py`:
  - Centralized application coordinator tying database, domain engines, desktop views, floating widget, tray, sound player, and notifications.
  - Heartbeat timer (1000ms QTimer) driving drift-free timer engine ticks, inactivity checks, and daily goal reminders.
  - Signal wiring between main window, floating timer, system tray, and notification dispatcher.
  - First-run wizard trigger for initial launches.
  - Command-line arguments: `--version`, `--minimized`, `--floating-only`, `--test-mode`, `--db-path`.
- Implemented `run.py`: executable CLI launcher.
- Implemented `setup.py`: standard Python package distribution configuration.
- Executed comprehensive unit test suite: 19/19 tests passing across database, tasks, timer drift, statistics, idle detector, and export/import.

### Git Commits
- `feat(app): implement application orchestrator, launcher, and full signal wiring`

### Next Planned Milestone
- Implement Debian Packaging (.deb) and Desktop Integration (`packaging/debian/`, `build_deb.sh`).

---

## Milestone 13: Debian Packaging (.deb) & System Integration

### Date: 2026-09-22

### Completed
- Created Debian package specifications:
  - `packaging/debian/control`: declared dependencies (`python3`, `python3-pyqt6`, `python3-dbus`, recommended audio utilities).
  - `packaging/debian/copyright`: machine-readable DEP-5 copyright specification.
  - `packaging/debian/changelog`: debian changelog for v0.1.0-1.
  - `packaging/focusflow.desktop`: standard XDG desktop entry with actions for floating-only and minimized start.
- Implemented `packaging/build_deb.sh`:
  - Builds canonical staging layout: `/usr/bin/focusflow`, `/usr/lib/focusflow/`, `/usr/share/applications/`, `/usr/share/icons/hicolor/scalable/apps/focusflow.svg`.
  - Configured `postinst` hook for `update-desktop-database` and `gtk-update-icon-cache`.
  - Successfully generated and validated `packaging/dist/focusflow_0.1.0-1_all.deb` using `dpkg-deb`.

### Git Commits
- `build(packaging): add Debian package generation and desktop integration`

### Next Planned Milestone
- Complete comprehensive README.md, documentation, tag v0.1.0 release, and guide remote GitHub push.

---

## Milestone 14: Release v0.1.0, Documentation & Final Verification

### Date: 2026-09-22

### Completed
- Completed comprehensive `README.md`:
  - Complete feature tour with badge details.
  - In-depth architectural evaluation explaining why PyQt6 was selected over GTK4 for native Linux floating widgets and system tray integration.
  - Complete directory tree and responsibility breakdown.
  - Installation instructions via Debian `.deb` package (`sudo dpkg -i ...`) and source checkout.
  - Keyboard shortcuts table.
  - Automated test execution commands and results (19/19 passing).
  - Explicit privacy statement and roadmap.
- Validated Debian package generation via `packaging/build_deb.sh`, producing `packaging/dist/focusflow_0.1.0-1_all.deb`.
- Verified headless execution with `python3 run.py --test-mode`.
- Ready for git tag `v0.1.0`.

### Git Commits
- `docs: complete user guide, packaging instructions, and release v0.1.0`

### Status
- **MVP Complete & Verified**: FocusFlow is ready for local production use and Debian/Parrot/Ubuntu deployment.

---

# FocusFlow v0.2.0: Daily-Driver Hardening

## Milestone 15: GitHub Actions CI Workflows

### Date: 2026-09-22

### Completed
- Implemented `.github/workflows/tests.yml`:
  - Multi-version matrix test workflow (Python 3.10, 3.11, 3.12, 3.13).
  - Installs system GUI/X11 and DBus libraries.
  - Executes unit test discovery in headless `offscreen` mode.
  - Executes `--test-mode` application initialization sanity test.
- Implemented `.github/workflows/build.yml`:
  - Automated Debian `.deb` package build verification.
  - Validates package metadata and debian file layout via `dpkg-deb`.

### Git Commits
- `ci: add GitHub Actions test and Debian build workflows`

### Next Planned Milestone
- Audit and harden Pomodoro timer engine with active state recovery, sleep/suspend detection, and pause isolation.

---

## Milestone 16: Timer Reliability Audit & Crash/Suspend Recovery

### Date: 2026-09-22

### Completed
- Hardened `focusflow/core/timer.py`:
  - Monotonic & wall-clock synchronization: accurately tracks true elapsed time without drift.
  - Suspend/sleep detection: detects discrepancies between wall clock (`datetime.now()`) and `time.monotonic()` exceeding 5 seconds, auto-pausing the timer so asleep hours are never misattributed as focus time.
  - Pause isolation: verified paused durations are fully excluded from focus time calculations.
  - State persistence & crash recovery: saves running/paused session state to SQLite (`persisted_timer_state`) and seamlessly restores active/paused timers upon application reboot.
- Enhanced `tests/test_timer.py`:
  - Added test cases for normal countdown, UI freeze recovery, pause isolation, suspend detection, and crash/restart recovery (9/9 tests passing).

### Git Commits
- `feat(timer): harden timer engine with wall-clock state recovery and suspend resilience`

### Next Planned Milestone
- Enhance Floating Timer with right-click context menu, auto-hide controls, and task switching.

---

## Milestone 17: Floating Timer Context Menu, Auto-Hide Controls & Task Switcher

### Date: 2026-09-22

### Completed
- Enhanced `focusflow/ui/floating_timer.py`:
  - Implemented rich right-click context menu (`contextMenuEvent`) with actions for Start/Pause/Resume, Stop, Skip, Show Dashboard, Task selection submenu, Compact Mode toggle, Opacity presets, Settings, and Quit.
  - Added "Change Task" dynamic submenu allowing instant task binding directly from the floating widget.
  - Implemented "Hide Controls Automatically" option (`floating_auto_hide_controls`): controls and buttons smoothly hide when mouse leaves the widget and appear on hover.
  - Enhanced compact mode transitions with unified controls container.

### Git Commits
- `feat(floating): add context menu, auto-hide controls, and task switching`

### Next Planned Milestone
- Enhance Task ↔ Pomodoro workflow with no-task prompt and reliable counter increments.

---

## Milestone 18: Task ↔ Pomodoro Workflow & No-Task Prompt

### Date: 2026-09-22

### Completed
- Implemented `focusflow/ui/components/no_task_dialog.py`:
  - Interactive prompt when starting a session without an active task.
  - Three distinct options: "Continue without Task" (general focus), "Select an Existing Task" (from pending tasks), or "Create New Task" (instant title entry and focus start).
  - "Don't ask again" option saved in local preferences (`prompt_no_task`).
- Enhanced `focusflow/ui/dashboard_view.py`:
  - Hooked play/pause trigger into `NoTaskDialog` when starting from idle with no task selected.
  - Verified 100% reliable transactional increment of task's `completed_pomodoros` and `total_focus_seconds`.

---

## Milestone 19: Daily Goal Progress Bar & Smart Productivity Insights

### Date: 2026-09-22

### Completed
- Enhanced `focusflow/ui/dashboard_view.py`:
  - Added dedicated Daily Focus Goal card featuring a styled progress bar and live ratio display (`1h 35m / 2.0h (78%)`).
  - Automatically updates when focus sessions complete or durations change.
- Enhanced `focusflow/db/repository.py`:
  - Added `get_longest_streak()` to compute historical record streaks across all recorded daily statistics.
- Enhanced `focusflow/ui/stats_view.py`:
  - Added data-aware productivity insights: Peak focus period (Morning/Afternoon/Evening), average session length, current vs. record streak.
  - Added empty state notice: *"Not enough data yet. Complete your first Pomodoro to start building your productivity history."* when less than 2 sessions exist.

### Git Commits
- `feat(dashboard): add visual daily goal progress, task selection prompt, and smart insights`

### Next Planned Milestone
- Implement Dedicated Session History View with timeline and date filters (`focusflow/ui/history_view.py`).

---

## Milestone 20: Dedicated Session History Timeline View

### Date: 2026-09-22

### Completed
- Implemented `focusflow/ui/history_view.py`:
  - Chronological session timeline grouping records by date (Today, Yesterday, Weekday dates).
  - Detailed cards with start—end timestamps, task association (or General Focus), duration, session type, and status badges (Completed / Interrupted).
  - Flexible date filter pills: *Today, Yesterday, Last 7 Days, Last 30 Days, All Time*.
  - Real-time search bar filtering across task names and session types.
  - Live summary banner calculating total focus time and completed count for the active filter.
- Updated `focusflow/ui/main_window.py`:
  - Added `📜 History` tab to the primary sidebar navigation.
  - Wired real-time automatic refreshes upon session completion.

### Git Commits
- `feat(history): implement session history timeline view with date filters`

### Next Planned Milestone
- Implement Error Logging, Diagnostics Viewer & Rolling Database Backups (`focusflow/config.py`, `focusflow/utils/export_import.py`, `focusflow/ui/settings_view.py`).

---

## Milestone 21: Error Logging, Diagnostics Viewer & Rolling Database Backups

### Date: 2026-09-22

### Completed
- Configured persistent file logging in `focusflow/config.py` and `focusflow/app.py`:
  - `RotatingFileHandler` writing to `~/.local/state/focusflow/focusflow.log` (2MB max size with 3 backups).
- Implemented `LogViewerDialog` in `focusflow/ui/settings_view.py`:
  - Allows users to inspect recent application logs directly within the Settings interface.
- Implemented rolling database snapshots in `focusflow/utils/export_import.py`:
  - `create_rolling_backup(max_backups=5)` creates timestamped snapshots in `~/.local/share/focusflow/backups/` and automatically prunes older backups so at most 5 are retained.
  - Automatic safety snapshot created prior to any JSON backup import.
- Added test in `tests/test_export_import.py` verifying rolling backup creation and pruning.

### Git Commits
- `feat(system): add persistent file logging, diagnostics viewer, and rolling backups`

### Next Planned Milestone
- Implement Inactivity / Idle Return Dialog and Privacy Settings (`focusflow/core/tracker.py`, `focusflow/ui/components/idle_dialog.py`).

---

## Milestone 22: Interactive Inactivity Return Dialog & Privacy Settings

### Date: 2026-09-22

### Completed
- Implemented `focusflow/ui/components/idle_dialog.py`:
  - `IdleReturnDialog` modal prompting the user when returning from system inactivity.
  - Options to keep inactive time as focus, discard inactive time and pause, discard inactive time and resume, or discard the Pomodoro session.
- Enhanced `focusflow/core/tracker.py`:
  - Added `returned_from_idle` signal to `IdleDetector` tracking when user returns after inactivity.
  - Non-invasive detection via `libXss` and DBus ScreenSaver.
- Added `adjust_remaining_time()` method to `PomodoroEngine` in `focusflow/core/timer.py`.
- Added unit test in `tests/test_idle_detector.py` validating idle return signal emission.

### Git Commits
- `feat(idle): add interactive idle recovery dialog and privacy settings`

### Next Planned Milestone
- Implement CLI flags, version bump to 0.2.0, Debian package rebuild, and release verification.

---

## Milestone 23: CLI Control Flags, Version 0.2.0 Bump & Release Verification

### Date: 2026-09-22

### Completed
- Implemented CLI control flags in `focusflow/app.py`:
  - `--start`: Start or resume focus session immediately.
  - `--pause`: Pause running session.
  - `--stop`: Stop active session.
  - `--show`: Raise and focus main application window.
  - `--version`, `--minimized`, `--floating-only`, `--test-mode`.
- Version bump to `0.2.0` across:
  - `focusflow/config.py` (`APP_VERSION = "0.2.0"`)
  - `setup.py` (`version="0.2.0"`)
  - `packaging/debian/control` (`Version: 0.2.0-1`)
  - `packaging/debian/changelog` (`focusflow (0.2.0-1)`)
  - `packaging/build_deb.sh` (`VERSION="0.2.0"`)
- Rebuilt Debian package `packaging/dist/focusflow_0.2.0-1_all.deb` and verified contents.
- Ran all 25 automated unit tests (25/25 passing).
- Verified headless test mode execution (`--test-mode`).

### Git Commits
- `release: v0.2.0 — daily-driver hardening, session history, and CI workflows`

### Status
- **FocusFlow v0.2.0 Released**: All 9 goals fulfilled, fully tested, and ready for daily driver use on Parrot OS / Debian.

---

## Milestone 24: Floating Timer Redesign, Drag Fix, Multi-Monitor Safety & Logging Silence

### Date: 2026-09-22

### Completed
- **Floating Timer UI Cleanup**:
  - Redesigned `focusflow/ui/floating_timer.py` to be smaller (175x110px), cleaner, and minimal.
  - Placed visual focus entirely on the countdown timer (`28px` bold font) with state badge (`FOCUS`) above and active task title (`Study Linux`) below.
  - Subdued, compact control row (`▶/⏸`, `■`, `⋮`) measuring 26x24px without visual dominance.
  - True compact mode (`136x40px`): single horizontal pill showing `[ 24:37  ▶  ⋮ ]`.
- **Drag Interaction Fix**:
  - Identified root cause of unresponsiveness: child labels and nested `QFrame` consumed/intercepted mouse events on frameless windows.
  - Implemented `DraggableFrame(QFrame)` to delegate mouse press, move, and release events directly to the floating window.
  - Set `WA_TransparentForMouseEvents` on timer, state, and task labels so clicks/drags anywhere on text pass seamlessly through to the draggable frame.
  - Verified buttons (`btn_play_pause`, `btn_stop`, `btn_more`) remain interactive and click without dragging.
- **Drag Position Persistence**:
  - Window position is saved only upon `mouseReleaseEvent` rather than continuously on move.
  - Coordinates are stored in SQLite preferences (`floating_x`, `floating_y`) and restored on app relaunch.
- **Multi-Monitor Safety**:
  - Implemented `ensure_on_screen(pos, size)`: verifies widget coordinates against all active `QGuiApplication.screens()`.
  - If saved position falls off-screen (e.g., unplugged external monitor), widget automatically falls back onto the primary screen's available geometry.
- **Auto-Hide Controls on Hover**:
  - When enabled, controls smoothly hide when the mouse leaves the widget and reveal on hover (`enterEvent`/`leaveEvent`).
  - Timer, state, and task label remain permanently visible.
- **Terminal Logging Silence**:
  - Configured console `StreamHandler` to `logging.WARNING` level during standard GUI launches in `focusflow/app.py`.
  - Detailed diagnostic `INFO` logs continue recording into `~/.local/state/focusflow/focusflow.log` for in-app viewer inspection.
  - CLI control commands (`--start`, `--pause`, `--stop`) output clean single-line feedback to stdout.
- **Testing & Verification**:
  - Added `tests/test_floating_timer.py` covering position persistence, off-screen multi-monitor fallback, compact mode, and auto-hide controls (5 new unit tests, 30/30 tests passing).
  - Executed GUI drag simulation verifying center drag, timer text drag, task text drag, button click isolation, and position restore across restarts.

### Git Commits
- `fix(logging): silence normal GUI stdout output`
- `fix(floating): clean up widget and restore drag interaction`



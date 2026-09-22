"""
Database Schema and Migrations for FocusFlow.
Defines tables, indices, and versioned migrations.
"""

INITIAL_SCHEMA_V1 = """
-- Schema Migrations Tracker
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
);

-- Preferences Key-Value Store
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    due_date TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    estimated_pomodoros INTEGER NOT NULL DEFAULT 1,
    completed_pomodoros INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '',
    total_focus_seconds INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

-- Pomodoro Sessions Table
CREATE TABLE IF NOT EXISTS pomodoro_sessions (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    session_type TEXT NOT NULL DEFAULT 'focus',
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    date TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON pomodoro_sessions(date);
CREATE INDEX IF NOT EXISTS idx_sessions_task_id ON pomodoro_sessions(task_id);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON pomodoro_sessions(session_type);

-- Daily Aggregated Statistics
CREATE TABLE IF NOT EXISTS daily_statistics (
    date TEXT PRIMARY KEY,
    total_focus_seconds INTEGER NOT NULL DEFAULT 0,
    pomodoros_completed INTEGER NOT NULL DEFAULT 0,
    tasks_completed INTEGER NOT NULL DEFAULT 0,
    longest_session_seconds INTEGER NOT NULL DEFAULT 0,
    interruptions_count INTEGER NOT NULL DEFAULT 0
);

-- Optional Privacy-Safe Application Usage Tracking
CREATE TABLE IF NOT EXISTS application_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    app_name TEXT NOT NULL,
    window_title TEXT DEFAULT '',
    duration_seconds INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_app_usage_date ON application_usage(date);
"""

# Dictionary of migrations (version: (description, sql_commands))
MIGRATIONS = {
    1: (
        "Initial FocusFlow schema with tasks, sessions, statistics, and preferences",
        INITIAL_SCHEMA_V1,
    ),
}

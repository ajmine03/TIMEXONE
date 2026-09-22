"""
Database connection manager and migration runner for FocusFlow.
Ensures thread safety, foreign key constraints, WAL journaling, and recovery.
"""

import sqlite3
import shutil
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from focusflow.config import DEFAULT_DB_PATH
from focusflow.db.schema import MIGRATIONS

logger = logging.getLogger(__name__)


class Database:
    """Thread-safe SQLite database manager with WAL and migrations."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local SQLite connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=20.0,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # Enable Foreign Keys & WAL mode for speed and reliability
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            self._local.connection = conn
        return self._local.connection

    @property
    def connection(self) -> sqlite3.Connection:
        return self._get_connection()

    def close(self):
        """Close the thread-local connection."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
            except Exception:
                pass
            self._local.connection = None

    def _check_integrity(self) -> bool:
        """Run PRAGMA integrity_check on the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            rows = cursor.fetchall()
            return len(rows) == 1 and rows[0][0] == "ok"
        except Exception as e:
            logger.error("Integrity check failed with error: %s", e)
            return False

    def _init_database(self):
        """Initialize database file, recover if corrupt, and run migrations."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if self.db_path.exists() and not self._check_integrity():
            logger.warning("Database corrupted! Backing up and re-initializing...")
            backup_path = self.db_path.with_suffix(
                f".corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            )
            self.close()
            shutil.move(str(self.db_path), str(backup_path))
            logger.info("Corrupted database moved to %s", backup_path)

        self._run_migrations()

    def _run_migrations(self):
        """Run any pending migrations within a transaction."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                # Ensure migration tracker table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL,
                        description TEXT NOT NULL
                    );
                """)

                # Fetch applied migrations
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
                applied = {row[0] for row in cursor.fetchall()}

                for version in sorted(MIGRATIONS.keys()):
                    if version not in applied:
                        description, sql_script = MIGRATIONS[version]
                        logger.info("Applying migration %d: %s", version, description)
                        conn.executescript(sql_script)
                        conn.execute(
                            "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?);",
                            (version, datetime.now().isoformat(), description)
                        )

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return the cursor."""
        conn = self._get_connection()
        return conn.execute(query, params)

    def executemany(self, query: str, seq_of_params) -> sqlite3.Cursor:
        """Execute many queries."""
        conn = self._get_connection()
        return conn.executemany(query, seq_of_params)

    def commit(self):
        """Commit current transaction."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.commit()

    def rollback(self):
        """Rollback current transaction."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.rollback()

    def transaction(self):
        """Context manager for explicit transactions."""
        conn = self._get_connection()
        return conn

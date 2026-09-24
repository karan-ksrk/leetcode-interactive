"""Database layer for LeetCode Interactive generator."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import json

from .models import Problem, Batch, GenerationJob, InvalidTransitionError, VALID_TRANSITIONS

DEFAULT_DB_PATH = Path("database/leetcode.db")


def get_connection(db_path=DEFAULT_DB_PATH):
    """Get a SQLite connection with optimized settings for concurrent writes."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db_path),
        timeout=30,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=OFF;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


class Database:
    """Database wrapper providing typed, thread-safe access to problem/batch/job state."""

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.conn = get_connection(db_path)

    @contextmanager
    def transaction(self):
        """Context manager for ACID transactions."""
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        """Close the connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def init_db(conn):
    """Initialize or verify database schema. Idempotent."""
    cursor = conn.cursor()

    # Schema version table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            migrated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Problems table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            leetcode_id INTEGER UNIQUE NOT NULL,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,

            difficulty TEXT NOT NULL,
            url TEXT NOT NULL,

            topics_json TEXT,

            html_file TEXT,

            status TEXT NOT NULL DEFAULT 'pending',

            generation_model TEXT,
            generation_agent TEXT,

            generation_attempts INTEGER DEFAULT 0,

            generation_started_at TEXT,
            generation_completed_at TEXT,

            generation_duration_seconds REAL,

            validation_passed INTEGER,

            last_error TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Batches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            batch_number INTEGER,

            difficulty TEXT NOT NULL,

            requested_count INTEGER NOT NULL,

            selected_count INTEGER DEFAULT 0,

            generated_count INTEGER DEFAULT 0,

            skipped_count INTEGER DEFAULT 0,

            failed_count INTEGER DEFAULT 0,

            status TEXT DEFAULT 'pending',

            started_at TEXT,
            completed_at TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Generation jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            batch_id INTEGER,

            problem_id INTEGER,

            status TEXT DEFAULT 'pending',

            agent TEXT,
            model TEXT,

            started_at TEXT,
            completed_at TEXT,

            duration_seconds REAL,

            error TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(batch_id) REFERENCES batches(id),
            FOREIGN KEY(problem_id) REFERENCES problems(id)
        )
    """)

    # Create indices
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON problems(difficulty)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_problems_leetcode_id ON problems(leetcode_id)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_jobs_batch_id ON generation_jobs(batch_id)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_jobs_problem_id ON generation_jobs(problem_id)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_jobs_status ON generation_jobs(status)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status)""")

    conn.commit()


def validate_transition(from_status: str, to_status: str):
    """Validate that a status transition is allowed."""
    if from_status not in VALID_TRANSITIONS:
        raise InvalidTransitionError(f"Unknown status: {from_status}")
    if to_status not in VALID_TRANSITIONS.get(from_status, set()):
        raise InvalidTransitionError(
            f"Invalid transition: {from_status} -> {to_status}"
        )


def get_problem_by_id(conn, leetcode_id: int) -> Optional[Problem]:
    """Get a problem by LeetCode ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM problems WHERE leetcode_id = ?", (leetcode_id,))
    row = cursor.fetchone()
    return Problem.from_row(row) if row else None


def get_problem_by_slug(conn, slug: str) -> Optional[Problem]:
    """Get a problem by slug."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM problems WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    return Problem.from_row(row) if row else None


def upsert_problem(conn, problem: Problem) -> int:
    """Insert or update a problem, return its DB ID."""
    cursor = conn.cursor()
    row_data = problem.to_row()

    cursor.execute("""
        INSERT OR REPLACE INTO problems (
            leetcode_id, title, slug, difficulty, url, topics_json,
            html_file, status, generation_model, generation_agent,
            generation_attempts, generation_started_at, generation_completed_at,
            generation_duration_seconds, validation_passed, last_error, updated_at
        ) VALUES (
            :leetcode_id, :title, :slug, :difficulty, :url, :topics_json,
            :html_file, :status, :generation_model, :generation_agent,
            :generation_attempts, :generation_started_at, :generation_completed_at,
            :generation_duration_seconds, :validation_passed, :last_error, CURRENT_TIMESTAMP
        )
    """, row_data)
    conn.commit()

    return get_problem_by_id(conn, problem.leetcode_id).db_id


def update_problem_status(conn, leetcode_id: int, new_status: str, **extra_fields):
    """Update a problem's status (with validation) and any extra fields."""
    problem = get_problem_by_id(conn, leetcode_id)
    if not problem:
        raise ValueError(f"Problem {leetcode_id} not found")

    validate_transition(problem.status, new_status)

    cursor = conn.cursor()
    updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params = [new_status]

    for key, value in extra_fields.items():
        updates.append(f"{key} = ?")
        params.append(value)

    params.append(leetcode_id)
    cursor.execute(
        f"UPDATE problems SET {', '.join(updates)} WHERE leetcode_id = ?",
        params
    )
    conn.commit()


def list_problems(conn, status: Optional[str] = None, difficulty: Optional[str] = None) -> List[Problem]:
    """List problems with optional filters."""
    cursor = conn.cursor()
    query = "SELECT * FROM problems WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)

    cursor.execute(query, params)
    return [Problem.from_row(row) for row in cursor.fetchall()]


def count_problems(conn, status: Optional[str] = None, difficulty: Optional[str] = None) -> int:
    """Count problems matching criteria."""
    cursor = conn.cursor()
    query = "SELECT COUNT(*) as cnt FROM problems WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)

    cursor.execute(query, params)
    return cursor.fetchone()["cnt"]


def create_batch(conn, batch: Batch) -> int:
    """Create a batch, return its DB ID."""
    cursor = conn.cursor()
    row_data = batch.to_row()

    cursor.execute("""
        INSERT INTO batches (
            batch_number, difficulty, requested_count, selected_count,
            generated_count, skipped_count, failed_count, status
        ) VALUES (
            :batch_number, :difficulty, :requested_count, :selected_count,
            :generated_count, :skipped_count, :failed_count, :status
        )
    """, row_data)
    conn.commit()
    return cursor.lastrowid


def update_batch(conn, batch_id: int, **fields):
    """Update batch fields."""
    cursor = conn.cursor()
    updates = []
    params = []

    for key, value in fields.items():
        updates.append(f"{key} = ?")
        params.append(value)

    params.append(batch_id)
    cursor.execute(
        f"UPDATE batches SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()


def get_batch(conn, batch_id: int) -> Optional[Batch]:
    """Get a batch by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
    row = cursor.fetchone()
    return Batch.from_row(row) if row else None


def increment_batch_counter(conn, batch_id: int, counter: str, delta: int = 1):
    """Atomically increment a batch counter (generated_count, failed_count, etc.)."""
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE batches SET {counter} = {counter} + ? WHERE id = ?",
        (delta, batch_id)
    )
    conn.commit()


def create_job(conn, job: GenerationJob) -> int:
    """Create a generation job, return its DB ID."""
    cursor = conn.cursor()
    row_data = job.to_row()

    cursor.execute("""
        INSERT INTO generation_jobs (
            batch_id, problem_id, status, agent, model,
            started_at, completed_at, duration_seconds, error
        ) VALUES (
            :batch_id, :problem_id, :status, :agent, :model,
            :started_at, :completed_at, :duration_seconds, :error
        )
    """, row_data)
    conn.commit()
    return cursor.lastrowid


def update_job(conn, job_id: int, **fields):
    """Update a generation job."""
    cursor = conn.cursor()
    updates = []
    params = []

    for key, value in fields.items():
        updates.append(f"{key} = ?")
        params.append(value)

    params.append(job_id)
    cursor.execute(
        f"UPDATE generation_jobs SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()


def get_job(conn, job_id: int) -> Optional[GenerationJob]:
    """Get a job by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    return GenerationJob.from_row(row) if row else None


def list_jobs(conn, batch_id: Optional[int] = None, status: Optional[str] = None) -> List[GenerationJob]:
    """List jobs with optional filters."""
    cursor = conn.cursor()
    query = "SELECT * FROM generation_jobs WHERE 1=1"
    params = []

    if batch_id:
        query += " AND batch_id = ?"
        params.append(batch_id)
    if status:
        query += " AND status = ?"
        params.append(status)

    cursor.execute(query, params)
    return [GenerationJob.from_row(row) for row in cursor.fetchall()]

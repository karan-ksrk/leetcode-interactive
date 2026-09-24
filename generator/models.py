"""Data models for LeetCode Interactive generator."""

from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime
from pathlib import Path
import json


@dataclass
class Problem:
    """Represents a LeetCode problem and its generation state."""
    leetcode_id: int
    title: str
    slug: str
    difficulty: str  # "Easy", "Medium", "Hard"
    url: str
    topics: list[str] = field(default_factory=list)
    html_file: Optional[str] = None  # "problems/1-two-sum.html"
    status: str = "pending"  # pending|fetching|fetched|generating|validating|published|failed
    generation_model: Optional[str] = None
    generation_agent: Optional[str] = None
    generation_attempts: int = 0
    generation_started_at: Optional[str] = None
    generation_completed_at: Optional[str] = None
    generation_duration_seconds: Optional[float] = None
    validation_passed: Optional[bool] = None
    last_error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    db_id: Optional[int] = None  # Internal database PK

    @classmethod
    def from_row(cls, row):
        """Construct from sqlite3.Row."""
        import json
        topics = json.loads(row["topics_json"]) if row["topics_json"] else []
        return cls(
            db_id=row["id"],
            leetcode_id=row["leetcode_id"],
            title=row["title"],
            slug=row["slug"],
            difficulty=row["difficulty"],
            url=row["url"],
            topics=topics,
            html_file=row["html_file"],
            status=row["status"],
            generation_model=row["generation_model"],
            generation_agent=row["generation_agent"],
            generation_attempts=row["generation_attempts"],
            generation_started_at=row["generation_started_at"],
            generation_completed_at=row["generation_completed_at"],
            generation_duration_seconds=row["generation_duration_seconds"],
            validation_passed=row["validation_passed"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_row(self):
        """Convert to DB row format (dict for SQL substitution)."""
        return {
            "leetcode_id": self.leetcode_id,
            "title": self.title,
            "slug": self.slug,
            "difficulty": self.difficulty,
            "url": self.url,
            "topics_json": json.dumps(self.topics),
            "html_file": self.html_file,
            "status": self.status,
            "generation_model": self.generation_model,
            "generation_agent": self.generation_agent,
            "generation_attempts": self.generation_attempts,
            "generation_started_at": self.generation_started_at,
            "generation_completed_at": self.generation_completed_at,
            "generation_duration_seconds": self.generation_duration_seconds,
            "validation_passed": self.validation_passed,
            "last_error": self.last_error,
        }

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        d.pop("db_id", None)
        return d


@dataclass
class Batch:
    """Represents a batch generation job."""
    batch_number: int
    difficulty: str
    requested_count: int
    selected_count: int = 0
    generated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    status: str = "pending"  # pending|running|completed|completed_with_failures
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    db_id: Optional[int] = None

    @classmethod
    def from_row(cls, row):
        """Construct from sqlite3.Row."""
        return cls(
            db_id=row["id"],
            batch_number=row["batch_number"],
            difficulty=row["difficulty"],
            requested_count=row["requested_count"],
            selected_count=row["selected_count"],
            generated_count=row["generated_count"],
            skipped_count=row["skipped_count"],
            failed_count=row["failed_count"],
            status=row["status"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
        )

    def to_row(self):
        """Convert to DB row format."""
        return {
            "batch_number": self.batch_number,
            "difficulty": self.difficulty,
            "requested_count": self.requested_count,
            "selected_count": self.selected_count,
            "generated_count": self.generated_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        d.pop("db_id", None)
        return d


@dataclass
class GenerationJob:
    """Represents a single problem generation within a batch."""
    problem_id: int  # FK to problems.id
    status: str = "pending"  # pending|running|succeeded|failed
    agent: Optional[str] = None
    model: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    batch_id: Optional[int] = None
    db_id: Optional[int] = None

    @classmethod
    def from_row(cls, row):
        """Construct from sqlite3.Row."""
        return cls(
            db_id=row["id"],
            batch_id=row["batch_id"],
            problem_id=row["problem_id"],
            status=row["status"],
            agent=row["agent"],
            model=row["model"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            duration_seconds=row["duration_seconds"],
            error=row["error"],
        )

    def to_row(self):
        """Convert to DB row format."""
        return {
            "batch_id": self.batch_id,
            "problem_id": self.problem_id,
            "status": self.status,
            "agent": self.agent,
            "model": self.model,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        d.pop("db_id", None)
        return d


@dataclass
class AgentResult:
    """Result of a single agent generation call."""
    success: bool
    output_file: Path
    duration_seconds: float
    stdout: str
    stderr: str
    error: Optional[str] = None

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return {
            "success": self.success,
            "output_file": str(self.output_file),
            "duration_seconds": self.duration_seconds,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
        }


class InvalidTransitionError(Exception):
    """Raised when a status transition is not allowed."""
    pass


VALID_TRANSITIONS = {
    "pending": {"fetching", "fetched"},
    "fetching": {"fetched", "failed"},
    "fetched": {"generating"},
    "generating": {"validating", "failed"},
    "validating": {"published", "failed"},
    "failed": {"pending"},
    "published": set(),
}

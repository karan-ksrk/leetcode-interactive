"""Single-problem generation orchestration."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import time

from .database import (
    get_connection, init_db, upsert_problem, update_problem_status,
    get_problem_by_id, create_job, update_job, count_problems
)
from .models import Problem, GenerationJob
from .leetcode_api import LeetCodeClient
from .problem_fetcher import fetch_and_save
from .html_validator import validate
from .manifest import rebuild_problems_json, rebuild_generation_manifest


class GenerationOutcome:
    """Result of a single problem generation."""
    def __init__(self, success, problem, job_id, error=None):
        self.success = success
        self.problem = problem
        self.job_id = job_id
        self.error = error


def reconcile_duplicate(conn: sqlite3.Connection, problem: Problem, problems_dir: Path = Path("problems")) -> str:
    """Check if problem already exists and in what state.

    Returns: "skip", "adopt", "regenerate", or "new"
    """
    existing = get_problem_by_id(conn, problem.leetcode_id)

    if not existing:
        return "new"

    # Published + file exists + valid → skip entirely
    if existing.status == "published":
        expected_file = problems_dir / (existing.html_file or f"problems/{problem.leetcode_id}-{problem.slug}.html")
        if expected_file.exists() and expected_file.stat().st_size > 0:
            return "skip"
        else:
            # Published but file missing → mark failed, log warning
            print(f"WARNING: Problem {problem.leetcode_id} is marked published but file missing: {expected_file}")
            update_problem_status(conn, problem.leetcode_id, "failed",
                                last_error="Published file missing on disk")
            return "skip"

    # File exists on disk but DB not published → regenerate to ensure proper workflow
    # (adopting would skip fetch/generate/validate workflow and violate status transitions)
    expected_file = problems_dir / f"{problem.leetcode_id}-{problem.slug}.html"
    if expected_file.exists() and expected_file.stat().st_size > 0:
        # Existing file on disk but not in DB — regenerate through proper workflow
        return "regenerate"

    return "new"


def generate_one(
    db_path: Path,
    agent,
    url_or_slug: str,
    force: bool = False,
    problems_dir: Path = Path("problems"),
    staging_dir: Path = Path("data/staging"),
) -> GenerationOutcome:
    """Generate HTML for one problem.

    Workflow:
    1. Fetch problem from LeetCode
    2. Normalize and save JSON to data/fetched/
    3. Check if already published (skip if yes)
    4. Invoke agent to generate HTML
    5. Validate output
    6. Move to problems/ directory
    7. Update SQLite + rebuild manifests

    Args:
        db_path: Path to SQLite database
        agent: BaseAgent instance (claude, codex, etc.)
        url_or_slug: LeetCode URL or problem slug
        force: Regenerate even if already published
        problems_dir: Output directory for HTML
        staging_dir: Temporary directory for agent output

    Returns:
        GenerationOutcome with success flag, problem, job_id, error
    """
    start_time = datetime.utcnow()
    conn = get_connection(db_path)
    init_db(conn)

    try:
        # 1. Fetch problem
        print(f"Fetching problem: {url_or_slug}")
        client = LeetCodeClient()
        problem_json_path = fetch_and_save(client, url_or_slug)

        with open(problem_json_path) as f:
            normalized = json.load(f)

        problem = Problem(
            leetcode_id=normalized["leetcode_id"],
            title=normalized["title"],
            slug=normalized["slug"],
            difficulty=normalized["difficulty"],
            url=normalized["url"],
            topics=normalized.get("topics", []),
        )

        # 2. Upsert to DB
        print(f"Tracking problem #{problem.leetcode_id}: {problem.title}")
        problem.db_id = upsert_problem(conn, problem)

        # 3. Check for duplicates
        reconcile_action = reconcile_duplicate(conn, problem, problems_dir)
        if reconcile_action == "skip":
            print(f"Problem #{problem.leetcode_id} already published, skipping.")
            return GenerationOutcome(True, problem, None, "already published")
        elif reconcile_action == "adopt":
            print(f"Adopted existing valid file for problem #{problem.leetcode_id}")
            problem = get_problem_by_id(conn, problem.leetcode_id)
            return GenerationOutcome(True, problem, None, "file adopted")

        # 4. Update status → generating
        update_problem_status(conn, problem.leetcode_id, "fetched")

        job = GenerationJob(
            problem_id=problem.db_id,
            agent=agent.name,
            status="running",
        )
        job.db_id = create_job(conn, job)
        job.started_at = datetime.utcnow().isoformat() + "Z"

        update_problem_status(conn, problem.leetcode_id, "generating",
                            generation_agent=agent.name,
                            generation_started_at=job.started_at,
                            generation_attempts=problem.generation_attempts + 1)

        # 5. Invoke agent
        staging_dir.mkdir(parents=True, exist_ok=True)
        staging_file = staging_dir / f"{problem.leetcode_id}-{problem.slug}.html"
        instruction_file = Path("generator/prompts/leetcode-animator.md")

        print(f"Invoking {agent.name} agent...")
        agent_result = agent.generate(
            problem_file=problem_json_path,
            instruction_file=instruction_file,
            output_file=staging_file,
            timeout_seconds=120,
        )

        if not agent_result.success:
            print(f"Agent failed: {agent_result.error}")
            update_problem_status(conn, problem.leetcode_id, "failed",
                                last_error=agent_result.error or "Agent returned failure")
            update_job(conn, job.db_id,
                     status="failed",
                     completed_at=datetime.utcnow().isoformat() + "Z",
                     duration_seconds=agent_result.duration_seconds,
                     error=agent_result.error)
            return GenerationOutcome(False, problem, job.db_id, agent_result.error)

        # 6. Validate
        print("Validating generated HTML...")
        update_problem_status(conn, problem.leetcode_id, "validating")

        validation = validate(staging_file, run_dynamic=False)
        if not validation.passed:
            error_msg = "; ".join(validation.errors[:3])
            print(f"Validation failed: {error_msg}")
            update_problem_status(conn, problem.leetcode_id, "failed",
                                last_error=error_msg)
            update_job(conn, job.db_id,
                     status="failed",
                     completed_at=datetime.utcnow().isoformat() + "Z",
                     duration_seconds=agent_result.duration_seconds,
                     error=error_msg)
            return GenerationOutcome(False, problem, job.db_id, error_msg)

        # 7. Move to problems/ directory
        problems_dir.mkdir(parents=True, exist_ok=True)
        final_file = problems_dir / f"{problem.leetcode_id}-{problem.slug}.html"
        staging_file.replace(final_file)
        print(f"Published: {final_file}")

        # 8. Update DB
        duration = (datetime.utcnow() - start_time).total_seconds()
        # Store just the filename (manifest.py will add the problems/ prefix)
        html_filename = final_file.name
        update_problem_status(conn, problem.leetcode_id, "published",
                            html_file=html_filename,
                            validation_passed=True,
                            generation_completed_at=datetime.utcnow().isoformat() + "Z",
                            generation_duration_seconds=duration)

        update_job(conn, job.db_id,
                 status="succeeded",
                 completed_at=datetime.utcnow().isoformat() + "Z",
                 duration_seconds=agent_result.duration_seconds)

        # 9. Rebuild manifests
        print("Rebuilding manifests...")
        rebuild_problems_json(conn, problems_dir)
        rebuild_generation_manifest(conn)

        problem = get_problem_by_id(conn, problem.leetcode_id)
        print(f"[OK] Generated #{problem.leetcode_id}: {problem.title} in {duration:.1f}s")

        return GenerationOutcome(True, problem, job.db_id)

    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return GenerationOutcome(False, None, None, str(e))

    finally:
        conn.close()


def update_job(conn, job_id, **fields):
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

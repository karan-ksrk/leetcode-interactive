"""Manifest generation (problems.json, generation-manifest.json)."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def rebuild_problems_json(
    conn: sqlite3.Connection,
    problems_dir: Path = Path("problems"),
    out_path: Path = Path("problems.json"),
) -> List[Dict[str, Any]]:
    """Rebuild problems.json from published problems in DB."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM problems WHERE status = 'published' ORDER BY leetcode_id ASC"
    )

    problems_list = []
    for row in cursor.fetchall():
        # Verify file actually exists on disk
        if row["html_file"]:
            file_path = problems_dir / row["html_file"]
            if not file_path.exists():
                print(f"WARNING: Published problem {row['leetcode_id']} file missing: {file_path}")
                continue

        problem_data = {
            "id": row["leetcode_id"],
            "title": row["title"],
            "slug": row["slug"],
            "difficulty": row["difficulty"],
            "topics": json.loads(row["topics_json"]) if row["topics_json"] else [],
            "file": f"problems/{row['html_file']}" if row["html_file"] else None,
            "url": row["url"],
        }

        problems_list.append(problem_data)

    # Write manifest
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(problems_list, f, indent=2)

    return problems_list


def rebuild_generation_manifest(
    conn: sqlite3.Connection,
    out_path: Path = Path("generation-manifest.json"),
) -> Dict[str, Any]:
    """Rebuild generation-manifest.json with statistics."""
    cursor = conn.cursor()

    # Total and per-status counts
    cursor.execute("SELECT COUNT(*) as cnt FROM problems")
    total_problems = cursor.fetchone()["cnt"]

    status_counts = {}
    for status in ["pending", "fetching", "fetched", "generating", "validating", "published", "failed"]:
        cursor.execute("SELECT COUNT(*) as cnt FROM problems WHERE status = ?", (status,))
        status_counts[status] = cursor.fetchone()["cnt"]

    # Per-difficulty counts
    difficulty_counts = {}
    for difficulty in ["Easy", "Medium", "Hard"]:
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM problems WHERE difficulty = ? AND status = 'published'",
            (difficulty,)
        )
        difficulty_counts[difficulty] = cursor.fetchone()["cnt"]

    # Per-agent counts
    agent_counts = {}
    cursor.execute(
        "SELECT DISTINCT generation_agent FROM problems WHERE status = 'published' AND generation_agent IS NOT NULL"
    )
    for row in cursor.fetchall():
        agent = row["generation_agent"]
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM problems WHERE generation_agent = ? AND status = 'published'",
            (agent,)
        )
        agent_counts[agent] = cursor.fetchone()["cnt"]

    # Last batch summary
    cursor.execute(
        "SELECT * FROM batches ORDER BY created_at DESC LIMIT 1"
    )
    last_batch_row = cursor.fetchone()
    last_batch_summary = None
    if last_batch_row:
        last_batch_summary = {
            "batch_number": last_batch_row["batch_number"],
            "difficulty": last_batch_row["difficulty"],
            "status": last_batch_row["status"],
            "generated_count": last_batch_row["generated_count"],
            "failed_count": last_batch_row["failed_count"],
        }

    # Average generation duration
    cursor.execute(
        "SELECT AVG(generation_duration_seconds) as avg_duration FROM problems WHERE status = 'published' AND generation_duration_seconds IS NOT NULL"
    )
    avg_duration_row = cursor.fetchone()
    avg_duration = avg_duration_row["avg_duration"] if avg_duration_row["avg_duration"] else 0

    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_problems": total_problems,
        "status_counts": status_counts,
        "difficulty_counts": difficulty_counts,
        "agent_counts": agent_counts,
        "last_batch": last_batch_summary,
        "avg_generation_duration_seconds": round(avg_duration, 2),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest

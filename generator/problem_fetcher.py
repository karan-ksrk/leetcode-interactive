"""Fetch and normalize LeetCode problems."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .leetcode_api import LeetCodeClient
from .utils import problem_filename_stem, normalize_slug


def normalize_problem(raw: dict) -> dict:
    """Normalize raw LeetCode API response to our schema."""
    # If already normalized (from new vercel API), return as-is
    if "leetcode_id" in raw and isinstance(raw.get("leetcode_id"), int):
        return raw

    frontend_id = raw.get("questionFrontendId", raw.get("questionId", 0))
    slug = normalize_slug(raw.get("titleSlug", ""))

    topics = []
    if "topicTags" in raw:
        topics = [tag.get("name") for tag in raw["topicTags"] if tag.get("name")]

    examples = []
    if "exampleTestcases" in raw:
        examples_str = raw["exampleTestcases"]
        if examples_str:
            examples = [{"input": examples_str, "output": "", "explanation": ""}]

    constraints = []
    if "constraints" in raw and isinstance(raw["constraints"], dict):
        constraints_list = raw["constraints"].get("constraints", [])
        constraints = constraints_list if isinstance(constraints_list, list) else []

    starter_code = ""
    if "codeSnippets" in raw:
        for snippet in raw["codeSnippets"]:
            if snippet.get("langSlug") == "python3":
                starter_code = snippet.get("code", "")
                break

    return {
        "leetcode_id": int(frontend_id) if frontend_id else 0,
        "title": raw.get("title", ""),
        "slug": slug,
        "difficulty": raw.get("difficulty", "").capitalize() if raw.get("difficulty") else "Medium",
        "url": f"https://leetcode.com/problems/{slug}/",
        "topics": topics,
        "description_summary": "",
        "examples": examples,
        "constraints": constraints,
        "starter_python": starter_code,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


def fetch_and_save(
    client: LeetCodeClient,
    url_or_slug: str,
    out_dir: Path = Path("data/fetched")
) -> Path:
    """Fetch a problem and save its normalized JSON."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if url_or_slug.startswith("http"):
        raw = client.get_problem_by_url(url_or_slug)
    else:
        raw = client.get_problem_by_slug(url_or_slug)

    normalized = normalize_problem(raw)

    filename = problem_filename_stem(
        normalized["leetcode_id"],
        normalized["slug"]
    ) + ".json"

    out_path = out_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)

    return out_path

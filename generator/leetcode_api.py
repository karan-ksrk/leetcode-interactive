"""LeetCode API client using vercel-hosted unofficial API."""

from typing import Optional, Dict, List
import re
import time
import requests


class LeetCodeAPIError(Exception):
    pass


class LeetCodeClient:
    """LeetCode client using vercel API (no scraping needed)."""

    BASE_URL = "https://leetcode-api-pied.vercel.app"

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.session = requests.Session()

    def get_problem_by_slug(self, slug: str) -> dict:
        """Fetch problem by slug from vercel API."""
        url = f"{self.BASE_URL}/problem/{slug}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Normalize to our schema
            return self._normalize_api_response(data)

        except requests.RequestException as e:
            raise LeetCodeAPIError(f"Failed to fetch problem {slug}: {e}")

    def get_problem_by_url(self, url: str) -> dict:
        """Parse slug from URL and fetch the problem."""
        match = re.search(r'/problems/([a-z0-9\-]+)', url)
        if not match:
            raise LeetCodeAPIError(f"Could not parse problem slug from URL: {url}")

        slug = match.group(1)
        return self.get_problem_by_slug(slug)

    def get_problems_by_difficulty(self, difficulty: str, limit: int = 50, skip: int = 0) -> List[dict]:
        """Fetch problems by difficulty from vercel API."""
        url = f"{self.BASE_URL}/problems"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            problems = response.json()

            # Filter by difficulty
            difficulty_map = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
            target_difficulty = difficulty_map.get(difficulty.lower())

            filtered = [p for p in problems if p.get("difficulty") == target_difficulty]

            # Return paginated results
            return filtered[skip:skip + limit]

        except requests.RequestException as e:
            raise LeetCodeAPIError(f"Failed to fetch problems by difficulty: {e}")

    def _normalize_api_response(self, data: dict) -> dict:
        """Normalize vercel API response to our internal schema."""
        frontend_id = data.get("questionFrontendId", data.get("questionId", 0))

        # Extract slug from content or URL
        slug = ""
        url = data.get("url", "")
        if url:
            match = re.search(r'/problems/([a-z0-9\-]+)', url)
            if match:
                slug = match.group(1)

        # Extract topics from topicTags
        topics = []
        if "topicTags" in data:
            topics = [tag.get("name") for tag in data["topicTags"] if tag.get("name")]

        # Extract examples/testcases from code snippets or hints
        examples = []
        if "codeSnippets" in data:
            # Try to find testcases in the content
            content = data.get("content", "")
            if "<strong class=\"example\">Example" in content:
                examples.append({
                    "input": content,
                    "output": "",
                    "explanation": "See content above"
                })

        # Extract constraints from content
        constraints = []
        content = data.get("content", "")
        constraints_section = re.search(r'<strong>Constraints:</strong>.*?</ul>', content, re.DOTALL)
        if constraints_section:
            constraints = [{"text": constraints_section.group(0)}]

        # Extract starter code for Python
        starter_code = ""
        if "codeSnippets" in data:
            for snippet in data["codeSnippets"]:
                if snippet.get("langSlug") == "python3":
                    starter_code = snippet.get("code", "")
                    break

        return {
            "leetcode_id": int(frontend_id) if frontend_id else 0,
            "title": data.get("title", ""),
            "slug": slug,
            "difficulty": data.get("difficulty", "").capitalize() if data.get("difficulty") else "Medium",
            "url": url,
            "topics": topics,
            "description_summary": "",
            "examples": examples,
            "constraints": constraints,
            "starter_python": starter_code,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

"""LeetCode API client using alfa-leetcode-api library."""

from typing import Optional, Dict, List
from alfa_leetcode_api.leetcode import LeetCode


class LeetCodeAPIError(Exception):
    pass


class LeetCodeClient:
    """LeetCode client using alfa-leetcode-api library (community-maintained)."""

    def __init__(self):
        try:
            self.lc = LeetCode()
        except Exception as e:
            raise LeetCodeAPIError(f"Failed to initialize LeetCode client: {e}")

    def get_problem_by_slug(self, slug: str) -> dict:
        """Fetch a problem by slug."""
        try:
            question = self.lc.get_question(slug)
            if not question:
                raise LeetCodeAPIError(f"Problem not found: {slug}")

            return {
                "questionId": question.get("questionId"),
                "questionFrontendId": question.get("questionFrontendId"),
                "title": question.get("title"),
                "titleSlug": question.get("titleSlug"),
                "difficulty": question.get("difficulty"),
                "topicTags": [{"name": tag} for tag in question.get("topicTags", [])],
                "exampleTestcases": question.get("exampleTestcases", ""),
                "constraints": question.get("constraints", []),
                "content": question.get("content", ""),
            }
        except Exception as e:
            raise LeetCodeAPIError(f"Failed to fetch problem {slug}: {e}")

    def get_problem_by_url(self, url: str) -> dict:
        """Parse slug from URL and fetch the problem."""
        import re
        match = re.search(r'/problems/([a-z0-9\-]+)', url)
        if not match:
            raise LeetCodeAPIError(f"Could not parse problem slug from URL: {url}")

        slug = match.group(1)
        return self.get_problem_by_slug(slug)

    def get_problems_by_difficulty(self, difficulty: str, limit: int = 50, skip: int = 0) -> List[dict]:
        """Fetch problems by difficulty level."""
        try:
            difficulty_map = {
                "easy": "Easy",
                "medium": "Medium",
                "hard": "Hard"
            }
            difficulty_display = difficulty_map.get(difficulty.lower())
            if not difficulty_display:
                raise ValueError(f"Invalid difficulty: {difficulty}")

            # Fetch problems with difficulty filter
            # alfa-leetcode-api returns a list of problems
            problems = self.lc.get_problems(
                filters={"difficulty": difficulty_display}
            )

            if not problems:
                return []

            # Return as list of dicts matching our expected format
            result = []
            for p in problems[skip:skip + limit]:
                result.append({
                    "questionId": p.get("questionId"),
                    "questionFrontendId": p.get("questionFrontendId"),
                    "title": p.get("title"),
                    "titleSlug": p.get("titleSlug"),
                    "difficulty": p.get("difficulty"),
                    "topicTags": [{"name": tag} for tag in p.get("topicTags", [])],
                })

            return result

        except Exception as e:
            print(f"Warning: Problem fetch failed ({e}), returning empty list")
            return []

"""LeetCode API client for fetching problem metadata."""

import requests
import json
from typing import Optional, Dict, List
import time


class LeetCodeAPIError(Exception):
    pass


class LeetCodeClient:
    """GraphQL-based LeetCode client, metadata-only (no full HTML descriptions)."""

    def __init__(self, base_url: str = "https://leetcode.com/graphql", timeout: float = 15.0):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/",
            "Accept": "application/json",
        })

    def _post_graphql(self, query: str, variables: dict) -> dict:
        """Execute a GraphQL query with retry/backoff."""
        payload = {
            "query": query,
            "variables": variables,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.base_url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    error_msg = "; ".join([e.get("message", str(e)) for e in data["errors"]])
                    raise LeetCodeAPIError(f"GraphQL error: {error_msg}")

                return data.get("data", {})

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                else:
                    raise LeetCodeAPIError(f"API request failed after {max_retries} attempts: {e}")

    def get_problem_by_slug(self, slug: str) -> dict:
        """Fetch a problem by slug. Returns metadata only."""
        query = """
        query getProblem($slug: String!) {
            question(titleSlug: $slug) {
                questionId
                questionFrontendId
                title
                titleSlug
                difficulty
                content
                exampleTestcases
                topicTags {
                    name
                }
                stats
                codeSnippets {
                    lang
                    langSlug
                    code
                }
                constraints {
                    constraints
                }
            }
        }
        """

        data = self._post_graphql(query, {"slug": slug})
        question = data.get("question")

        if not question:
            raise LeetCodeAPIError(f"Problem not found: {slug}")

        return question

    def get_problem_by_url(self, url: str) -> dict:
        """Parse slug from a LeetCode URL and fetch the problem."""
        # Extract slug from URL like https://leetcode.com/problems/two-sum/
        # or https://leetcode.com/problems/two-sum/?something=value
        import re
        match = re.search(r'/problems/([a-z0-9\-]+)', url)
        if not match:
            raise LeetCodeAPIError(f"Could not parse problem slug from URL: {url}")

        slug = match.group(1)
        return self.get_problem_by_slug(slug)

    def get_problems_by_difficulty(self, difficulty: str, limit: int = 50, skip: int = 0) -> List[dict]:
        """Fetch problems by difficulty level."""
        # Normalize difficulty
        difficulty_map = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
        difficulty_display = difficulty_map.get(difficulty.lower())
        if not difficulty_display:
            raise ValueError(f"Invalid difficulty: {difficulty}")

        query = """
        query getProblems($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
            problemsetQuestionList(
                categorySlug: $categorySlug
                limit: $limit
                skip: $skip
                filters: $filters
            ) {
                total
                questions {
                    questionId
                    questionFrontendId
                    title
                    titleSlug
                    difficulty
                    topicTags {
                        name
                    }
                }
            }
        }
        """

        try:
            data = self._post_graphql(query, {
                "categorySlug": "all-code-problems",
                "limit": limit,
                "skip": skip,
                "filters": {"difficulty": difficulty_display},
            })

            problem_list = data.get("problemsetQuestionList", {})
            return problem_list.get("questions", [])
        except Exception as e:
            print(f"API Error: {e}. Try single problem mode instead (option 1)")
            return []

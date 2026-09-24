"""LeetCode API client - scrapes problem data from HTML."""

from typing import Optional, Dict, List
import re
import requests
from bs4 import BeautifulSoup


class LeetCodeAPIError(Exception):
    pass


class LeetCodeClient:
    """LeetCode client - fetches individual problems from their pages."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def get_problem_by_slug(self, slug: str) -> dict:
        """Fetch a problem by slug - scrapes the problem page."""
        url = f"https://leetcode.com/problems/{slug}/"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Extract data from the HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try to find the problem data in the page's JavaScript data
            # LeetCode embeds problem data in a script tag
            script_tags = soup.find_all('script')

            problem_data = self._extract_problem_from_html(response.text, slug)

            if not problem_data:
                raise LeetCodeAPIError(f"Could not extract problem data for {slug}")

            return problem_data

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
        """Fetch problems by difficulty - returns a static hardcoded list."""
        # Since LeetCode blocks batch API calls, we provide a default list
        # Users should use batch_generate.py with their own URLs instead

        hardcoded_problems = {
            "Easy": [
                {"questionFrontendId": 1, "title": "Two Sum", "titleSlug": "two-sum", "difficulty": "Easy", "topicTags": [{"name": "Array"}, {"name": "Hash Table"}]},
                {"questionFrontendId": 9, "title": "Palindrome Number", "titleSlug": "palindrome-number", "difficulty": "Easy", "topicTags": [{"name": "Math"}]},
                {"questionFrontendId": 13, "title": "Roman to Integer", "titleSlug": "roman-to-integer", "difficulty": "Easy", "topicTags": [{"name": "Hash Table"}, {"name": "Math"}, {"name": "String"}]},
                {"questionFrontendId": 14, "title": "Longest Common Prefix", "titleSlug": "longest-common-prefix", "difficulty": "Easy", "topicTags": [{"name": "String"}, {"name": "Trie"}]},
                {"questionFrontendId": 20, "title": "Valid Parentheses", "titleSlug": "valid-parentheses", "difficulty": "Easy", "topicTags": [{"name": "String"}, {"name": "Stack"}]},
            ],
            "Medium": [
                {"questionFrontendId": 2, "title": "Add Two Numbers", "titleSlug": "add-two-numbers", "difficulty": "Medium", "topicTags": [{"name": "Linked List"}, {"name": "Math"}]},
                {"questionFrontendId": 3, "title": "Longest Substring Without Repeating Characters", "titleSlug": "longest-substring-without-repeating-characters", "difficulty": "Medium", "topicTags": [{"name": "Hash Table"}, {"name": "String"}, {"name": "Sliding Window"}]},
                {"questionFrontendId": 5, "title": "Longest Palindromic Substring", "titleSlug": "longest-palindromic-substring", "difficulty": "Medium", "topicTags": [{"name": "String"}, {"name": "Dynamic Programming"}]},
                {"questionFrontendId": 11, "title": "Container With Most Water", "titleSlug": "container-with-most-water", "difficulty": "Medium", "topicTags": [{"name": "Array"}, {"name": "Two Pointers"}]},
                {"questionFrontendId": 15, "title": "3Sum", "titleSlug": "3sum", "difficulty": "Medium", "topicTags": [{"name": "Array"}, {"name": "Sorting"}]},
            ],
            "Hard": [
                {"questionFrontendId": 4, "title": "Median of Two Sorted Arrays", "titleSlug": "median-of-two-sorted-arrays", "difficulty": "Hard", "topicTags": [{"name": "Array"}, {"name": "Binary Search"}, {"name": "Divide and Conquer"}]},
                {"questionFrontendId": 10, "title": "Regular Expression Matching", "titleSlug": "regular-expression-matching", "difficulty": "Hard", "topicTags": [{"name": "String"}, {"name": "Dynamic Programming"}]},
                {"questionFrontendId": 23, "title": "Merge k Sorted Lists", "titleSlug": "merge-k-sorted-lists", "difficulty": "Hard", "topicTags": [{"name": "Linked List"}, {"name": "Divide and Conquer"}, {"name": "Heap"}]},
                {"questionFrontendId": 25, "title": "Reverse Nodes in k-Group", "titleSlug": "reverse-nodes-in-k-group", "difficulty": "Hard", "topicTags": [{"name": "Linked List"}, {"name": "Recursion"}]},
                {"questionFrontendId": 51, "title": "N-Queens", "titleSlug": "n-queens", "difficulty": "Hard", "topicTags": [{"name": "Array"}, {"name": "Backtracking"}]},
            ]
        }

        difficulty_map = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
        difficulty_display = difficulty_map.get(difficulty.lower())

        if not difficulty_display or difficulty_display not in hardcoded_problems:
            return []

        problems = hardcoded_problems[difficulty_display]
        return problems[skip:skip + limit]

    def _extract_problem_from_html(self, html: str, slug: str) -> Optional[dict]:
        """Extract problem data from HTML page."""
        try:
            # Try to extract from initial data in HTML
            # LeetCode stores problem data in a script tag with id __INITIAL_STATE__

            match = re.search(r'"questionFrontendId":"?(\d+)"?', html)
            frontend_id = match.group(1) if match else None

            match = re.search(r'"title":"([^"]+)"', html)
            title = match.group(1) if match else slug.replace('-', ' ').title()

            match = re.search(r'"difficulty":"([^"]+)"', html)
            difficulty = match.group(1) if match else "Medium"

            # Extract topics
            topics_list = []
            topic_matches = re.findall(r'"name":"([^"]+)"', html)
            if topic_matches:
                topics_list = [{"name": t} for t in list(set(topic_matches))[:5]]

            return {
                "questionId": frontend_id,
                "questionFrontendId": frontend_id,
                "title": title,
                "titleSlug": slug,
                "difficulty": difficulty,
                "url": f"https://leetcode.com/problems/{slug}/",
                "topicTags": topics_list,
                "exampleTestcases": "",
                "constraints": [],
                "content": "",
            }

        except Exception as e:
            print(f"Warning: Could not extract full problem data for {slug}: {e}")
            return None

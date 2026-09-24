"""Utility functions for LeetCode Interactive generator."""

import re


def problem_filename_stem(leetcode_id: int, slug: str) -> str:
    """Generate a consistent filename stem from problem ID + slug."""
    return f"{leetcode_id}-{slug}"


def slug_from_title(title: str) -> str:
    """Convert a problem title to a URL-safe slug."""
    s = title.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'^-+|-+$', '', s)
    return s


def normalize_slug(slug: str) -> str:
    """Normalize a slug to lowercase with hyphens."""
    s = slug.lower()
    s = re.sub(r'[^a-z0-9\-]', '', s)
    s = re.sub(r'-+', '-', s)
    s = re.sub(r'^-+|-+$', '', s)
    return s

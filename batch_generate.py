#!/usr/bin/env python3
"""
Simple batch generation script — read problem URLs from a file and generate each.

Usage:
  1. Create batch_problems.txt with one LeetCode URL per line
  2. python batch_generate.py
"""

import sys
from pathlib import Path
from generator.config import load_config, create_default_config
from generator.agents import get_agent
from generator.generation_manager import generate_one


def main():
    # Setup
    create_default_config()
    config = load_config()

    # Read problem URLs
    batch_file = Path("batch_problems.txt")
    if not batch_file.exists():
        print("Error: batch_problems.txt not found")
        print("\nCreate batch_problems.txt with one LeetCode URL per line:")
        print("  https://leetcode.com/problems/two-sum/")
        print("  https://leetcode.com/problems/add-two-numbers/")
        sys.exit(1)

    with open(batch_file) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("No URLs found in batch_problems.txt")
        sys.exit(1)

    print(f"Generating {len(urls)} problems...\n")

    # Select agent
    print("Available agents:")
    for agent_name in ["claude", "codex", "gemini"]:
        agent_cls = get_agent(agent_name)
        available = agent_cls.is_available() if hasattr(agent_cls, 'is_available') else False
        status = "✓" if available else "✗"
        print(f"  {status} {agent_name}")

    agent_choice = input("\nSelect agent (claude/codex/gemini): ").strip().lower() or "claude"
    if agent_choice not in ["claude", "codex", "gemini"]:
        print("Invalid agent")
        sys.exit(1)

    agent = get_agent(agent_choice)
    if not agent.is_available():
        print(f"{agent_choice} not installed")
        sys.exit(1)

    # Generate each problem
    generated = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")

        outcome = generate_one(
            db_path=config.db_path,
            agent=agent,
            url_or_slug=url,
        )

        if outcome.success:
            generated += 1
            print(f"✓ Generated: {outcome.problem.title}")
        else:
            failed += 1
            print(f"✗ Failed: {outcome.error}")

    print(f"\n=== Summary ===")
    print(f"Generated: {generated}")
    print(f"Failed: {failed}")
    print(f"Total: {len(urls)}")


if __name__ == "__main__":
    main()

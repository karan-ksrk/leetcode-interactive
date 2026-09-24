"""Interactive CLI for the LeetCode Interactive generator."""

import argparse
import sqlite3
from pathlib import Path

from .database import init_db, get_connection, list_problems
from .config import load_config, create_default_config
from .manifest import rebuild_problems_json, rebuild_generation_manifest
from .agents import get_agent
from .generation_manager import generate_one
from .batch_manager import BatchManager


def print_menu():
    print("\n" + "="*50)
    print("LEETCODE INTERACTIVE GENERATOR")
    print("="*50)
    print("1. Generate specific problem")
    print("2. Generate batches")
    print("3. Validate generated problems")
    print("4. Rebuild website manifest")
    print("5. Show generation statistics")
    print("6. Exit")
    print("="*50)


def show_stats(conn):
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM problems")
    total = cursor.fetchone()["cnt"]

    print(f"\nGeneration Statistics")
    print(f"Total problems tracked: {total}")

    for difficulty in ["Easy", "Medium", "Hard"]:
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM problems WHERE difficulty = ?",
            (difficulty,)
        )
        count = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM problems WHERE difficulty = ? AND status = 'published'",
            (difficulty,)
        )
        published = cursor.fetchone()["cnt"]

        print(f"\n{difficulty}:")
        print(f"  Published: {published}")
        print(f"  Remaining: {count - published}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="LeetCode Interactive Generator")
    parser.add_argument("--agent", choices=["claude", "codex", "gemini", "generic"], help="AI agent to use")
    parser.add_argument("--parallel", type=int, help="Parallelism level")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Config file path")

    args = parser.parse_args(argv)

    # Create default config if it doesn't exist
    create_default_config(args.config)

    # Load config
    config = load_config(args.config)

    # Initialize database
    conn = get_connection(config.db_path)
    init_db(conn)

    # Interactive menu
    while True:
        print_menu()
        choice = input("\nSelect an option (1-6): ").strip()

        if choice == "1":
            print("\nGenerate specific problem")
            url = input("Paste LeetCode problem URL (or slug): ").strip()
            if not url:
                print("No URL provided.")
                continue

            print("\nAvailable agents:")
            available_agents = []
            for agent_name in ["claude", "codex", "gemini"]:
                if config.agents.get(agent_name, {}).enabled:
                    agent_cls = get_agent(agent_name)
                    available = agent_cls.is_available() if hasattr(agent_cls, 'is_available') else False
                    status = "[OK] installed" if available else "[FAIL] not found"
                    print(f"  {agent_name}: {status}")
                    available_agents.append((agent_name, available))

            agent_choice = input("Select agent (claude/codex/gemini): ").strip().lower()
            if agent_choice not in ["claude", "codex", "gemini"]:
                print("Invalid agent.")
                continue

            agent = get_agent(agent_choice)
            if not agent.is_available():
                print(f"{agent_choice} CLI not found. Install it and try again.")
                continue

            print(f"Generating with {agent_choice}...")
            outcome = generate_one(
                db_path=config.db_path,
                agent=agent,
                url_or_slug=url,
            )

            if outcome.success:
                print(f"\n[OK] Generated: #{outcome.problem.leetcode_id} - {outcome.problem.title}")
            else:
                print(f"\n[FAIL] Failed: {outcome.error}")

        elif choice == "2":
            print("\nGenerate batches")

            print("\nDifficulty:")
            print("  1. Easy")
            print("  2. Medium")
            print("  3. Hard")
            difficulty_choice = input("Select (1-3): ").strip()
            difficulty_map = {"1": "Easy", "2": "Medium", "3": "Hard"}
            difficulty = difficulty_map.get(difficulty_choice)
            if not difficulty:
                print("Invalid choice.")
                continue

            batch_count = input("Number of batches [1]: ").strip() or "1"
            try:
                batch_count = int(batch_count)
            except ValueError:
                print("Invalid number.")
                continue

            batch_size = input("Batch size [5]: ").strip() or "5"
            try:
                batch_size = int(batch_size)
            except ValueError:
                print("Invalid number.")
                continue

            print("\nGeneration mode:")
            print("  1. Sequential (one at a time)")
            print("  2. Parallel (5 concurrent workers)")
            mode_choice = input("Select (1-2) [2]: ").strip() or "2"
            sequential = mode_choice == "1"

            agent_choice = input("Select agent (claude/codex/gemini) [claude]: ").strip().lower() or "claude"
            if agent_choice not in ["claude", "codex", "gemini"]:
                print("Invalid agent.")
                continue

            agent = get_agent(agent_choice)
            if not agent.is_available():
                print(f"{agent_choice} CLI not found.")
                continue

            def agent_factory():
                return get_agent(agent_choice)

            mgr = BatchManager(config.db_path)
            try:
                batch = mgr.run_batch(
                    agent_factory=agent_factory,
                    difficulty=difficulty,
                    batch_count=batch_count,
                    batch_size=batch_size,
                    sequential=sequential,
                    max_workers=5,
                )

                if batch:
                    print(f"\nBatch generation complete!")
                    print(f"  Difficulty: {batch.difficulty}")
                    print(f"  Total: {batch.selected_count} problems")
                    print(f"  Generated: {batch.generated_count}")
                    print(f"  Failed: {batch.failed_count}")
            finally:
                mgr.close()
            print("  5. Generate problems in parallel (max 5 workers)")

        elif choice == "3":
            print("\nValidating all published problems...")
            from .html_validator import validate

            published = list_problems(conn, status="published")
            if not published:
                print("No published problems to validate.")
                continue

            passed = 0
            failed = 0

            for problem in published:
                if problem.html_file:
                    file_path = Path(problem.html_file)
                    result = validate(file_path, run_dynamic=False)

                    if result.passed:
                        passed += 1
                        print(f"  ✓ #{problem.leetcode_id} - {problem.title}")
                    else:
                        failed += 1
                        print(f"  ✗ #{problem.leetcode_id} - {problem.title}")
                        for error in result.errors[:2]:
                            print(f"      {error}")

            print(f"\nValidation complete: {passed} passed, {failed} failed")

        elif choice == "4":
            print("\nRebuilding manifests...")
            try:
                rebuild_problems_json(conn)
                print("✓ Rebuilt problems.json")
                rebuild_generation_manifest(conn)
                print("✓ Rebuilt generation-manifest.json")
            except Exception as e:
                print(f"✗ Error: {e}")

        elif choice == "5":
            show_stats(conn)

        elif choice == "6":
            print("\nExiting.")
            conn.close()
            return 0

        else:
            print("Invalid choice. Please select 1-6.")

    conn.close()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

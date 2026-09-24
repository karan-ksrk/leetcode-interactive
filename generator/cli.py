"""Interactive CLI for the LeetCode Interactive generator."""

import argparse
import sqlite3
from pathlib import Path

from .database import init_db, get_connection
from .config import load_config, create_default_config
from .manifest import rebuild_problems_json, rebuild_generation_manifest


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
            print("(Feature not yet implemented)")
            print("Expected workflow:")
            print("  1. Paste LeetCode problem URL")
            print("  2. Select AI agent")
            print("  3. Generate → Validate → Publish")

        elif choice == "2":
            print("\nGenerate batches")
            print("(Feature not yet implemented)")
            print("Expected workflow:")
            print("  1. Select difficulty (Easy/Medium/Hard)")
            print("  2. Enter batch count")
            print("  3. Enter batch size (default 5)")
            print("  4. Select sequential/parallel mode")
            print("  5. Generate problems in parallel (max 5 workers)")

        elif choice == "3":
            print("\nValidate generated problems")
            print("(Feature not yet implemented)")
            print("Expected workflow:")
            print("  - Run static HTML checks on all published problems")
            print("  - Optional Playwright dynamic checks if installed")

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

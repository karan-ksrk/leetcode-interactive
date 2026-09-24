"""Batch generation orchestration."""

import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .database import (
    get_connection, init_db, list_problems, create_batch, update_batch,
    increment_batch_counter, get_problem_by_id, count_problems
)
from .models import Batch
from .leetcode_api import LeetCodeClient
from .generation_manager import generate_one


class BatchManager:
    """Orchestrates batch problem generation."""

    def __init__(self, db_path: Path = Path("database/leetcode.db")):
        self.db_path = db_path
        self.conn = get_connection(db_path)
        init_db(self.conn)
        self._db_lock = threading.Lock()

    def close(self):
        if self.conn:
            self.conn.close()

    def select_batch_candidates(self, difficulty: str, limit: int) -> list:
        """Select unpublished problems by difficulty.

        Args:
            difficulty: "Easy", "Medium", or "Hard"
            limit: Maximum number of problems to select

        Returns:
            List of unpublished problems (as dicts from LeetCode API)
        """
        print(f"Fetching {difficulty} problems from LeetCode...")
        client = LeetCodeClient()

        # Fetch all problems of this difficulty
        all_problems = []
        skip = 0
        batch_size = 50

        while len(all_problems) < limit * 2:  # Fetch extra to account for already-published
            batch = client.get_problems_by_difficulty(difficulty, limit=batch_size, skip=skip)
            if not batch:
                break
            all_problems.extend(batch)
            skip += batch_size

        # Filter out already-published
        with self._db_lock:
            published_ids = set()
            for problem in list_problems(self.conn, status="published", difficulty=difficulty):
                published_ids.add(problem.leetcode_id)

        candidates = []
        for problem in all_problems:
            problem_id = problem.get("questionFrontendId", problem.get("questionId"))
            if problem_id not in published_ids:
                candidates.append(problem)
            if len(candidates) >= limit:
                break

        print(f"Selected {len(candidates)} unpublished {difficulty} problems")
        return candidates

    def run_batch(
        self,
        agent_factory,
        difficulty: str,
        batch_count: int = 1,
        batch_size: int = 5,
        sequential: bool = False,
        max_workers: int = 5,
    ) -> Batch:
        """Run a batch of problem generations.

        Args:
            agent_factory: Callable that returns a BaseAgent instance
            difficulty: "Easy", "Medium", or "Hard"
            batch_count: Number of batches to run
            batch_size: Problems per batch
            sequential: If True, generate one-by-one. If False, use ThreadPoolExecutor
            max_workers: Max concurrent workers (used if sequential=False)

        Returns:
            Last batch object with final counts
        """
        total_requested = batch_count * batch_size
        print(f"\nBatch generation: {difficulty} x {batch_count} batches of {batch_size} = {total_requested} total")

        # Select all candidates upfront (once)
        candidates = self.select_batch_candidates(difficulty, total_requested)
        selected = len(candidates)

        if selected < total_requested:
            print(f"WARNING: Only {selected} unpublished problems available (wanted {total_requested})")

        last_batch = None

        for batch_num in range(1, batch_count + 1):
            batch_start_idx = (batch_num - 1) * batch_size
            batch_end_idx = min(batch_start_idx + batch_size, len(candidates))
            batch_candidates = candidates[batch_start_idx:batch_end_idx]

            if not batch_candidates:
                print(f"No more problems for batch {batch_num}, stopping.")
                break

            print(f"\n--- Batch #{batch_num} ({len(batch_candidates)} problems) ---")

            # Create batch record
            with self._db_lock:
                batch = Batch(
                    batch_number=batch_num,
                    difficulty=difficulty,
                    requested_count=batch_size,
                    selected_count=len(batch_candidates),
                    status="running",
                    started_at=datetime.utcnow().isoformat() + "Z",
                )
                batch.db_id = create_batch(self.conn, batch)

            # Generate problems
            if sequential:
                self._run_sequential(batch.db_id, batch_candidates, agent_factory)
            else:
                self._run_parallel(batch.db_id, batch_candidates, agent_factory, max_workers)

            # Finalize batch
            with self._db_lock:
                batch_db = self.conn.cursor()
                batch_db.execute("SELECT * FROM batches WHERE id = ?", (batch.db_id,))
                batch_row = batch_db.fetchone()

                update_batch(self.conn, batch.db_id,
                           status="completed",
                           completed_at=datetime.utcnow().isoformat() + "Z")

                batch.generated_count = batch_row["generated_count"]
                batch.failed_count = batch_row["failed_count"]
                batch.status = "completed"
                batch.completed_at = datetime.utcnow().isoformat() + "Z"

            print(f"\nBatch #{batch_num} complete: {batch.generated_count} generated, {batch.failed_count} failed")
            last_batch = batch

        return last_batch

    def _run_sequential(self, batch_id: int, candidates: list, agent_factory):
        """Generate problems one-by-one."""
        for i, problem_data in enumerate(candidates, 1):
            problem_id = problem_data.get("questionFrontendId", problem_data.get("questionId"))
            problem_slug = problem_data.get("titleSlug")
            print(f"  [{i}/{len(candidates)}] Generating #{problem_id}: {problem_data.get('title')}")

            agent = agent_factory()
            url = f"https://leetcode.com/problems/{problem_slug}/"

            outcome = generate_one(self.db_path, agent, url)

            with self._db_lock:
                if outcome.success:
                    increment_batch_counter(self.conn, batch_id, "generated_count")
                    print(f"        ✓ Success")
                else:
                    increment_batch_counter(self.conn, batch_id, "failed_count")
                    print(f"        ✗ Failed: {outcome.error}")

    def _run_parallel(self, batch_id: int, candidates: list, agent_factory, max_workers: int):
        """Generate problems in parallel with ThreadPoolExecutor."""
        print(f"Running {len(candidates)} problems with {max_workers} workers...")

        completed = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for problem_data in candidates:
                problem_id = problem_data.get("questionFrontendId", problem_data.get("questionId"))
                problem_slug = problem_data.get("titleSlug")

                future = executor.submit(
                    self._worker_generate,
                    agent_factory,
                    problem_id,
                    problem_slug,
                    problem_data.get("title")
                )
                futures[future] = problem_id

            # Collect results as they complete
            for future in as_completed(futures):
                problem_id = futures[future]
                try:
                    outcome = future.result()

                    with self._db_lock:
                        if outcome.success:
                            increment_batch_counter(self.conn, batch_id, "generated_count")
                            completed += 1
                            print(f"  ✓ #{problem_id}")
                        else:
                            increment_batch_counter(self.conn, batch_id, "failed_count")
                            failed += 1
                            print(f"  ✗ #{problem_id}: {outcome.error}")

                except Exception as e:
                    with self._db_lock:
                        increment_batch_counter(self.conn, batch_id, "failed_count")
                    failed += 1
                    print(f"  ✗ #{problem_id}: {e}")

        print(f"Parallel batch complete: {completed} succeeded, {failed} failed")

    def _worker_generate(self, agent_factory, problem_id: int, slug: str, title: str):
        """Worker function for parallel generation (runs in thread)."""
        agent = agent_factory()
        url = f"https://leetcode.com/problems/{slug}/"

        try:
            outcome = generate_one(self.db_path, agent, url)
            return outcome
        except Exception as e:
            from .models import GenerationOutcome
            return GenerationOutcome(False, None, None, str(e))

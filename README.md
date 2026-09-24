# LeetCode Interactive

Animated, step-by-step algorithm explanations for LeetCode problems. Fully static (GitHub Pages compatible), no backend required.

## Architecture

### Public Website (GitHub Pages)
- `index.html` — Problem explorer with search/filter
- `app.js` — Vanilla JS: load problems.json, filter by title/difficulty/topic
- `styles.css` — CSS tokens, light/dark mode, responsive to 400px
- `problems.json` — Public manifest: `{id, title, slug, difficulty, topics, file, url}`
- `problems/*.html` — Standalone interactive problem explanations (each is a complete HTML file)

### Local Generator (Developer-Only)
- **Database**: SQLite (WAL mode) at `database/leetcode.db` — tracks problem state, generation jobs, batches
- **LeetCode API**: GraphQL client (metadata-only: title, difficulty, topics, examples, constraints)
- **Agents**: Pluggable CLI interface — Claude Code / Codex / Gemini / Generic command template
- **CLI**: Interactive menu for single-problem generation, batch generation, validation, manifest rebuild
- **Pipeline**: Fetch → Normalize JSON → Generate (via AI) → Validate → Publish

## Quick Start

### Install
```bash
pip install -r requirements.txt
# Copy .env.example to .env (optional, for LeetCode rate-limit headroom)
cp .env.example .env
```

### View Site Locally
```bash
python -m http.server 8000
# Open http://localhost:8000
# Note: fetch('./problems.json') fails on file:// due to CORS — use a local server
```

### Run Generator
```bash
python -m generator
# Menu options:
# 1. Generate specific problem (not yet wired)
# 2. Generate batches (not yet wired)
# 3. Validate (not yet wired)
# 4. Rebuild manifest ✓ (working)
# 5. Show stats ✓ (working)
# 6. Exit
```

## Current Status

### ✓ Implemented
- Core database layer (models, SQLite schema, typed access)
- LeetCode API client (metadata-only)
- Agent abstraction (Base class, Claude / Codex / Gemini / Generic adapters)
- Problem fetching & normalization
- HTML validator (static checks, optional Playwright dynamic)
- Manifest generation (problems.json, generation-manifest.json)
- Frontend (search, filter, responsive)
- Sample problem page (Two Sum with full animation, keyboard controls, code highlighting)

### ⏳ Next Steps
1. **Implement generation_manager.py** — Full `generate_one()` workflow:
   - Fetch problem JSON
   - Reconcile duplicates (skip if already published, validate existing if orphaned)
   - Invoke agent (Claude, etc.)
   - Validate output
   - Move to problems/ + update DB + rebuild manifest

2. **Implement batch_manager.py** — Batch orchestration:
   - Select unpublished problems by difficulty
   - ThreadPoolExecutor with max_workers=5
   - Serialize DB writes through Lock (WAL safe)
   - Track batch progress + counters

3. **Wire CLI options 1-3** — Menu options for:
   - Option 1: prompt URL → agent selection → generate_one()
   - Option 2: prompt difficulty/count → run_batch() sequential/parallel
   - Option 3: validate all published problems

4. **Verify Agent Flags** — Test against real installed CLIs:
   - Claude: confirm `-p` / `--print` flags
   - Codex: verify `exec` subcommand + approval mode
   - Gemini: verify CLI flags + approval mode

5. **Tests** — pytest coverage:
   - Database schema, transitions, concurrency
   - LeetCode API mocking
   - Duplicate protection logic
   - Batch selection
   - Agent subprocess invocation

6. **Documentation** — README sections:
   - Adding new agents
   - Verified CLI command-line flags (currently best-effort)
   - DB schema & status lifecycle diagram
   - CI/CD integration

## Project Structure

```
leetcode-interactive/
├── index.html, app.js, styles.css, problems.json    # Public site
├── problems/1-two-sum.html                          # Sample problem
├── generator/
│   ├── models.py                  # Problem, Batch, GenerationJob, AgentResult
│   ├── database.py                # SQLite layer (WAL, typed access)
│   ├── leetcode_api.py            # GraphQL client
│   ├── problem_fetcher.py         # Fetch → normalize → save JSON
│   ├── agents/
│   │   ├── base.py                # BaseAgent ABC
│   │   ├── claude.py              # ClaudeAgent (verified)
│   │   ├── codex.py               # CodexAgent (best-effort)
│   │   ├── gemini.py              # GeminiAgent (best-effort)
│   │   └── generic.py             # GenericAgent (template-driven)
│   ├── generation_manager.py      # TODO: single-problem generation
│   ├── batch_manager.py           # TODO: batch orchestration + parallel
│   ├── manifest.py                # Rebuild problems.json, generation-manifest.json
│   ├── html_validator.py          # Static + optional Playwright checks
│   ├── config.py                  # Config + env loading
│   ├── utils.py                   # Slug/filename utilities
│   ├── cli.py                     # Interactive menu
│   └── __main__.py                # python -m generator entry
├── data/fetched/                  # Normalized problem JSON (committed)
├── database/                      # SQLite DB (gitignored)
├── scripts/                       # generate.py, rebuild_manifest.py, validate_all.py
├── tests/                         # pytest suite
├── requirements.txt
├── config.yaml
└── .env.example
```

## Key Decisions

- **Static-first**: Public site is 100% vanilla HTML/CSS/JS, no framework, no build step. Works on GitHub Pages.
- **Metadata-only**: LeetCode API fetches title, difficulty, topics, examples — never stores copyrighted problem HTML.
- **Pluggable agents**: Agent abstraction means any CLI (claude, codex, gemini, or custom) can be used interchangeably.
- **SQLite + WAL**: Single file DB, concurrent reads even during writes, thread-safe via Lock serialization.
- **Staging isolation**: Agents write to `data/staging/` only; only orchestrator moves validated HTML into `problems/`.
- **No auto-push**: Generator creates files and updates DB; developer reviews diffs and pushes manually.

## Verification

After completing "Next Steps" above:

```bash
# Test frontend + sample
python -m http.server 8000
# Open http://localhost:8000 → search "Two Sum" → click → animation works

# Test single problem generation (option 1)
python -m generator
# Select option 1 → paste https://leetcode.com/problems/two-sum/ → claude
# Confirm HTML generated, validated, published to problems/

# Test batch generation (option 2)
python -m generator
# Select option 2 → Medium → 1 batch → 5 size → sequential → confirm 5 generated

# Test parallel (option 2 + parallel mode)
# Confirm 5 concurrent workers, no database locks, all succeed

# Test validation (option 3)
# Confirm all published problems pass static checks

# Run tests
pytest -v
```

## License

MIT. See GitHub for details.

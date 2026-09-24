# LeetCode Interactive

Animated, step-by-step algorithm explanations for LeetCode problems. Fully static (GitHub Pages compatible), no backend required.

**Live Site**: https://karan-ksrk.github.io/leetcode-interactive/

## Architecture

### Public Website (GitHub Pages)
- `index.html` — Problem explorer with search/filter
- `app.js` — Vanilla JS: load problems.json, filter by title/difficulty/topic
- `styles.css` — CSS tokens, light/dark mode, responsive to 400px
- `problems.json` — Public manifest: `{id, title, slug, difficulty, topics, file, url}`
- `problems/*.html` — Standalone interactive problem explanations (each is a complete HTML file)

### Local Generator (Developer-Only)
- **Database**: SQLite (WAL mode) at `database/leetcode.db` — tracks problem state, generation jobs, batches
- **LeetCode API**: Vercel API (https://leetcode-api-pied.vercel.app) — fast, no auth required
- **Agents**: Pluggable CLI interface — Claude Code / Codex / Gemini / Generic command template
- **CLI**: Interactive menu for problem generation, batch generation, validation, manifest rebuild
- **Pipeline**: Fetch → Normalize JSON → Generate (via AI) → Validate → Publish

## Quick Start

### Prerequisites
- Python 3.10+
- Claude Code CLI installed (`claude` command available)

### Install
```bash
git clone https://github.com/karan-ksrk/leetcode-interactive.git
cd leetcode-interactive
pip install -r requirements.txt
```

### View Site Locally
```bash
python -m http.server 8000
# Open http://localhost:8000
# Note: fetch('./problems.json') fails on file:// due to CORS — use a local server
```

### Generate Problems
```bash
python -m generator

# Menu options:
# 1. Generate specific problem — paste URL or slug
# 2. Generate batches — select difficulty, count, sequential or parallel
# 3. Validate generated problems
# 4. Rebuild website manifest
# 5. Show generation statistics
# 6. Exit
```

**Example workflow:**
```bash
python -m generator
# Select: 2 (Generate batches)
# Difficulty: 1 (Easy)
# Batches: 1
# Batch size: 5
# Mode: 2 (Parallel)
# Agent: claude (default)
# → Generates 5 Easy problems in parallel, ~90s each
```

## Current Status

### ✓ Fully Implemented
- [x] Vercel LeetCode API client (instant fetch, no 403 blocks)
- [x] Problem fetching & normalization
- [x] Single problem generation (option 1)
- [x] Batch generation with parallel workers (option 2)
- [x] HTML validation (static checks)
- [x] Manifest generation (problems.json, generation-manifest.json)
- [x] Database layer (SQLite + WAL + concurrent safety)
- [x] Claude agent (subprocess + HTML extraction from stdout)
- [x] Frontend (search, filter, responsive, dark mode)
- [x] GitHub Pages deployment

### ⏳ Optional Enhancements
- Playwright dynamic validation (currently optional)
- Codex / Gemini agent implementations (scaffolded)
- Additional test coverage
- Pagination for large problem sets (500+)

## Project Structure

```
leetcode-interactive/
├── index.html, app.js, styles.css, problems.json    # Public site
├── problems/*.html                                  # Generated problem explanations
├── generator/
│   ├── cli.py                         # Interactive menu
│   ├── __main__.py                    # python -m generator entry
│   ├── models.py                      # Problem, Batch, GenerationJob
│   ├── database.py                    # SQLite layer (WAL, concurrent-safe)
│   ├── leetcode_api.py                # Vercel API client
│   ├── problem_fetcher.py             # Fetch → normalize → save JSON
│   ├── generation_manager.py          # Single-problem workflow
│   ├── batch_manager.py               # Batch orchestration + parallel
│   ├── manifest.py                    # Rebuild problems.json
│   ├── html_validator.py              # Static validation
│   ├── config.py                      # Config + env loading
│   ├── agents/
│   │   ├── base.py                    # BaseAgent ABC
│   │   └── claude.py                  # ClaudeAgent implementation
│   └── prompts/
│       └── leetcode-animator.md       # Instruction template for Claude
├── data/fetched/                      # Normalized problem JSON (committed)
├── database/                          # SQLite DB (gitignored at runtime)
├── generation-manifest.json           # Generation statistics
├── requirements.txt                   # Python dependencies
└── .gitignore                         # Excludes .db, .env, staging, cache
```

## How It Works

### Generation Pipeline

1. **Fetch**: Vercel API returns problem metadata (instant, no auth)
2. **Normalize**: Convert to internal schema, save as JSON to `data/fetched/`
3. **Generate**: Claude CLI creates interactive HTML from problem + instruction template
4. **Validate**: Static checks (valid HTML, has controls)
5. **Publish**: Move HTML to `problems/`, update DB, rebuild manifest

### Batch Mode (Parallel)

- Selects N unpublished problems of given difficulty
- Submits each to ThreadPoolExecutor (default 5 workers)
- Each worker calls the pipeline independently
- All DB writes serialized through threading.Lock (safe with SQLite WAL)
- Manifest rebuilt once at the end

### Database Schema

- **problems**: id, leetcode_id, title, slug, difficulty, topics, status, generation_agent, html_file, etc.
- **batches**: batch_number, difficulty, generated_count, failed_count, status
- **generation_jobs**: problem_id, agent, status, duration, error

Status lifecycle: `pending → fetching → fetched → generating → validating → published` (or `failed` at any step)

## Dependencies

From `requirements.txt`:
- `requests` — HTTP client for Vercel API
- `pyyaml` — Config file parsing
- `python-dotenv` — Environment variable loading
- `beautifulsoup4` — HTML parsing (optional)
- `playwright` — Dynamic validation (optional, `pip install -e .[dynamic-validation]`)

No heavy dependencies needed for core functionality.

## Known Limitations

- **File URLs**: Frontend fetch fails on `file://` (CORS). Use `python -m http.server 8000` locally.
- **Rate limiting**: Vercel API occasionally throttles. Add exponential backoff if needed.
- **Validation**: Currently only checks for basic HTML structure and controls. Playwright validation is optional.
- **Claude timeout**: Generation takes ~90s per problem (Claude model latency). Batch generation is parallel to minimize wall time.

## Future Ideas

- [ ] Pagination or infinite scroll for 500+ problems
- [ ] Search via problem tags/difficulty server-side
- [ ] User analytics (which problems viewed most)
- [ ] Problem difficulty recommendations
- [ ] Lazy-load HTML to speed up initial load
- [ ] API endpoint for problems (currently just static JSON)

## License

MIT. See GitHub for details.

# git-trend-sync Design Spec

## Problem

The current system ranks repos by total stars, which surfaces established projects but misses what's actually trending right now. The user wants to:

1. Detect **real development activity** — repos with high commit activity, not just star counts
2. Get **actionable recommendations** — how to apply trending tools to their own projects
3. Access everything from **Claude Code slash commands** — not just CLI scripts

## Goals

- Replace static star ranking with activity-based trending (30-day commits)
- Filter out repos with < 1,000 stars (noise reduction)
- Auto-recommend trending tools for the user's project, matched to their actual codebase
- Deep-dive analysis on demand via CLI or `/trend-apply`
- Track 12 categories covering the full AI ecosystem
- Slash commands: `/trend` (view report) and `/trend-apply` (project recommendations)

## Non-Goals

- Real-time monitoring (daily batch is sufficient)
- Social media scraping (Hacker News, Reddit, X)
- Building a web dashboard

---

## Architecture

### Three Independent Pipelines

```
Pipeline 1: Trend Collection (daily, automated)
  collect.py → trending.py → analyze → report
  Output: reports/YYYY-MM-DD.md

Pipeline 2: Project Recommendations (after Pipeline 1, automated)
  scan_project.py → recommend.py
  Output: reports/YYYY-MM-DD-recommendations.md

Pipeline 3: Deep Apply Analysis (manual, on-demand)
  apply.py --repo <name> --project <path>
  Output: docs/trend-apply/YYYY-MM-DD-<repo>.md
```

### Data Flow

```
GitHub API ──→ collect.py (stars>1000, pushed within 7d)
                    │
                    ▼
              raw.json (per category, up to 30 repos)
                    │
                    ▼
              trending.json (ranked by 30-day commits, top 10 per category)
                    │
                    ▼
              analysis/*.json (qualitative, via analyze.py)
                    │
                    ▼
              reports/YYYY-MM-DD.md
                    │
                    ├── history.py (append to trend history)
                    │
                    ▼ (if project config exists)
              reports/YYYY-MM-DD-recommendations.md
```

---

## Component Design

### 1. Data Collection (`src/collect.py`)

Fetches repos from GitHub with hard filters applied at query time:

Query template:
```
topic:{topic} stars:>1000 pushed:>{7_days_ago}
```

Per category: fetch up to 30 repos to ensure enough candidates for activity ranking, then trim to top 10.

Saves raw results to `data/YYYY-MM-DD/raw.json`.

### 2. Trending Calculator (`src/trending.py`)

Core responsibility: rank repos by development activity within each category.

**Primary ranking metric:** 30-day commit count (`commits_30d`)

**Secondary signals used in activity score:**

| Metric | Role |
|--------|------|
| `commits_30d` | Primary sort key — actual development pace |
| `days_since_push` | Recency penalty — recently pushed scores higher |
| `age_days` | Newness context — newer repos get a visibility note |
| `stars` | Credibility floor (already gated at >1,000) |

**New entry detection:** If a repo appears in today's data but not in the previous run's top 10 for that category, mark as `is_new_entry: true`.

**Status labels:**
- `NEW ENTRY` — first appearance in the tracked top 10
- `RISING` — moved up in ranking from previous run
- `STABLE` — rank roughly unchanged
- `COOLING` — dropped in ranking

**Output:** `data/YYYY-MM-DD/trending.json`
```json
{
  "AI Agent Framework": [
    {
      "name": "some-repo",
      "full_name": "org/some-repo",
      "activity_score": 8.7,
      "commits_30d": 347,
      "stars": 5230,
      "days_since_push": 1,
      "age_days": 85,
      "is_new_entry": true,
      "status": "NEW ENTRY"
    }
  ]
}
```

**Ranking:** Within each category, sort by `commits_30d` descending. Top 10 go into the report.

### 3. Trend History (`src/history.py`)

Maintains a running record of which repos appeared in each daily top 10, enabling:
- New entry detection (repo not seen before)
- Rising/cooling status (rank comparison to previous run)
- Multi-day comparison tables in the report

**Storage:** `data/history.json` — appended after each run.

### 4. Analysis (`src/analyze.py`)

Qualitative analysis for each trending repo. Prompt context includes:
- Activity score and 30-day commit count
- Whether it's a new entry
- Stars and repo age

Analysis addresses: "Why is this actively developed now? What problem is it solving?"

### 5. Report Generator (`src/report.py`)

Updated report format showing activity-based ranking:

```markdown
# git-trend-sync Report — 2026-03-24

## AI Agent Framework

| # | Repository | Activity | Stars | Commits (30d) | Last Push | Age | Status |
|---|-----------|----------|-------|---------------|-----------|-----|--------|
| 1 | some-repo | 🔥 8.7 | 5,230 | 347 | 1d ago | 85d | NEW ENTRY |
| 2 | other-repo | 📈 6.8 | 45,000 | 189 | 3d ago | 2y | RISING |
```

Includes comparison table showing rank changes from previous run where history is available.

### 6. Project Scanner (`src/scan_project.py`)

Reads the user's project to build a context profile for category-aware recommendations.

**Auto-detection (reads from project root):**
- `README.md` — project description
- `package.json` / `pyproject.toml` / `requirements.txt` / `go.mod` — tech stack and dependencies
- `src/` or `lib/` directory structure — architecture patterns
- `.env.example` — external services used

**User config (`git-trend-sync.yaml` in project root):**
```yaml
project:
  name: "My AI App"
  description: "A conversational AI assistant with RAG pipeline"
  tech_stack: ["python", "fastapi", "langchain", "chromadb"]
  interests: ["better RAG", "agent orchestration", "code generation"]
  exclude: ["java", "go"]
```

**Category recommendation:** Based on detected stack and interests, `scan_project.py` ranks the 12 categories by relevance to the project. This focuses recommendations — a project with no browser automation use case won't be shown Browser Agent trends.

**Output:** A project profile JSON used by the recommender:
```json
{
  "name": "My AI App",
  "description": "...",
  "detected_stack": ["python", "fastapi", "langchain", "chromadb"],
  "declared_interests": ["better RAG", "agent orchestration"],
  "current_dependencies": ["langchain==0.1.0", "chromadb==0.4.0"],
  "relevant_categories": ["RAG Framework", "AI Agent Framework", "Multi-Agent"],
  "architecture_hints": ["uses vector store", "has API endpoints", "agent pattern detected"]
}
```

### 7. Recommender (`src/recommend.py`)

Takes trending repos + project profile → generates targeted recommendations.

**Matching logic:**
1. **Category filter:** Only consider repos in categories flagged as relevant by `scan_project.py`
2. **Stack compatibility:** Does the repo's language/ecosystem match the project?
3. **Interest alignment:** Does the repo solve a problem in the project's declared interests?
4. **Dependency overlap:** Is the repo a potential replacement or complement for current dependencies?

**Output:** `reports/YYYY-MM-DD-recommendations.md`

Relevance tiers:
- **High Relevance** — direct stack match + category match
- **Worth Watching** — category match but different stack or early stage
- **New Entrant** — new repos that match interests (flagged as higher risk)

### 8. Deep Apply Analysis (`src/apply.py`)

On-demand deep analysis for a specific trending repo against a specific project.

**Usage:**
```bash
python apply.py --repo ragflow --project /path/to/my/project
```

**Process:**
1. Read the trending repo's README, docs, and API surface from collected data
2. Scan the target project's full structure (deeper than `scan_project.py`)
3. Generate a detailed design document

**Output:** `docs/trend-apply/YYYY-MM-DD-<repo-name>.md`

### 9. Claude Code Slash Commands

**`/trend`** — Show today's trend report
```
Location: .claude/commands/trend.md
Reads the latest report from {project_root}/reports/ and summarizes
key trends. Highlights NEW ENTRY and RISING repos. Shows comparison
table if history is available.
```

**`/trend-apply`** — Analyze current project against trends and generate design docs
```
Location: .claude/commands/trend-apply.md

Steps:
1. Scan current project (README, dependencies, directory structure)
2. Load latest trending.json from git-trend-sync data directory
3. Match trending repos against project stack and interests
4. Decision gate: if nothing relevant, report "No actionable trends today" and stop
5. For each relevant repo: generate design doc at docs/trend-apply/YYYY-MM-DD-<repo>.md
   - Why This Matters (activity data + relevance to this project)
   - Current State (which files/modules are affected)
   - Proposed Changes (architecture, new dependencies)
   - Migration Path (step-by-step, before/after code examples)
   - Risks & Trade-offs
   - Effort Estimate (small/medium/large)
   - Verdict: YES (adopt now) / WAIT (monitor) / NO (not worth it)
6. Print summary of what was found and what docs were generated
```

---

## Directory Structure

```
git-trend-sync/
├── src/
│   ├── collect.py        # GitHub data collection (stars>1000, 7d active)
│   ├── trending.py       # Activity-based trend scoring (30-day commits)
│   ├── metrics.py        # Quantitative metrics (kept for compatibility)
│   ├── analyze.py        # Qualitative analysis
│   ├── report.py         # Report generation (activity format)
│   ├── scan_project.py   # Project context scanner + category recommendation
│   ├── recommend.py      # Project-trend matcher
│   ├── apply.py          # Deep apply analysis
│   ├── history.py        # Trend history tracking (new entry / rising detection)
│   └── publish.sh        # Git commit & push
├── config/
│   ├── categories.yaml   # 12 category & topic config
│   └── prompts/
│       ├── analyze.md    # Trend analysis prompt
│       ├── recommend.md  # Recommendation prompt
│       └── apply.md      # Deep apply prompt
├── data/
│   ├── history.json      # Running history of top-10 appearances
│   └── YYYY-MM-DD/       # Daily analysis data (raw.json, trending.json, analysis/)
├── reports/              # Generated reports
├── .claude/
│   └── commands/
│       ├── trend.md
│       └── trend-apply.md
├── run.py                # Main orchestrator
├── git-trend-sync.yaml.example
└── requirements.txt
```

---

## Tracked Categories (12)

| Category | Description |
|:---------|:------------|
| 🧠 **AI Agent Framework** | General-purpose agent frameworks |
| 🔍 **RAG Framework** | Retrieval-augmented generation |
| 🤝 **Multi-Agent** | Multi-agent orchestration |
| 💻 **Coding Assistant** | AI coding tools |
| ⚙️ **AI Infrastructure** | LLM serving, gateways, inference |
| 🌐 **Browser Agent** | Web browser automation agents |
| 🔌 **MCP** | Model Context Protocol ecosystem |
| 🔄 **AI Workflow** | Visual AI workflow builders |
| 🎙️ **Voice Agent** | Voice/realtime AI agents |
| 🧩 **Knowledge Management** | Knowledge graphs, vector DBs, memory |
| 📊 **AI Observability** | LLM monitoring, evaluation, prompts |
| 🖥️ **Computer Use Agent** | Desktop/OS automation agents |

---

## Run Modes

```bash
# Full daily pipeline (collect + trend + analyze + report + recommend)
python run.py

# Report only, no recommendations
python run.py --no-recommend

# Skip analysis
python run.py --skip-analysis

# Recommendations for a specific project
python run.py --project /path/to/project

# Regenerate report from existing data
python run.py --report-only

# Deep apply analysis for a specific repo
python src/apply.py --repo ragflow --project /path/to/project

# No git push
python run.py --no-push
```

---

## Edge Cases

- **No prior history:** New entry detection falls back to "first run" state. Report notes that comparison data will be available from the next run.
- **Repo disappears from search:** Mark as "DROPPED" in history if it was in yesterday's top 10 but not today's. Keep in history record.
- **API rate limit:** Respect 5,000/hour with token. Each run uses ~50-100 calls. Safe margin.
- **Project has no git-trend-sync.yaml:** `scan_project.py` still works with auto-detection only. Category recommendation will be less precise but still useful.
- **Repo with < 1,000 stars:** Hard-filtered at collection time. The 1,000 threshold is a gate applied before any ranking.

# AI Agent Trend Report v2 — Design Spec

## Problem

The current system ranks repos by total stars, which surfaces established projects but misses what's actually trending right now. The user wants to:

1. Detect **velocity** — repos gaining stars fast, not just repos with many stars
2. Get **actionable recommendations** — how to apply trending tools to their own projects
3. Access everything from **Claude Code slash commands** — not just CLI scripts

## Goals

- Replace static star ranking with velocity-based trending
- Filter out repos with < 1,000 stars (noise reduction)
- Provide Day 1 value before velocity data accumulates
- Auto-recommend trending tools for the user's project
- Deep-dive analysis on demand via CLI or `/trend-apply`
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
  Output: reports/apply-<repo>-YYYY-MM-DD.md
```

### Data Flow

```
GitHub API ──→ snapshots/YYYY-MM-DD.json (daily star counts)
                    │
                    ├── compare with previous snapshot
                    │         │
                    ▼         ▼
              raw.json    velocity.json
                    │         │
                    ▼         ▼
              metrics.json (instant metrics + velocity blend)
                    │
                    ▼
              analysis/*.json (qualitative)
                    │
                    ▼
              reports/YYYY-MM-DD.md
                    │
                    ▼ (if project config exists)
              reports/YYYY-MM-DD-recommendations.md
```

---

## Component Design

### 1. Data Collection (`src/collect.py` — modified)

**Change:** Add `stars:>1000` filter and `pushed:>{7_days_ago}` to search queries.

Query template:
```
topic:{topic} stars:>1000 pushed:>{7_days_ago}
```

Per category: fetch up to 30 repos (to capture enough for velocity ranking, then trim to top 10 trending).

**Snapshot storage:** After collection, save a snapshot file:
```
data/snapshots/YYYY-MM-DD.json
{
  "date": "2026-03-23",
  "repos": {
    "langchain-ai/langchain": {"stars": 130632, "forks": 21000},
    "langgenius/dify": {"stars": 133987, "forks": 18500},
    ...
  }
}
```

### 2. Trending Calculator (`src/trending.py` — new)

Core responsibility: compute trend scores from snapshots + instant metrics.

**Instant metrics (Day 1, no history needed):**

| Metric | Formula | Weight (Day 1) |
|--------|---------|----------------|
| Stars per day avg | `stars / (today - created_at).days` | 0.3 |
| Recent activity | `commits_30d * 10 + max(0, 30 - days_since_push)` | 0.25 |
| Newness boost | `max(0, 1 - age_days/180) * 10` (bonus for < 6 months old) | 0.2 |
| Issue velocity | recent open issues / 30 days | 0.1 |
| Release frequency | releases in last 90 days | 0.15 |

**Velocity metrics (Day 2+, from snapshots):**

| Metric | Formula | Weight |
|--------|---------|--------|
| Daily star delta | `today_stars - yesterday_stars` | 0.4 |
| 7-day moving avg | `avg(daily_deltas[-7:])` | 0.3 |
| Acceleration | `7d_avg - 30d_avg` (speeding up?) | 0.3 |

**Blending strategy:**
```python
if days_of_data == 0:
    trend_score = instant_score
elif days_of_data < 7:
    velocity_weight = days_of_data / 7
    trend_score = instant_score * (1 - velocity_weight) + velocity_score * velocity_weight
else:
    trend_score = instant_score * 0.3 + velocity_score * 0.7
```

**Output:** `data/YYYY-MM-DD/trending.json`
```json
{
  "AI Agent Framework": [
    {
      "name": "some-repo",
      "full_name": "org/some-repo",
      "trend_score": 8.7,
      "instant_score": 7.2,
      "velocity_score": 9.5,
      "star_delta_1d": 127,
      "star_delta_7d_avg": 95.3,
      "is_new_entry": true,
      "stars_per_day_avg": 45.2,
      "age_days": 85,
      ...metrics
    }
  ]
}
```

**Ranking:** Within each category, sort by `trend_score` descending. Top 10 go into the report.

**New entry detection:** If a repo appears in today's snapshot but not in any previous snapshot, mark as `is_new_entry: true` and highlight in the report.

### 3. Analysis (`src/analyze.py` — modified)

Same structure as current, but the prompt template gets additional context:
- Trend score and velocity data
- Whether it's a new entry
- Stars per day average

The analysis should specifically address: "Why is this trending now? What changed?"

### 4. Report Generator (`src/report.py` — modified)

Updated report format:

```markdown
# AI Agent Trend Report — 2026-03-24

## Trending: AI Agent Framework

| # | Repository | Trend | Stars | +1d | +7d avg | Age | Status |
|---|-----------|-------|-------|-----|---------|-----|--------|
| 1 | some-repo | 🔥 8.7 | 5,230 | +127 | +95/d | 85d | NEW ENTRY |
| 2 | other-repo | 📈 7.3 | 45,000 | +89 | +72/d | 2y | RISING |
```

Status labels:
- `NEW ENTRY` — first time appearing in the tracked list
- `RISING` — trend score increased from yesterday
- `STABLE` — trend score roughly same
- `COOLING` — trend score decreased

### 5. Project Scanner (`src/scan_project.py` — new)

Reads the user's project to build a context profile.

**Auto-detection (reads from project root):**
- `README.md` — project description
- `package.json` / `pyproject.toml` / `requirements.txt` / `go.mod` — tech stack & dependencies
- `src/` or `lib/` directory structure — architecture patterns
- `.env.example` — external services used

**User config (`ai-trend.yaml` in project root):**
```yaml
project:
  name: "My AI App"
  description: "A conversational AI assistant with RAG pipeline"
  tech_stack: ["python", "fastapi", "langchain", "chromadb"]
  interests: ["better RAG", "agent orchestration", "code generation"]
  exclude: ["java", "go"]  # not interested in these ecosystems
```

**Output:** A project profile JSON used by the recommender.

```json
{
  "name": "My AI App",
  "description": "...",
  "detected_stack": ["python", "fastapi", "langchain", "chromadb"],
  "declared_interests": ["better RAG", "agent orchestration"],
  "current_dependencies": ["langchain==0.1.0", "chromadb==0.4.0"],
  "architecture_hints": ["uses vector store", "has API endpoints", "agent pattern detected"]
}
```

### 6. Recommender (`src/recommend.py` — new)

Takes trending repos + project profile → generates recommendations.

**Matching logic:**
1. **Stack compatibility:** Does the trending repo's language/ecosystem match the project? (e.g., Python repo → Python project)
2. **Interest alignment:** Does the repo's category match declared interests?
3. **Dependency overlap:** Is the trending repo a potential replacement/complement for current dependencies?
4. **Architecture fit:** Does the repo solve a pattern the project already uses?

**Output:** `reports/YYYY-MM-DD-recommendations.md`

```markdown
# Recommendations for "My AI App" — 2026-03-24

## High Relevance

### 🔥 ragflow (Trend: 8.7)
**Why it matters to you:** Your project uses LangChain for RAG. RAGFlow offers
a visual pipeline builder that could simplify your current retrieval chain.
**How to evaluate:** Compare retrieval accuracy on your dataset with your
current LangChain setup.
**Effort:** Medium — requires migrating vector store connector

## Worth Watching

### 📈 some-agent (Trend: 7.1)
**Why it matters to you:** ...
```

Relevance tiers:
- **High Relevance** — direct stack match + interest match
- **Worth Watching** — interest match but different stack or early stage
- **New Entrant** — brand new repos that match interests (high risk, high reward)

### 7. Deep Apply Analysis (`src/apply.py` — new)

On-demand deep analysis for a specific trending repo against a specific project.

**Usage:**
```bash
python apply.py --repo ragflow --project /path/to/my/project
```

**Process:**
1. Read the trending repo's README, docs, and API surface from collected data
2. Scan the target project's full structure (deeper than scan_project.py)
3. Generate a detailed report covering:
   - What this repo does and why it's trending
   - Specific files/modules in your project that would be affected
   - Migration path from current tools (if replacing something)
   - Code examples showing integration
   - Risks and trade-offs
   - Estimated effort (small/medium/large)

**Output:** `reports/apply-<repo>-YYYY-MM-DD.md`

### 8. Claude Code Slash Commands

Two slash commands registered as Claude Code custom commands.

**`/trend`** — Show today's trend report
```
Location: .claude/commands/trend.md
Prompt: Read the latest report from {project_root}/reports/ and summarize
the key trends. Highlight NEW ENTRY and RISING repos. If recommendations
exist, show them too.
```

**`/trend-apply`** — Analyze current project against trends
```
Location: .claude/commands/trend-apply.md
Prompt: Run the project scanner on the current working directory, then
match against the latest trending data. Generate actionable recommendations
for how to apply trending tools to this project.
```

---

## Directory Structure (Updated)

```
ai-trend/
├── src/
│   ├── collect.py        # GitHub data collection (modified: stars>1000 filter)
│   ├── trending.py       # NEW: velocity & trend score calculation
│   ├── metrics.py        # Quantitative metrics (kept for compatibility)
│   ├── analyze.py        # Qualitative analysis
│   ├── report.py         # Report generation (modified: trend format)
│   ├── scan_project.py   # NEW: project context scanner
│   ├── recommend.py      # NEW: project-trend matcher
│   ├── apply.py          # NEW: deep apply analysis
│   └── publish.sh        # Git commit & push
├── config/
│   ├── categories.yaml   # Category & topic config
│   └── prompts/
│       ├── analyze.md    # Trend analysis prompt
│       ├── recommend.md  # Recommendation prompt
│       └── apply.md      # Deep apply prompt
├── data/
│   ├── snapshots/        # NEW: daily star count snapshots
│   └── YYYY-MM-DD/       # Daily analysis data
├── reports/              # Generated reports
├── .claude/
│   └── commands/         # NEW: Claude Code slash commands
│       ├── trend.md
│       └── trend-apply.md
├── run.py                # Main orchestrator (modified)
├── ai-trend.yaml.example # NEW: project config template
└── requirements.txt
```

---

## Run Modes

```bash
# Full daily pipeline (collect + trend + analyze + report + recommend)
python run.py

# Report only, no recommendations
python run.py --no-recommend

# Skip analysis
python run.py --skip-analysis

# Deep apply analysis for a specific repo
python apply.py --repo ragflow --project /path/to/project

# No git push
python run.py --no-push
```

---

## Edge Cases

- **Day 1 (no snapshots):** Use instant metrics only. Report clearly states "Velocity data will be available from tomorrow."
- **Repo disappears from search:** Keep in snapshot history. Mark as "DROPPED" if it was in yesterday's top 10 but not today's.
- **API rate limit:** Respect 5,000/hour with token. Each run uses ~50-100 calls. Safe margin.
- **Project has no ai-trend.yaml:** scan_project.py still works with auto-detection only. Recommendations will be less targeted but still useful.
- **Repo with < 1,000 stars suddenly gains 500 in a day:** Still filtered out. The 1,000 threshold is a hard gate to avoid noise.

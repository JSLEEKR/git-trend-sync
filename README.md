<div align="center">

# 🔄 git-trend-sync

### Sync AI trends to your project

[![GitHub Stars](https://img.shields.io/github/stars/JSLEEKR/git-trend-sync?style=for-the-badge&logo=github&color=yellow)](https://github.com/JSLEEKR/git-trend-sync/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Claude](https://img.shields.io/badge/powered%20by-Claude%20Code-D4A574?style=for-the-badge)](https://claude.ai)

<br/>

**Detects what's actually trending — not just popular — in the AI agent ecosystem**

Activity-based scoring + Project-specific recommendations + Claude Code slash commands

[📊 Latest Report](reports/) · [🔧 Setup Guide](#-quick-start)

</div>

---

## Why This Exists

The AI ecosystem moves fast. New frameworks, tools, and patterns emerge weekly. Yesterday's best practice is today's legacy code.

**git-trend-sync** keeps your project in sync with what matters. It scans 12 categories of AI repositories, ranks them by real development activity, and tells you — specifically for YOUR codebase — what's worth adopting and what's noise.

Think of it as a daily briefing: "Here's what's actively being built in the AI world, and here's what actually applies to your project."

- **12 categories tracked** — from AI agents to MCP servers, browser automation to voice AI
- **Activity-ranked** — sorted by 30-day commits, not just stars
- **Project-aware** — scans your code and only recommends what fits your stack
- **Design docs on demand** — `/trend-apply` generates integration plans, not just links

Stop manually browsing GitHub. Let the trends sync to you.

<!-- TREND-START -->
### Today's Top Trending (2026-04-18)

| # | Repository | Category | Score | Signal | Detail |
|---|-----------|----------|-------|--------|--------|
| 1 | [rtk](https://github.com/rtk-ai/rtk) | Coding Assistant | 9.2 | 🆕 newcomer | 85d, 338.6/day |
| 2 | [voicebox](https://github.com/jamiepine/voicebox) | Voice Agent | 9.0 | 🆕 newcomer | 82d, 245.9/day |
| 3 | [code-review-graph](https://github.com/tirth8205/code-review-graph) | Knowledge Management | 9.0 | 🆕 newcomer | 50d, 217.3/day |
| 4 | [antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | Coding Assistant | 8.7 | 🆕 newcomer | 93d, 362.9/day |
| 5 | [everything-claude-code](https://github.com/affaan-m/everything-claude-code) | MCP | 8.4 | 📈 momentum | 189 commits/7d |
| 6 | [graphify](https://github.com/safishamsi/graphify) | Knowledge Management | 8.4 | 🆕 newcomer | 14d, 2104.8/day |
| 7 | [agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh) | Multi-Agent | 8.3 | 🆕 newcomer | 43d, 158.1/day |
| 8 | [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | Multi-Agent | 8.3 | 📈 momentum | 198 commits/7d |
| 9 | [mempalace](https://github.com/MemPalace/mempalace) | MCP | 8.3 | 🆕 newcomer | 13d, 3668.6/day |
| 10 | [caveman](https://github.com/JuliusBrussee/caveman) | AI Observability | 8.3 | 🆕 newcomer | 14d, 2662.6/day |

> Last updated: 2026-04-18 — [Full Report](reports/2026-04-18.md)
<!-- TREND-END -->

---

## 📋 What is this?

An automated system that tracks **development activity** across 12 AI agent categories and recommends trending tools that are relevant to **your** project.

### Why activity, not just stars?

| Metric | What it finds | Problem |
|--------|--------------|---------|
| ⭐ Total stars | Established projects | Misses actively developed new tools |
| 🔥 **30-day commits** | Tools being actively built *right now* | Catches real momentum |

### Three Pipelines

| Pipeline | When | What |
|----------|------|------|
| 🔍 **Trend Collection** | Daily (automated) | Collects repos, computes activity scores, generates report |
| 🎯 **Recommendations** | After collection | Scans your project, matches with trends, suggests what's relevant |
| 🔬 **Deep Analysis** | On-demand | Detailed integration design doc for a specific trending repo |

### Categories

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

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- GitHub Personal Access Token

### Setup

```bash
git clone https://github.com/JSLEEKR/git-trend-sync.git
cd git-trend-sync
pip install -r requirements.txt
echo "GITHUB_TOKEN=ghp_your_token_here" > .env
```

### Run

```bash
# Full pipeline (collect → trending → analysis → report → recommendations)
python run.py

# Skip analysis
python run.py --skip-analysis

# Recommendations for a specific project
python run.py --project /path/to/my/project

# Skip recommendations
python run.py --no-recommend

# Regenerate report from existing data
python run.py --report-only

# Deep analysis for a specific repo
python src/apply.py --repo ragflow --project /path/to/my/project
```

---

## ⚡ Claude Code Slash Commands

Install slash commands by placing this repo's `.claude/commands/` in your project:

### `/trend` — View today's trends

Shows a summary of trending repos: new entries, rising repos, top performers.

### `/trend-apply` — Smart project recommendations

Scans your current project's code, matches against today's trending data, and:
- If relevant trends found → generates a **design document** with integration plan
- If nothing relevant → tells you "nothing today" with explanation

Design docs are saved to `docs/trend-apply/YYYY-MM-DD-<repo>.md` with:
- Why the trending repo matters to your project
- Which files would be affected
- Migration path with code examples
- Risks, effort estimate, and verdict (adopt/wait/skip)

---

## 📊 How Trending Works

Repos are ranked by **development activity** — the number of commits in the last 30 days. This surfaces tools that are actively being built and improved, not just popular repos that stopped evolving.

### Filters
- **Stars > 1,000** — eliminates noise from toy projects
- **Pushed within 7 days** — must be recently active
- **30-day commit count** — primary ranking signal

### Report Format

| # | Repository | Activity | Stars | Commits (30d) | Last Push | Age | Status |
|---|-----------|----------|-------|---------------|-----------|-----|--------|
| 1 | some-repo | 🔥 9.2 | 5,230 | 347 | 1d ago | 85d | NEW ENTRY |
| 2 | other-repo | 📈 6.8 | 45,000 | 189 | 3d ago | 2y | ACTIVE |

---

## 🎯 Project Recommendations

Add `git-trend-sync.yaml` to your project root for targeted recommendations:

```yaml
project:
  name: "My AI App"
  description: "A conversational AI assistant with RAG pipeline"
  tech_stack: ["python", "fastapi", "langchain"]
  interests: ["better RAG", "agent orchestration", "code generation"]
  exclude: ["java", "go"]
```

Without config, the scanner auto-detects your stack from `requirements.txt`, `package.json`, etc.

---

## 📁 Project Structure

```
git-trend-sync/
├── src/
│   ├── collect.py        # GitHub data collection (stars>1000, 7d active)
│   ├── trending.py       # Activity-based trend scoring
│   ├── metrics.py        # Legacy quantitative metrics
│   ├── analyze.py        # Qualitative analysis engine
│   ├── analyze.sh        # Shell-based analysis runner
│   ├── report.py         # Trend report generation
│   ├── scan_project.py   # Project context scanner
│   ├── recommend.py      # Project-trend matcher
│   ├── apply.py          # Deep integration analysis
│   ├── history.py        # Trend history tracking
│   ├── badge.py          # Shields.io badge generation
│   ├── readme_update.py  # README trend table updater
│   ├── star_history.py   # Star growth visualization
│   └── publish.sh        # Git commit & push
├── config/
│   ├── categories.yaml   # Category & topic config
│   └── prompts/          # Analysis prompt templates
├── data/
│   └── YYYY-MM-DD/       # Daily analysis data
├── reports/              # Generated reports
├── .claude/commands/     # /trend and /trend-apply
├── run.py                # Main orchestrator
└── git-trend-sync.yaml.example
```

---

## Architecture

### Data Flow

```
GitHub Topics API
      |
      v
  collect.py ──────> data/{date}/raw.json
      |
      v
  trending.py ─────> data/{date}/trending.json
      |
      v
  metrics.py ──────> data/{date}/metrics.json
      |
      v
  analyze.py ──────> data/{date}/analysis/{category}.json
      |
      v
  report.py ───────> reports/{date}.md
      |
      v
  recommend.py ────> reports/{date}-recommendations.md
      |
      v
  apply.py ────────> reports/apply-{repo}-{date}.md
```

### Scoring Algorithm

Each repository receives an **activity score** (0-10) based on 30-day commit count, normalized within its category:

```
score = (repo_commits - category_min) / (category_max - category_min) * 10
```

Repos with identical commit counts are ranked by star count as tiebreaker.

### Recommendation Matching

When scanning your project, git-trend-sync builds a compatibility profile:

| Signal | Points | How Detected |
|--------|--------|-------------|
| Stack match | +2 | Your language/ecosystem matches repo's primary language |
| Interest match | +2 | Keywords from your config or dependencies overlap with repo topics |
| Dependency overlap | +1 | Repo name appears in your current dependencies |
| New entry | +1 | Repository is less than 6 months old |

Repos scoring 4+ are **High Relevance**, 2+ are **Worth Watching**.

---

## Supported Stack Detection

git-trend-sync auto-detects your project's tech stack by scanning dependency manifests:

| Language | Manifest Files |
|----------|---------------|
| Python | `requirements.txt`, `pyproject.toml`, `setup.py` |
| JavaScript/TypeScript | `package.json` |
| Go | `go.mod` |
| Rust | `Cargo.toml` |
| Java | `pom.xml`, `build.gradle` |
| Ruby | `Gemfile` |
| PHP | `composer.json` |
| Elixir | `mix.exs` |

Framework detection maps 50+ known packages to labels (e.g., `langchain` -> LLM Framework, `fastapi` -> Web Framework).

---

## Reports Generated

Each daily run produces multiple reports:

| Report | File | Content |
|--------|------|---------|
| Main trend report | `reports/{date}.md` | Per-category trending tables with analysis |
| Activity history | `reports/{date}-history.md` | Sparkline charts showing repo momentum |
| Star growth | `reports/{date}-star-history.md` | 30-day star growth visualization |
| Badges | `reports/{date}-badges.md` | Copy-paste shields.io badges for trending repos |
| Recommendations | `reports/{date}-recommendations.md` | Project-specific tool suggestions |
| Deep analysis | `reports/apply-{repo}-{date}.md` | Integration design doc for a specific repo |

### Example Activity Sparkline

```
langchain  ▅▆▇▇█▇▆▅▅▆▆▇▇█████▇▆▆▇▇█▇▆▅▅▆▇█  9.2
browser-use ▁▂▃▃▅▇▇██████▇▇▆▅▅▆▇▇████████▇▇█  8.7
vllm        ▃▃▅▆▇▇█▇▆▅▄▃▃▅▆▇▇█▇▆▅▅▆▇▇█▇▆▅▅▆  7.4
```

---

## ⚙️ Automation

### GitHub Actions (Recommended)

The included workflow (`.github/workflows/daily-trend.yml`) runs daily at 09:00 UTC:

1. Collects trending data from GitHub API
2. Generates reports and updates README
3. Commits results and pushes automatically
4. Posts a notification comment on a pinned GitHub issue

To enable:
1. Go to **Settings > Secrets and variables > Actions**
2. Add `GH_PAT` with a GitHub Personal Access Token (read:repo scope)
3. The workflow triggers daily or via **Actions > Daily Trend Sync > Run workflow**

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task -> Name: `git-trend-sync`
3. Trigger: Daily at your preferred time
4. Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\git-trend-sync\run.py`
5. Done

### cron (Linux/macOS)

```bash
# Run daily at 6 PM
0 18 * * * cd /path/to/git-trend-sync && python run.py --skip-analysis >> /var/log/git-trend-sync.log 2>&1
```

---

## API Reference

### Core Functions

```python
from src.collect import collect_all
from src.trending import run_trending
from src.metrics import run_metrics
from src.report import generate_reports
from src.recommend import run_recommendations
from src.scan_project import scan_project, recommend_categories

# Collect trending data
data = collect_all()                              # -> data/{date}/raw.json

# Compute activity scores
trending = run_trending("2026-03-28")             # -> data/{date}/trending.json

# Compute quantitative metrics
metrics = run_metrics("2026-03-28")               # -> data/{date}/metrics.json

# Generate markdown report
report_path = generate_reports("2026-03-28")      # -> reports/{date}.md

# Scan a project's tech stack
profile = scan_project("/path/to/project")        # -> dict with stack, deps, frameworks

# Get recommendations
rec_path = run_recommendations("2026-03-28", "/path/to/project")
```

### Configuration

Create `git-trend-sync.yaml` in your project root:

```yaml
project:
  name: "My AI App"
  description: "A conversational AI assistant with RAG pipeline"
  tech_stack: ["python", "fastapi", "langchain"]
  interests:
    - "better RAG performance"
    - "agent orchestration"
    - "code generation"
    - "MCP integration"
  exclude: ["java", "go"]  # Exclude entire ecosystems
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token for API access |
| `CLAUDE_API_KEY` | No | Required only for analysis mode (enabled by default, skip with `--skip-analysis`) |

---

## Testing

```bash
# Install test dependencies
pip install -r requirements.txt pytest

# Run all tests
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/test_trending.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/amazing-feature`)
3. Run tests (`python -m pytest tests/ -v`)
4. Commit your changes (`git commit -m "feat: add amazing feature"`)
5. Push to the branch (`git push origin feat/amazing-feature`)
6. Open a Pull Request

---

## License

MIT -- see [LICENSE](LICENSE) for details.

---

<div align="center">

### Built with Claude Code

[Report Bug](https://github.com/JSLEEKR/git-trend-sync/issues) . [Request Feature](https://github.com/JSLEEKR/git-trend-sync/issues)

</div>

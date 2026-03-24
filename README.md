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
### 🔥 Today's Top Trending (2026-03-24)

| # | Repository | Category | Activity | Stars | Commits (30d) |
|---|-----------|----------|----------|-------|---------------|
| 1 | [hermes-agent](https://github.com/NousResearch/hermes-agent) | AI Agent Framework | 🔥 10.0 | 12,034 | 2292 |
| 2 | [dify](https://github.com/langgenius/dify) | RAG Framework | 🔥 10.0 | 134,238 | 601 |
| 3 | [goclaw](https://github.com/nextlevelbuilder/goclaw) | Multi-Agent | 🔥 10.0 | 1,102 | 654 |
| 4 | [kilocode](https://github.com/Kilo-Org/kilocode) | Coding Assistant | 🔥 10.0 | 17,129 | 2482 |
| 5 | [vllm](https://github.com/vllm-project/vllm) | AI Infrastructure | 🔥 10.0 | 74,148 | 1069 |
| 6 | [browser-use](https://github.com/browser-use/browser-use) | Browser Agent | 🔥 10.0 | 84,122 | 279 |
| 7 | [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | MCP | 🔥 10.0 | 83,965 | 1366 |
| 8 | [dagu](https://github.com/dagu-org/dagu) | AI Workflow | 🔥 10.0 | 3,201 | 199 |
| 9 | [voicebox](https://github.com/jamiepine/voicebox) | Voice Agent | 🔥 10.0 | 14,086 | 252 |
| 10 | [WFGY](https://github.com/onestardao/WFGY) | Knowledge Management | 🔥 10.0 | 1,676 | 912 |

> Last updated: 2026-03-24 — [Full Report](reports/2026-03-24.md)
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
│   ├── report.py         # Trend report generation
│   ├── scan_project.py   # Project context scanner
│   ├── recommend.py      # Project-trend matcher
│   ├── apply.py          # Deep integration analysis
│   ├── history.py        # Trend history tracking
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

## ⚙️ Automation

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task → Name: `git-trend-sync`
3. Trigger: Daily at your preferred time
4. Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\git-trend-sync\run.py`
5. Done

---

<div align="center">

### Built with ❤️ and Claude Code

</div>

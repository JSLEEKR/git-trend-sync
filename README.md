<div align="center">

# 🤖 AI Agent Trend Report v2

### Activity-based trending of AI agent repositories on GitHub

[![GitHub Stars](https://img.shields.io/github/stars/JSLEEKR/ai-trend?style=for-the-badge&logo=github&color=yellow)](https://github.com/JSLEEKR/ai-trend/stargazers)
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

The AI agent ecosystem moves fast. New frameworks, tools, and patterns emerge weekly. Yesterday's best practice is today's legacy code.

The problem isn't finding good tools — it's finding the **right tool at the right time** for **your specific project**. A framework with 100k stars might be mature but stagnant. A repo with 2k stars might be the one that solves your exact problem, and it just launched last month.

**AI Trend** solves this by:
- **Tracking what's actually active** — not just popular, but actively developed (30-day commit activity)
- **Filtering noise** — only repos with 1,000+ stars, eliminating toy projects
- **Matching to your project** — scans your codebase and recommends only what's relevant
- **Generating integration designs** — not just "check this out", but "here's exactly how to integrate it into your code"

Stop scrolling through GitHub trending. Let the trends come to you — already filtered, analyzed, and matched to your stack.

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
| 🔍 **Trend Collection** | Daily (automated) | Collects repos, computes velocity scores, generates report |
| 🎯 **Recommendations** | After collection | Scans your project, matches with trends, suggests what's relevant |
| 🔬 **Deep Analysis** | On-demand | Detailed integration design doc for a specific trending repo |

### Categories

| Category | Description |
|:---------|:------------|
| 🧠 **AI Agent Framework** | General-purpose agent frameworks |
| 🔍 **RAG Framework** | Retrieval-augmented generation |
| 🤝 **Multi-Agent** | Multi-agent orchestration |
| 💻 **Coding Assistant** | AI coding tools |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- GitHub Personal Access Token

### Setup

```bash
git clone https://github.com/JSLEEKR/ai-trend.git
cd ai-trend
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

Add `ai-trend.yaml` to your project root for targeted recommendations:

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
ai-trend/
├── src/
│   ├── collect.py        # GitHub data collection (stars>1000, 7d active)
│   ├── trending.py       # Velocity-based trend scoring
│   ├── metrics.py        # Legacy quantitative metrics
│   ├── analyze.py        # Qualitative analysis engine
│   ├── report.py         # Trend report generation
│   ├── scan_project.py   # Project context scanner
│   ├── recommend.py      # Project-trend matcher
│   ├── apply.py          # Deep integration analysis
│   └── publish.sh        # Git commit & push
├── config/
│   ├── categories.yaml   # Category & topic config
│   └── prompts/          # Analysis prompt templates
├── data/
│   ├── snapshots/        # Daily star count snapshots
│   └── YYYY-MM-DD/       # Daily analysis data
├── reports/              # Generated reports
├── .claude/commands/     # /trend and /trend-apply
├── run.py                # Main orchestrator
└── ai-trend.yaml.example
```

---

## ⚙️ Automation

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task → Name: `AI Trend Report`
3. Trigger: Daily at your preferred time
4. Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\ai-trend\run.py`
5. Done

---

<div align="center">

### Built with ❤️ and Claude Code

</div>

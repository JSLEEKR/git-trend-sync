<div align="center">

# 🤖 AI Agent Trend Report v2

### Velocity-based trending of AI agent repositories on GitHub

[![GitHub Stars](https://img.shields.io/github/stars/JSLEEKR/ai-trend?style=for-the-badge&logo=github&color=yellow)](https://github.com/JSLEEKR/ai-trend/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Claude](https://img.shields.io/badge/powered%20by-Claude%20Code-D4A574?style=for-the-badge)](https://claude.ai)

<br/>

**Detects what's actually trending — not just popular — in the AI agent ecosystem**

Velocity-based scoring + Project-specific recommendations + Claude Code slash commands

[📊 Latest Report](reports/) · [🔧 Setup Guide](#-quick-start)

</div>

---

## 📋 What is this?

An automated system that tracks **velocity** — which AI agent repos are gaining stars *fastest* — and recommends trending tools that are relevant to **your** project.

### Why velocity, not just stars?

| Metric | What it finds | Problem |
|--------|--------------|---------|
| ⭐ Total stars | Established projects | Misses new rising tools |
| 📈 **Velocity** | Tools gaining traction *right now* | Catches trends early |

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

### Day 1 (Instant Metrics)

| Metric | Weight | What it measures |
|--------|--------|-----------------|
| Stars/day average | 30% | Growth rate over project lifetime |
| Recent activity | 25% | Commits + push recency (30 days) |
| Newness boost | 20% | Bonus for repos < 6 months old |
| Issue velocity | 10% | Community engagement |
| Commit frequency | 15% | Development pace |

### Day 2+ (Velocity Blending)

Daily snapshots track star counts. Velocity = actual daily star gains.

| Metric | Weight |
|--------|--------|
| Daily star delta | 40% |
| 7-day moving average | 30% |
| Acceleration (7d vs 30d) | 30% |

Blend: `Day 1 = instant only → Day 7+ = 30% instant + 70% velocity`

### Report Format

| # | Repository | Trend | Stars | +1d | +7d avg | Age | Status |
|---|-----------|-------|-------|-----|---------|-----|--------|
| 1 | some-repo | 🔥 8.7 | 5,230 | +127 | +95/d | 85d | NEW ENTRY |
| 2 | other-repo | 📈 7.3 | 45,000 | +89 | +72/d | 2y | TRENDING |

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

# AI Agent Trend v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static star-based ranking with velocity-based trending, add project-aware recommendations, and create Claude Code slash commands.

**Architecture:** 3 pipelines — (1) daily trend collection with snapshot-based velocity, (2) auto project recommendations by scanning codebase + matching trends, (3) on-demand deep apply analysis. All accessible via CLI and `/trend`, `/trend-apply` slash commands.

**Tech Stack:** Python 3.10+, requests, PyYAML, python-dotenv, GitHub Search API

---

### Task 1: Update collect.py — stars>1000 filter + snapshot saving

**Files:**
- Modify: `src/collect.py`

- [ ] **Step 1: Update search_repos to add stars>1000 filter**

Change the query in `search_repos()` to always include `stars:>1000`:

```python
def search_repos(topic: str, limit: int, headers: dict) -> list[dict]:
    """Search trending repositories by topic. Only repos with 1000+ stars."""
    url = f"{GITHUB_API}/search/repositories"
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    q = f"topic:{topic} stars:>1000 pushed:>{since}"
    params = {
        "q": q,
        "sort": "stars",
        "order": "desc",
        "per_page": limit,
    }
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("items", [])
```

- [ ] **Step 2: Increase per-category limit to 30 in categories.yaml**

```yaml
categories:
  - name: "AI Agent Framework"
    topics: ["ai-agent", "ai-agents", "autonomous-agent"]
    limit: 30

  - name: "RAG Framework"
    topics: ["rag", "retrieval-augmented-generation"]
    limit: 30

  - name: "Multi-Agent"
    topics: ["multi-agent", "multi-agent-systems", "agent-orchestration"]
    limit: 30

  - name: "Coding Assistant"
    topics: ["coding-assistant", "code-generation", "ai-coding"]
    limit: 30
```

- [ ] **Step 3: Add snapshot saving to collect_all()**

After saving `raw.json`, also save a snapshot:

```python
# Save snapshot for velocity tracking
snapshot_dir = BASE_DIR / "data" / "snapshots"
snapshot_dir.mkdir(parents=True, exist_ok=True)
snapshot_path = snapshot_dir / f"{today}.json"

snapshot = {"date": today, "repos": {}}
for cat_repos in result.values():
    for r in cat_repos:
        snapshot["repos"][r["full_name"]] = {
            "stars": r["stars"],
            "forks": r["forks"],
        }

with open(snapshot_path, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)
print(f"Snapshot saved to {snapshot_path}")
```

- [ ] **Step 4: Remove old `mode` parameter and `timedelta` import at function level**

Clean up the old `mode` parameter from `search_repos`. Move `from datetime import timedelta` to top-level imports.

- [ ] **Step 5: Test collection**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.collect import collect_all; collect_all()"`
Expected: repos collected, all with 1000+ stars, snapshot saved to `data/snapshots/2026-03-23.json`

- [ ] **Step 6: Commit**

```bash
git add src/collect.py config/categories.yaml
git commit -m "feat: add stars>1000 filter and daily snapshot saving"
```

---

### Task 2: Create trending.py — velocity and trend score calculation

**Files:**
- Create: `src/trending.py`

- [ ] **Step 1: Create trending.py with instant metrics calculation**

```python
"""
Velocity-based trend scoring.
Day 1: instant metrics only. Day 2+: blends with snapshot velocity.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def days_since(date_str: str) -> int:
    if not date_str:
        return 9999
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return 9999


def load_snapshots() -> list[dict]:
    """Load all available snapshots, sorted by date ascending."""
    snapshot_dir = BASE_DIR / "data" / "snapshots"
    if not snapshot_dir.exists():
        return []
    snapshots = []
    for f in sorted(snapshot_dir.glob("*.json")):
        with open(f, "r", encoding="utf-8") as fh:
            snapshots.append(json.load(fh))
    return snapshots


def compute_instant_score(repo: dict) -> float:
    """Compute trend score from single-day data (no history needed)."""
    age_days = max(days_since(repo["created_at"]), 1)
    stars = repo["stars"]

    # Stars per day average (0-10 normalized, cap at 50/day = 10)
    stars_per_day = min(stars / age_days, 50)
    spd_score = (stars_per_day / 50) * 10

    # Recent activity (commits + recency)
    commits = repo["recent_commits_30d"]
    push_recency = max(0, 30 - days_since(repo["pushed_at"]))
    activity_score = min((commits * 0.1 + push_recency * 0.2), 10)

    # Newness boost (< 6 months old gets bonus)
    newness = max(0, 1 - age_days / 180) * 10

    # Issue velocity (more recent issues = more active community)
    issue_score = min(repo["open_issues"] / max(stars / 1000, 1), 10)

    return round(
        spd_score * 0.3
        + activity_score * 0.25
        + newness * 0.2
        + issue_score * 0.1
        + min(commits / 30, 10) * 0.15,  # release proxy
        2,
    )


def compute_velocity_score(full_name: str, snapshots: list[dict]) -> dict:
    """Compute velocity from snapshot history."""
    deltas = []
    prev_stars = None
    for snap in snapshots:
        current = snap["repos"].get(full_name)
        if current is None:
            prev_stars = None
            continue
        if prev_stars is not None:
            deltas.append(current["stars"] - prev_stars)
        prev_stars = current["stars"]

    if not deltas:
        return {"velocity_score": 0, "star_delta_1d": 0, "star_delta_7d_avg": 0, "acceleration": 0, "days_of_data": 0}

    delta_1d = deltas[-1] if deltas else 0
    avg_7d = sum(deltas[-7:]) / len(deltas[-7:]) if deltas else 0
    avg_30d = sum(deltas[-30:]) / len(deltas[-30:]) if deltas else 0
    acceleration = avg_7d - avg_30d

    # Normalize velocity score (cap daily delta at 200 = score 10)
    delta_norm = min(delta_1d / 200, 1) * 10
    avg_norm = min(avg_7d / 150, 1) * 10
    accel_norm = max(min(acceleration / 50, 1), -1) * 5 + 5  # center at 5

    velocity_score = round(delta_norm * 0.4 + avg_norm * 0.3 + accel_norm * 0.3, 2)

    return {
        "velocity_score": velocity_score,
        "star_delta_1d": delta_1d,
        "star_delta_7d_avg": round(avg_7d, 1),
        "acceleration": round(acceleration, 1),
        "days_of_data": len(deltas),
    }


def compute_trend_scores(raw_data: dict) -> dict:
    """Compute blended trend scores for all repos."""
    snapshots = load_snapshots()
    # Check which repos existed in previous snapshots
    prev_repo_set = set()
    for snap in snapshots[:-1]:  # all except today
        prev_repo_set.update(snap["repos"].keys())

    result = {}
    for cat_name, repos in raw_data["categories"].items():
        scored = []
        for r in repos:
            instant = compute_instant_score(r)
            vel = compute_velocity_score(r["full_name"], snapshots)

            # Blend
            days = vel["days_of_data"]
            if days == 0:
                trend_score = instant
            elif days < 7:
                w = days / 7
                trend_score = instant * (1 - w) + vel["velocity_score"] * w
            else:
                trend_score = instant * 0.3 + vel["velocity_score"] * 0.7

            is_new = r["full_name"] not in prev_repo_set

            scored.append({
                **r,
                "trend_score": round(trend_score, 1),
                "instant_score": instant,
                "velocity_score": vel["velocity_score"],
                "star_delta_1d": vel["star_delta_1d"],
                "star_delta_7d_avg": vel["star_delta_7d_avg"],
                "acceleration": vel["acceleration"],
                "days_of_data": vel["days_of_data"],
                "is_new_entry": is_new,
                "stars_per_day_avg": round(r["stars"] / max(days_since(r["created_at"]), 1), 1),
                "age_days": days_since(r["created_at"]),
            })

        # Sort by trend_score, take top 10
        scored.sort(key=lambda x: x["trend_score"], reverse=True)
        result[cat_name] = scored[:10]

    return {"date": raw_data["date"], "categories": result}


def run_trending(date: str = None) -> dict:
    """Load raw data and compute trend scores."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    raw_path = BASE_DIR / "data" / date / "raw.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    trending = compute_trend_scores(raw_data)

    output_path = BASE_DIR / "data" / date / "trending.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(trending, f, ensure_ascii=False, indent=2)

    print(f"Trending scores saved to {output_path}")
    return trending


if __name__ == "__main__":
    run_trending()
```

- [ ] **Step 2: Test trending calculation**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.trending import run_trending; run_trending('2026-03-23')"`
Expected: `data/2026-03-23/trending.json` created with trend scores (Day 1 = instant only)

- [ ] **Step 3: Commit**

```bash
git add src/trending.py
git commit -m "feat: add velocity-based trend scoring engine"
```

---

### Task 3: Update report.py — new trend-focused format

**Files:**
- Modify: `src/report.py`

- [ ] **Step 1: Rewrite generate_en_report to use trending data**

Replace the current `generate_en_report` function to use the new trending format with status labels (NEW ENTRY, RISING, STABLE, COOLING), trend scores, star deltas, and age display.

Key changes:
- Read from `trending.json` instead of `metrics.json`
- Table columns: `# | Repository | Trend | Stars | +1d | +7d avg | Age | Status`
- Status logic: `is_new_entry` → NEW ENTRY, else compare with previous day's trend data
- Keep qualitative analysis sections as-is
- Update cross-category section to sort by `trend_score`

- [ ] **Step 2: Update generate_reports to load trending.json**

Change the data source from `metrics.json` to `trending.json`. Fall back to `metrics.json` if trending not available.

- [ ] **Step 3: Remove load_categories_config (no longer needed)**

This was for Korean names. Clean up the dead code.

- [ ] **Step 4: Test report generation**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.report import generate_reports; generate_reports('2026-03-23')"`
Expected: `reports/2026-03-23.md` with new trend format

- [ ] **Step 5: Commit**

```bash
git add src/report.py
git commit -m "feat: update report format to velocity-based trending"
```

---

### Task 4: Create scan_project.py — project context scanner

**Files:**
- Create: `src/scan_project.py`

- [ ] **Step 1: Create scan_project.py**

```python
"""
Scan a project directory to build a context profile for recommendations.
Reads auto-detected files + optional ai-trend.yaml config.
"""

import json
import re
from pathlib import Path

import yaml


def detect_tech_stack(project_path: Path) -> dict:
    """Auto-detect tech stack from project files."""
    stack = {"languages": [], "frameworks": [], "dependencies": []}

    # Python
    req_txt = project_path / "requirements.txt"
    if req_txt.exists():
        stack["languages"].append("python")
        with open(req_txt, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    stack["dependencies"].append(line)

    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        stack["languages"].append("python")
        with open(pyproject, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            # Extract dependencies from pyproject.toml
            dep_match = re.findall(r'"([a-zA-Z0-9_-]+)', content)
            stack["dependencies"].extend(dep_match[:50])

    # JavaScript/TypeScript
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        stack["languages"].append("javascript")
        with open(pkg_json, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        stack["dependencies"].extend(deps.keys())
        # Detect frameworks
        for fw in ["react", "vue", "angular", "next", "nuxt", "express", "fastify"]:
            if fw in deps or f"@{fw}" in str(deps):
                stack["frameworks"].append(fw)
        if "typescript" in deps:
            stack["languages"].append("typescript")

    # Go
    if (project_path / "go.mod").exists():
        stack["languages"].append("go")

    # Rust
    if (project_path / "Cargo.toml").exists():
        stack["languages"].append("rust")

    # Java
    if (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
        stack["languages"].append("java")

    stack["languages"] = list(set(stack["languages"]))
    return stack


def read_project_description(project_path: Path) -> str:
    """Read project description from README."""
    for name in ["README.md", "readme.md", "README.rst", "README"]:
        readme = project_path / name
        if readme.exists():
            with open(readme, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            # Return first 2000 chars
            return content[:2000]
    return ""


def detect_architecture(project_path: Path, stack: dict) -> list[str]:
    """Detect architecture patterns from file structure and dependencies."""
    hints = []
    deps_str = " ".join(stack["dependencies"]).lower()

    # AI/ML patterns
    if any(d in deps_str for d in ["langchain", "llama-index", "llamaindex"]):
        hints.append("uses LLM framework")
    if any(d in deps_str for d in ["chromadb", "pinecone", "weaviate", "qdrant", "faiss"]):
        hints.append("uses vector store")
    if any(d in deps_str for d in ["openai", "anthropic", "cohere"]):
        hints.append("calls LLM API")
    if any(d in deps_str for d in ["transformers", "torch", "tensorflow"]):
        hints.append("runs ML models locally")

    # Web patterns
    if any(d in deps_str for d in ["fastapi", "flask", "django", "express"]):
        hints.append("has API endpoints")
    if any(d in deps_str for d in ["react", "vue", "angular", "next", "svelte"]):
        hints.append("has frontend UI")

    # Agent patterns
    if any(d in deps_str for d in ["crewai", "autogen", "agentscope", "metagpt"]):
        hints.append("uses agent framework")

    # Data patterns
    if any(d in deps_str for d in ["pandas", "polars", "sqlalchemy", "prisma"]):
        hints.append("has data processing")
    if any(d in deps_str for d in ["celery", "rq", "dramatiq"]):
        hints.append("has background jobs")

    return hints


def load_user_config(project_path: Path) -> dict:
    """Load optional ai-trend.yaml from project root."""
    config_path = project_path / "ai-trend.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("project", {})


def scan_project(project_path: str) -> dict:
    """Build a complete project profile."""
    path = Path(project_path).resolve()
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")

    stack = detect_tech_stack(path)
    description = read_project_description(path)
    hints = detect_architecture(path, stack)
    user_config = load_user_config(path)

    profile = {
        "name": user_config.get("name", path.name),
        "description": user_config.get("description", description[:500]),
        "detected_stack": stack["languages"],
        "detected_frameworks": stack["frameworks"],
        "declared_interests": user_config.get("interests", []),
        "exclude": user_config.get("exclude", []),
        "current_dependencies": stack["dependencies"][:100],
        "architecture_hints": hints,
        "tech_stack_override": user_config.get("tech_stack", []),
    }

    return profile


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    profile = scan_project(path)
    print(json.dumps(profile, indent=2, ensure_ascii=False))
```

- [ ] **Step 2: Test project scanner**

Run: `PYTHONIOENCODING=utf-8 python src/scan_project.py .`
Expected: JSON output with detected Python stack, dependencies (requests, PyYAML, python-dotenv)

- [ ] **Step 3: Commit**

```bash
git add src/scan_project.py
git commit -m "feat: add project context scanner for recommendations"
```

---

### Task 5: Create recommend.py — project-trend matcher

**Files:**
- Create: `src/recommend.py`
- Create: `config/prompts/recommend.md`

- [ ] **Step 1: Create config/prompts/recommend.md**

```markdown
You are an AI technology advisor. Given a project profile and trending repositories,
determine which trending repos are relevant to this project.

## Project Profile
{{project_profile}}

## Trending Repositories
{{trending_data}}

## Instructions

For each trending repo, assess relevance to this project:
- Does the tech stack match?
- Does it solve a problem the project likely has?
- Could it replace or complement an existing dependency?
- Does it align with the project's declared interests?

Categorize each relevant repo into one of:
- **high**: Direct stack match + solves a clear need
- **watch**: Interesting but different stack or too early
- **new_entrant**: Brand new repo matching interests

Skip repos with zero relevance.

Respond in JSON:
```json
{
  "recommendations": [
    {
      "name": "repo-name",
      "relevance": "high|watch|new_entrant",
      "why": "One paragraph explaining why this matters to the project",
      "how_to_evaluate": "Concrete next step to try it",
      "effort": "small|medium|large"
    }
  ],
  "summary": "One sentence: are there actionable recommendations today or not?"
}
```

If nothing is relevant, return empty recommendations and say so in summary.
Be honest — don't force irrelevant matches.
```

- [ ] **Step 2: Create src/recommend.py**

```python
"""
Match trending repos against a project profile to generate recommendations.
"""

import json
from datetime import datetime
from pathlib import Path

from src.scan_project import scan_project

BASE_DIR = Path(__file__).resolve().parent.parent


def load_prompt_template() -> str:
    path = BASE_DIR / "config" / "prompts" / "recommend.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def match_trending_to_project(trending: dict, profile: dict) -> list[dict]:
    """Pre-filter trending repos by basic stack/interest compatibility."""
    project_langs = set(profile["detected_stack"] + profile.get("tech_stack_override", []))
    interests = set(i.lower() for i in profile.get("declared_interests", []))
    excludes = set(e.lower() for e in profile.get("exclude", []))
    deps = set(d.lower().split("==")[0].split(">=")[0] for d in profile["current_dependencies"])

    candidates = []
    for cat_name, repos in trending["categories"].items():
        cat_lower = cat_name.lower()
        for r in repos:
            repo_lang = (r.get("language") or "").lower()

            # Skip excluded ecosystems
            if repo_lang in excludes:
                continue

            # Score relevance signals
            signals = 0
            reasons = []

            if repo_lang in project_langs or not project_langs:
                signals += 2
                reasons.append("stack_match")

            if any(i in cat_lower or i in (r.get("description") or "").lower() for i in interests):
                signals += 2
                reasons.append("interest_match")

            repo_name_lower = r["name"].lower()
            if repo_name_lower in deps or any(repo_name_lower in d for d in deps):
                signals += 1
                reasons.append("dependency_overlap")

            if r.get("is_new_entry"):
                signals += 1
                reasons.append("new_entry")

            if signals >= 2:
                candidates.append({**r, "category": cat_name, "match_signals": reasons, "match_score": signals})

    candidates.sort(key=lambda x: (x["match_score"], x["trend_score"]), reverse=True)
    return candidates[:15]  # Top 15 candidates for LLM analysis


def generate_recommendations_report(date: str, profile: dict, recommendations: dict) -> str:
    """Generate markdown recommendations report."""
    lines = [
        f"# Recommendations for \"{profile['name']}\" — {date}",
        "",
        f"> {recommendations.get('summary', 'Analysis complete.')}",
        "",
    ]

    recs = recommendations.get("recommendations", [])
    if not recs:
        lines.append("No actionable recommendations today. Check back tomorrow!")
        return "\n".join(lines)

    # Group by relevance
    groups = {"high": [], "watch": [], "new_entrant": []}
    for r in recs:
        groups.get(r["relevance"], groups["watch"]).append(r)

    if groups["high"]:
        lines.append("## High Relevance")
        lines.append("")
        for r in groups["high"]:
            lines.append(f"### {r['name']}")
            lines.append(f"**Why it matters:** {r['why']}")
            lines.append(f"**How to evaluate:** {r['how_to_evaluate']}")
            lines.append(f"**Effort:** {r['effort']}")
            lines.append("")

    if groups["watch"]:
        lines.append("## Worth Watching")
        lines.append("")
        for r in groups["watch"]:
            lines.append(f"### {r['name']}")
            lines.append(f"**Why:** {r['why']}")
            lines.append("")

    if groups["new_entrant"]:
        lines.append("## New Entrants")
        lines.append("")
        for r in groups["new_entrant"]:
            lines.append(f"### {r['name']}")
            lines.append(f"**Why:** {r['why']}")
            lines.append("")

    return "\n".join(lines)


def run_recommendations(date: str = None, project_path: str = ".") -> Path:
    """Generate recommendations for a project."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    trending_path = BASE_DIR / "data" / date / "trending.json"
    if not trending_path.exists():
        print(f"No trending data for {date}. Run the pipeline first.")
        return None

    with open(trending_path, "r", encoding="utf-8") as f:
        trending = json.load(f)

    # Scan project
    print(f"Scanning project at {project_path}...")
    profile = scan_project(project_path)
    print(f"  Detected: {profile['detected_stack']}, {len(profile['current_dependencies'])} deps")

    # Pre-filter candidates
    candidates = match_trending_to_project(trending, profile)
    print(f"  Found {len(candidates)} potential matches")

    if not candidates:
        recommendations = {"recommendations": [], "summary": "No trending repos match your project today."}
    else:
        # Build prompt for LLM analysis
        template = load_prompt_template()
        prompt = template.replace("{{project_profile}}", json.dumps(profile, ensure_ascii=False, indent=2))

        # Trim candidate data for prompt
        candidate_summary = []
        for c in candidates:
            candidate_summary.append({
                "name": c["name"],
                "full_name": c["full_name"],
                "url": c["url"],
                "description": c.get("description", ""),
                "category": c["category"],
                "language": c.get("language", ""),
                "trend_score": c["trend_score"],
                "stars": c.get("stars", 0),
                "is_new_entry": c.get("is_new_entry", False),
                "match_signals": c.get("match_signals", []),
            })
        prompt = prompt.replace("{{trending_data}}", json.dumps(candidate_summary, ensure_ascii=False, indent=2))

        # Save prompt for manual or CLI-based analysis
        prompt_path = BASE_DIR / "data" / date / "recommend_prompt.md"
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"  Recommendation prompt saved to {prompt_path}")

        # For now, generate a basic rule-based recommendation
        # (LLM analysis can be added via Claude Code CLI or subagent)
        recommendations = {"recommendations": [], "summary": ""}
        for c in candidates:
            relevance = "high" if c["match_score"] >= 4 else "watch" if c["match_score"] >= 2 else "new_entrant"
            if c.get("is_new_entry"):
                relevance = "new_entrant"
            recommendations["recommendations"].append({
                "name": c["name"],
                "relevance": relevance,
                "why": f"{c.get('description', 'No description')} (Trend: {c['trend_score']}, Signals: {', '.join(c.get('match_signals', []))})",
                "how_to_evaluate": f"Check {c['url']} and compare with your current stack",
                "effort": "medium",
            })

        if recommendations["recommendations"]:
            recommendations["summary"] = f"Found {len(recommendations['recommendations'])} relevant trending repos for your project."
        else:
            recommendations["summary"] = "No trending repos match your project today."

    # Generate report
    report = generate_recommendations_report(date, profile, recommendations)
    report_path = BASE_DIR / "reports" / f"{date}-recommendations.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Recommendations saved to {report_path}")

    return report_path


if __name__ == "__main__":
    import sys
    project = sys.argv[1] if len(sys.argv) > 1 else "."
    run_recommendations(project_path=project)
```

- [ ] **Step 3: Test recommendations**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.recommend import run_recommendations; run_recommendations('2026-03-23', '.')"`
Expected: `reports/2026-03-23-recommendations.md` created

- [ ] **Step 4: Commit**

```bash
git add src/recommend.py config/prompts/recommend.md
git commit -m "feat: add project-trend recommendation engine"
```

---

### Task 6: Create apply.py — deep apply analysis

**Files:**
- Create: `src/apply.py`
- Create: `config/prompts/apply.md`

- [ ] **Step 1: Create config/prompts/apply.md**

```markdown
You are a senior engineer helping integrate a trending tool into an existing project.

## Trending Repository
{{repo_data}}

## Target Project
{{project_profile}}

## Instructions

Provide a detailed integration analysis:

1. **What this repo does** — one paragraph
2. **Why it's trending** — what changed recently
3. **Impact on your project:**
   - Which files/modules would be affected
   - What it would replace or complement
4. **Migration path:**
   - Step-by-step integration guide
   - Code examples showing before/after
5. **Risks and trade-offs**
6. **Effort estimate:** small (< 1 day) / medium (1-3 days) / large (3+ days)
7. **Verdict:** Should you adopt this? Yes/No/Wait with reasoning.

Be specific to THIS project's stack and architecture.
```

- [ ] **Step 2: Create src/apply.py**

```python
"""
Deep apply analysis — detailed integration report for a specific
trending repo against a specific project.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.scan_project import scan_project

BASE_DIR = Path(__file__).resolve().parent.parent


def find_repo_in_trending(repo_name: str, date: str) -> dict | None:
    """Find a repo in trending data by name."""
    trending_path = BASE_DIR / "data" / date / "trending.json"
    if not trending_path.exists():
        return None
    with open(trending_path, "r", encoding="utf-8") as f:
        trending = json.load(f)
    for cat_repos in trending["categories"].values():
        for r in cat_repos:
            if r["name"].lower() == repo_name.lower() or r["full_name"].lower() == repo_name.lower():
                return r
    return None


def find_repo_in_raw(repo_name: str, date: str) -> dict | None:
    """Fallback: find repo in raw data."""
    raw_path = BASE_DIR / "data" / date / "raw.json"
    if not raw_path.exists():
        return None
    with open(raw_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    for cat_repos in raw["categories"].values():
        for r in cat_repos:
            if r["name"].lower() == repo_name.lower() or r["full_name"].lower() == repo_name.lower():
                return r
    return None


def generate_apply_report(repo: dict, profile: dict, date: str) -> str:
    """Generate a deep apply analysis prompt and save it."""
    template_path = BASE_DIR / "config" / "prompts" / "apply.md"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Build repo summary
    repo_summary = {
        "name": repo["name"],
        "full_name": repo["full_name"],
        "url": repo["url"],
        "description": repo.get("description", ""),
        "language": repo.get("language", ""),
        "stars": repo.get("stars", 0),
        "trend_score": repo.get("trend_score", "N/A"),
        "is_new_entry": repo.get("is_new_entry", False),
        "readme_excerpt": repo.get("readme_excerpt", ""),
    }

    prompt = template.replace("{{repo_data}}", json.dumps(repo_summary, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{{project_profile}}", json.dumps(profile, ensure_ascii=False, indent=2))

    # Save prompt for Claude Code execution
    prompt_path = BASE_DIR / "data" / date / f"apply_prompt_{repo['name']}.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    # Generate basic report structure
    lines = [
        f"# Deep Analysis: {repo['name']} for \"{profile['name']}\"",
        "",
        f"> Generated on {date}",
        "",
        f"## Repository: [{repo['name']}]({repo['url']})",
        f"- **Description:** {repo.get('description', 'N/A')}",
        f"- **Language:** {repo.get('language', 'N/A')}",
        f"- **Stars:** {repo.get('stars', 0):,}",
        f"- **Trend Score:** {repo.get('trend_score', 'N/A')}",
        "",
        "## Your Project",
        f"- **Stack:** {', '.join(profile['detected_stack'])}",
        f"- **Interests:** {', '.join(profile.get('declared_interests', ['not specified']))}",
        "",
        f"## Analysis Prompt",
        "",
        f"Run the following to get a detailed analysis from Claude Code:",
        "```bash",
        f"claude -p \"$(cat {prompt_path})\"",
        "```",
        "",
        "Or use `/trend-apply` in Claude Code for interactive analysis.",
    ]

    report_path = BASE_DIR / "reports" / f"apply-{repo['name']}-{date}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Apply report saved to {report_path}")
    print(f"Analysis prompt saved to {prompt_path}")
    return str(report_path)


def main():
    parser = argparse.ArgumentParser(description="Deep apply analysis")
    parser.add_argument("--repo", required=True, help="Repository name to analyze")
    parser.add_argument("--project", default=".", help="Path to your project")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    # Find repo
    repo = find_repo_in_trending(args.repo, args.date)
    if not repo:
        repo = find_repo_in_raw(args.repo, args.date)
    if not repo:
        print(f"Error: Repository '{args.repo}' not found in {args.date} data.")
        print("Available repos:")
        trending_path = BASE_DIR / "data" / args.date / "trending.json"
        if trending_path.exists():
            with open(trending_path, "r", encoding="utf-8") as f:
                t = json.load(f)
            for cat, repos in t["categories"].items():
                for r in repos:
                    print(f"  {r['name']} ({cat})")
        return

    # Scan project
    profile = scan_project(args.project)
    generate_apply_report(repo, profile, args.date)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add src/apply.py config/prompts/apply.md
git commit -m "feat: add deep apply analysis for specific repos"
```

---

### Task 7: Create Claude Code slash commands

**Files:**
- Create: `.claude/commands/trend.md`
- Create: `.claude/commands/trend-apply.md`

- [ ] **Step 1: Create .claude/commands/trend.md**

```markdown
Read the latest trend report from the `reports/` directory in this project.
Look for the most recent file matching `YYYY-MM-DD.md` pattern (not recommendations or apply files).

Summarize:
1. Which repos are NEW ENTRY (first time trending)?
2. Which repos are RISING (trend score increasing)?
3. Top 3 repos across all categories by trend score
4. Any notable changes from the previous day

If a recommendations file exists for the same date, also summarize:
- How many repos are relevant to this project?
- Any high-relevance recommendations?

Keep it concise — bullet points, no fluff.
```

- [ ] **Step 2: Create .claude/commands/trend-apply.md**

```markdown
Analyze the current project against the latest AI agent trend data.

Steps:
1. Run `python src/scan_project.py .` to get the project profile
2. Read the latest `data/YYYY-MM-DD/trending.json`
3. For each trending repo, assess:
   - Does the tech stack match this project?
   - Does it solve a problem this project has?
   - Could it replace or complement a current dependency?
4. Report findings:
   - If something is highly relevant: explain what it does, why it matters for THIS project, and how to start evaluating it
   - If nothing matches: say "No actionable recommendations today" and explain why

Be specific to this project's actual code and dependencies. Don't force irrelevant recommendations.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/trend.md .claude/commands/trend-apply.md
git commit -m "feat: add /trend and /trend-apply Claude Code slash commands"
```

---

### Task 8: Update run.py — integrate new pipeline steps

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Add trending and recommend steps to run.py**

Add new step functions and wire them into the pipeline:

```python
def step_trending(date: str):
    """Step 2b: Compute trend scores."""
    from src.trending import run_trending
    return run_trending(date)

def step_recommend(date: str, project_path: str):
    """Step 5: Generate project recommendations."""
    from src.recommend import run_recommendations
    return run_recommendations(date, project_path)
```

Update `main()`:
- Add `--project` argument (default: `.`)
- Add `--no-recommend` flag
- Pipeline order: collect → trending → analyze → report → recommend
- Update the docstring and print messages

- [ ] **Step 2: Add --project and --no-recommend args**

```python
parser.add_argument(
    "--project",
    default=".",
    help="Path to your project for recommendations",
)
parser.add_argument(
    "--no-recommend",
    action="store_true",
    help="Skip project recommendation step",
)
```

- [ ] **Step 3: Update pipeline flow in main()**

```python
# Full pipeline
raw_data = run_step("Collect Repositories", step_collect)
date = raw_data["date"]

run_step("Compute Trend Scores", step_trending, date)

if not args.skip_analysis:
    run_step("Qualitative Analysis", step_analyze, date)

run_step("Generate Report", step_report, date)

if not args.no_recommend:
    run_step("Project Recommendations", step_recommend, date, args.project)
```

- [ ] **Step 4: Update docstring and final print**

```python
"""
AI Agent Trend Report v2 — Main Orchestrator

Pipeline:
1. Collect trending repos from GitHub Topics (stars>1000, active in 7d)
2. Compute velocity-based trend scores
3. Qualitative analysis
4. Generate trend report
5. Project-specific recommendations (optional)

Usage:
    python run.py                           # Full pipeline
    python run.py --skip-analysis           # Skip qualitative analysis
    python run.py --no-recommend            # Skip recommendations
    python run.py --project /path/to/proj   # Recommendations for specific project
    python run.py --report-only             # Regenerate from existing data
"""
```

- [ ] **Step 5: Test full pipeline**

Run: `PYTHONIOENCODING=utf-8 python run.py --no-push --skip-analysis`
Expected: collect → trending → report → recommendations all complete

- [ ] **Step 6: Commit**

```bash
git add run.py
git commit -m "feat: integrate trending + recommendations into pipeline"
```

---

### Task 9: Create ai-trend.yaml.example

**Files:**
- Create: `ai-trend.yaml.example`

- [ ] **Step 1: Create example config**

```yaml
# Place this file as ai-trend.yaml in your project root
# for targeted trend recommendations.

project:
  name: "My AI App"
  description: "A conversational AI assistant with RAG pipeline"
  tech_stack: ["python", "fastapi", "langchain"]
  interests: ["better RAG", "agent orchestration", "code generation", "multi-agent"]
  exclude: ["java", "go"]  # ecosystems you're not interested in
```

- [ ] **Step 2: Commit**

```bash
git add ai-trend.yaml.example
git commit -m "feat: add ai-trend.yaml example config"
```

---

### Task 10: Update README.md and final push

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with v2 features**

Update to reflect:
- Velocity-based trending (not just stars)
- Project recommendations
- `/trend` and `/trend-apply` slash commands
- `ai-trend.yaml` configuration
- Updated project structure
- New CLI options

- [ ] **Step 2: Final commit and push**

```bash
git add README.md
git commit -m "docs: update README for v2 with velocity trending and recommendations"
git push origin main
```

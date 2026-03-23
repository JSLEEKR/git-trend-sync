"""
recommend.py — rule-based project recommendation engine for ai-trend

Given a project profile (from scan_project) and trending repos (from collect/metrics),
pre-filters candidates by compatibility, scores them, and generates a markdown report.
Also saves a prompt file for optional Claude Code deep analysis.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.scan_project import scan_project

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Language / ecosystem normalisation
# ---------------------------------------------------------------------------

# Maps repo language to a canonical ecosystem token
_LANG_TO_ECOSYSTEM = {
    "python": "python",
    "jupyter notebook": "python",
    "typescript": "javascript",
    "javascript": "javascript",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "kotlin": "java",
    "scala": "java",
    "c#": "csharp",
    "f#": "fsharp",
    "php": "php",
    "ruby": "ruby",
    "elixir": "elixir",
    "c": "c",
    "c++": "cpp",
    "swift": "swift",
    "dart": "dart",
    "r": "r",
}

# Maps detected project stack tokens to compatible ecosystems
_STACK_ECOSYSTEM_MAP = {
    "python": {"python"},
    "javascript": {"javascript"},
    "typescript": {"javascript"},
    "go": {"go"},
    "rust": {"rust"},
    "java": {"java"},
    "csharp": {"csharp"},
    "fsharp": {"fsharp"},
    "php": {"php"},
    "ruby": {"ruby"},
    "elixir": {"elixir"},
}


def _repo_ecosystem(repo: dict) -> str | None:
    """Return the canonical ecosystem string for a repo, or None if unknown."""
    lang = (repo.get("language") or "").lower()
    return _LANG_TO_ECOSYSTEM.get(lang)


def _project_ecosystems(profile: dict) -> set[str]:
    """Return the set of compatible ecosystems for a project profile."""
    ecosystems: set[str] = set()
    stacks = profile.get("tech_stack_override") or profile.get("detected_stack") or []
    for stack in stacks:
        mapped = _STACK_ECOSYSTEM_MAP.get(stack.lower())
        if mapped:
            ecosystems.update(mapped)
    return ecosystems


def _is_new_entry(repo: dict, threshold_days: int = 180) -> bool:
    """Return True if the repo was created within threshold_days."""
    created_at = repo.get("created_at") or ""
    if not created_at:
        return False
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt).days
        return age_days <= threshold_days
    except (ValueError, TypeError):
        return False


def _interest_keywords(profile: dict) -> list[str]:
    """Build a flat list of lowercase interest keywords from the profile."""
    interests = profile.get("declared_interests") or []
    frameworks = profile.get("detected_frameworks") or []
    hints = profile.get("architecture_hints") or []
    deps = profile.get("current_dependencies") or []

    keywords: list[str] = []
    for item in interests + frameworks:
        keywords.append(item.lower())
    # Extract meaningful words from architecture hints
    for hint in hints:
        keywords.extend(hint.lower().split())
    # Add dependency names (already lowercased)
    keywords.extend(deps)
    return list(set(keywords))


def _repo_tokens(repo: dict) -> set[str]:
    """Build a set of lowercase tokens from a repo's name, description, and topics."""
    tokens: set[str] = set()
    tokens.update((repo.get("name") or "").lower().replace("-", " ").split())
    tokens.update((repo.get("description") or "").lower().split())
    for topic in repo.get("topics") or []:
        tokens.update(topic.lower().replace("-", " ").split())
    # Also add the full_name owner/repo components
    full_name = (repo.get("full_name") or "").lower()
    tokens.update(full_name.replace("/", " ").replace("-", " ").replace("_", " ").split())
    return tokens


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_prompt_template() -> str:
    """Read the recommend.md prompt template."""
    template_path = BASE_DIR / "config" / "prompts" / "recommend.md"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def match_trending_to_project(trending: dict, profile: dict) -> list[dict]:
    """
    Pre-filter trending repos by compatibility with the project profile.

    Scoring signals:
      +2  stack_match    — repo language maps to a compatible project ecosystem
      +2  interest_match — repo tokens overlap with declared interests / frameworks
      +1  dependency_overlap — repo name matches a current dependency
      +1  new_entry      — repo is < 6 months old

    Returns top 15 candidates with score >= 2, sorted by score descending.
    """
    excluded: set[str] = set(e.lower() for e in (profile.get("exclude") or []))
    project_ecosystems = _project_ecosystems(profile)
    interest_kws = _interest_keywords(profile)
    current_deps: set[str] = set(profile.get("current_dependencies") or [])

    # Collect all repos from all categories
    all_repos: list[dict] = []
    categories = trending.get("categories") or {}
    for cat_repos in categories.values():
        for repo in cat_repos:
            all_repos.append(repo)

    scored: list[dict] = []
    for repo in all_repos:
        repo_name = (repo.get("name") or "").lower()
        repo_full = (repo.get("full_name") or "").lower()

        # Skip excluded ecosystems
        ecosystem = _repo_ecosystem(repo)
        if ecosystem and ecosystem in excluded:
            continue
        # Also skip if repo name or full_name is directly excluded
        if repo_name in excluded or repo_full in excluded:
            continue

        score = 0
        signals: list[str] = []

        # stack_match
        if ecosystem and ecosystem in project_ecosystems:
            score += 2
            signals.append("stack_match")

        # interest_match — any keyword overlap
        repo_tokens = _repo_tokens(repo)
        if interest_kws and repo_tokens.intersection(interest_kws):
            score += 2
            signals.append("interest_match")

        # dependency_overlap — repo name matches an existing dep
        if repo_name in current_deps:
            score += 1
            signals.append("dependency_overlap")

        # new_entry
        is_new = _is_new_entry(repo)
        if is_new:
            score += 1
            signals.append("new_entry")

        if score >= 2:
            scored.append({**repo, "_match_score": score, "_signals": signals})

    # Sort by score descending, then by overall score if available
    scored.sort(
        key=lambda r: (r["_match_score"], (r.get("scores") or {}).get("overall", 0)),
        reverse=True,
    )
    return scored[:15]


def generate_recommendations_report(
    date: str,
    profile: dict,
    recommendations: list[dict],
) -> str:
    """
    Generate a markdown recommendations report.

    Each recommendation dict is expected to have at minimum:
      name, url, description, relevance, why, how_to_evaluate, effort
    """
    lines: list[str] = [
        f"# AI Trend Recommendations — {date}",
        "",
        f"> Project: **{profile.get('name', 'Unknown')}**",
        "",
    ]

    if profile.get("description"):
        lines += [f"> {profile['description']}", ""]

    if not recommendations:
        lines += [
            "No actionable recommendations today. "
            "No trending repositories matched this project's stack or interests.",
            "",
        ]
        return "\n".join(lines)

    high = [r for r in recommendations if r.get("relevance") == "high"]
    watch = [r for r in recommendations if r.get("relevance") == "watch"]
    new_entrants = [r for r in recommendations if r.get("relevance") == "new_entrant"]

    def _render_rec(rec: dict) -> list[str]:
        name = rec.get("name", "")
        url = rec.get("url", "")
        desc = rec.get("description", "")
        why = rec.get("why", "")
        how_to = rec.get("how_to_evaluate", "")
        effort = rec.get("effort", "")
        section: list[str] = []
        header = f"### [{name}]({url})" if url else f"### {name}"
        section.append(header)
        section.append("")
        if desc:
            section.append(f"_{desc}_")
            section.append("")
        if why:
            section.append(f"**Why it matters:** {why}")
            section.append("")
        if how_to:
            section.append(f"**How to evaluate:** {how_to}")
            section.append("")
        if effort:
            section.append(f"**Effort:** {effort}")
            section.append("")
        return section

    if high:
        lines += ["## High Relevance", ""]
        lines += ["Direct stack match — these repos solve a clear need for this project.", ""]
        for rec in high:
            lines += _render_rec(rec)
        lines += ["---", ""]

    if watch:
        lines += ["## Worth Watching", ""]
        lines += ["Interesting but not a direct match — worth keeping an eye on.", ""]
        for rec in watch:
            lines += _render_rec(rec)
        lines += ["---", ""]

    if new_entrants:
        lines += ["## New Entrants", ""]
        lines += ["Brand-new repos (< 6 months old) that align with this project's interests.", ""]
        for rec in new_entrants:
            lines += _render_rec(rec)
        lines += ["---", ""]

    return "\n".join(lines)


def run_recommendations(date: str = None, project_path: str = ".") -> Path:
    """
    Main entry point for the recommendations pipeline.

    1. Loads trending.json (metrics) for the given date.
    2. Scans the target project via scan_project().
    3. Pre-filters candidates via match_trending_to_project().
    4. Applies rule-based relevance classification:
         match_score >= 4  -> "high"
         match_score >= 2  -> "watch"
         new_entry signal  -> "new_entrant" (when score < 4)
    5. Saves a prompt for Claude Code analysis to data/YYYY-MM-DD/recommend_prompt.md.
    6. Saves the markdown report to reports/YYYY-MM-DD-recommendations.md.
    7. Returns the report path.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # 1. Load trending data
    # ------------------------------------------------------------------
    metrics_path = BASE_DIR / "data" / date / "metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        trending = json.load(f)

    # ------------------------------------------------------------------
    # 2. Scan project
    # ------------------------------------------------------------------
    profile = scan_project(project_path)

    # ------------------------------------------------------------------
    # 3. Pre-filter candidates
    # ------------------------------------------------------------------
    candidates = match_trending_to_project(trending, profile)
    print(f"  Pre-filter: {len(candidates)} candidates found")

    # ------------------------------------------------------------------
    # 4. Rule-based relevance classification
    # ------------------------------------------------------------------
    recommendations: list[dict] = []
    for repo in candidates:
        score = repo.get("_match_score", 0)
        signals = repo.get("_signals", [])
        is_new = "new_entry" in signals

        if score >= 4:
            relevance = "high"
        elif is_new and score < 4:
            relevance = "new_entrant"
        else:
            relevance = "watch"

        recommendations.append({
            "name": repo.get("name", ""),
            "url": repo.get("url", ""),
            "description": repo.get("description", ""),
            "relevance": relevance,
            "why": (
                f"Matched signals: {', '.join(signals)}. "
                f"Match score: {score}. "
                f"Language: {repo.get('language', 'unknown')}. "
                f"Stars: {repo.get('raw_metrics', {}).get('stars') or repo.get('stars', 'N/A')}."
            ),
            "how_to_evaluate": (
                f"Review the repository at {repo.get('url', '')} and check if it "
                "integrates with your existing stack."
            ),
            "effort": (
                "small" if score >= 4 else
                "medium" if score >= 2 else
                "large"
            ),
            # Preserve internal scoring for prompt
            "_match_score": score,
            "_signals": signals,
        })

    # ------------------------------------------------------------------
    # 5. Save prompt for Claude Code
    # ------------------------------------------------------------------
    template = load_prompt_template()

    profile_str = json.dumps(profile, ensure_ascii=False, indent=2)
    # Pass lean candidate data (drop internal fields)
    trending_candidates = [
        {k: v for k, v in r.items() if not k.startswith("_") and k != "readme_excerpt"}
        for r in candidates
    ]
    trending_str = json.dumps(trending_candidates, ensure_ascii=False, indent=2)

    prompt = template.replace("{{project_profile}}", profile_str).replace(
        "{{trending_data}}", trending_str
    )

    data_dir = BASE_DIR / "data" / date
    data_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = data_dir / "recommend_prompt.md"
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"  Prompt saved: {prompt_path}")

    # ------------------------------------------------------------------
    # 6. Generate and save markdown report
    # ------------------------------------------------------------------
    report_md = generate_recommendations_report(date, profile, recommendations)

    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{date}-recommendations.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  Report saved: {report_path}")

    return report_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    project_arg = sys.argv[2] if len(sys.argv) > 2 else "."
    path = run_recommendations(date_arg, project_arg)
    print(f"Done: {path}")

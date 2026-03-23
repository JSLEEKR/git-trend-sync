"""
recommend.py — rule-based project recommendation engine for ai-trend

Given a project profile (from scan_project) and trending repos (from collect/metrics),
pre-filters candidates by compatibility, scores them, and generates a markdown report.
Also saves a prompt file for optional Claude Code deep analysis.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.scan_project import scan_project, recommend_categories

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


def generate_comparison_table(candidates: list[dict], profile: dict) -> str:
    """
    Generate a feature comparison table in markdown format.

    The table compares each candidate repo against the user's own project
    across a fixed set of AI-relevant features.

    Parameters
    ----------
    candidates:
        List of pre-filtered repo dicts (as returned by match_trending_to_project).
    profile:
        Project profile dict (as returned by scan_project).

    Returns
    -------
    A markdown string containing the ## Feature Comparison section.
    """
    if not candidates:
        return ""

    # Limit to the top 5 candidates to keep the table readable
    display = candidates[:5]

    # ------------------------------------------------------------------
    # Helper: check a repo's description + topics for a keyword set
    # ------------------------------------------------------------------
    def _repo_has(repo: dict, *keywords: str) -> bool:
        text = " ".join([
            (repo.get("description") or "").lower(),
            " ".join(repo.get("topics") or []).lower(),
            (repo.get("name") or "").lower(),
        ])
        return any(kw in text for kw in keywords)

    # ------------------------------------------------------------------
    # Helper: format star count with thousands separator
    # ------------------------------------------------------------------
    def _fmt_stars(repo: dict) -> str:
        stars = (repo.get("raw_metrics") or {}).get("stars") or repo.get("stars")
        if stars is None:
            return "N/A"
        try:
            return f"{int(stars):,}"
        except (ValueError, TypeError):
            return str(stars)

    # ------------------------------------------------------------------
    # Helper: trend score cell with emoji
    # ------------------------------------------------------------------
    def _fmt_trend(repo: dict) -> str:
        score = (repo.get("scores") or {}).get("overall")
        if score is None:
            return "N/A"
        try:
            val = float(score)
        except (ValueError, TypeError):
            return str(score)
        emoji = "🔥" if val >= 8.0 else "📈" if val >= 5.0 else "📉"
        return f"{emoji} {val:.1f}"

    # ------------------------------------------------------------------
    # Helper: active development cell
    # ------------------------------------------------------------------
    def _fmt_activity(repo: dict) -> str:
        commits = (repo.get("raw_metrics") or {}).get("commits_last_30_days")
        if commits is None:
            commits = repo.get("recent_commits_30d")
        if commits is None:
            return "N/A"
        try:
            c = int(commits)
        except (ValueError, TypeError):
            return str(commits)
        if c > 50:
            return f"✅ ({c} commits/30d)"
        elif c > 10:
            return f"⚠️ ({c} commits/30d)"
        else:
            return f"❌ ({c} commits/30d)"

    # ------------------------------------------------------------------
    # Helper: stack compatible cell
    # ------------------------------------------------------------------
    def _fmt_stack_compat(repo: dict, profile: dict) -> str:
        project_ecosystems = _project_ecosystems(profile)
        eco = _repo_ecosystem(repo)
        if eco and eco in project_ecosystems:
            return "✅"
        return "❌"

    # ------------------------------------------------------------------
    # Feature detection for a repo: returns ✅ / ❌
    # ------------------------------------------------------------------
    def _bool_cell(flag: bool) -> str:
        return "✅" if flag else "❌"

    # ------------------------------------------------------------------
    # "Your Project" feature detection from profile
    # ------------------------------------------------------------------
    profile_deps: set[str] = set(profile.get("current_dependencies") or [])
    profile_hints: str = " ".join(profile.get("architecture_hints") or []).lower()
    profile_interests: str = " ".join(profile.get("declared_interests") or []).lower()
    profile_text = profile_hints + " " + profile_interests

    def _project_dep_label(*dep_names: str) -> str:
        """Return ✅ (dep_name) if any of the given dep names are in profile_deps."""
        for dep in dep_names:
            if dep in profile_deps:
                return f"✅ ({dep})"
        return "❌"

    def _project_text_has(*keywords: str) -> str:
        for kw in keywords:
            if kw in profile_text:
                return "✅"
        return "❌"

    # RAG support: uses LLM framework or vector store hint
    rag_deps = {"langchain", "langchain-core", "langchain-community",
                "llama-index", "llama_index", "haystack-ai", "haystack"}
    project_rag = _project_dep_label(*rag_deps)

    # Agent framework
    agent_deps = {"crewai", "autogen", "metagpt", "dspy", "dspy-ai", "phidata"}
    project_agent = _project_dep_label(*agent_deps)

    # Vector store
    vector_deps = {"chromadb", "pinecone-client", "pinecone", "weaviate-client",
                   "qdrant-client", "faiss-cpu", "faiss-gpu", "faiss",
                   "milvus", "pymilvus", "lancedb", "pgvector"}
    project_vector = _project_dep_label(*vector_deps)

    # Multi-agent: agent framework OR "multi-agent" / "orchestrat" in hints
    project_multi_agent = "✅" if (
        any(d in profile_deps for d in {"crewai", "autogen", "metagpt"})
        or "multi-agent" in profile_text
        or "orchestrat" in profile_text
    ) else "❌"

    # API server
    api_deps = {"fastapi", "flask", "django", "starlette", "express"}
    project_api = _project_dep_label(*api_deps)

    # UI / Dashboard
    ui_deps = {"react", "vue", "angular", "svelte", "next", "nuxt", "remix"}
    project_ui = _project_dep_label(*ui_deps)

    # MCP
    project_mcp = "✅" if (
        any("mcp" in d for d in profile_deps) or "mcp" in profile_text
    ) else "❌"

    # Project language (best-effort from detected_stack)
    stack = profile.get("tech_stack_override") or profile.get("detected_stack") or []
    project_lang = stack[0].capitalize() if stack else "-"

    # ------------------------------------------------------------------
    # Build table rows
    # ------------------------------------------------------------------
    repo_names = [repo.get("name", f"repo-{i}") for i, repo in enumerate(display)]
    col_header = " | ".join(repo_names) + " | Your Project"
    separator = " | ".join(["--------"] * len(display)) + " | ------------|"

    def _row(feature: str, *cells: str) -> str:
        return f"| {feature} | " + " | ".join(cells) + " |"

    rows: list[str] = [
        _row("Language",
             *[repo.get("language") or "N/A" for repo in display],
             project_lang),
        _row("License",
             *[repo.get("license") or "-" for repo in display],
             "-"),
        _row("Stars",
             *[_fmt_stars(repo) for repo in display],
             "-"),
        _row("Trend Score",
             *[_fmt_trend(repo) for repo in display],
             "-"),
        _row("RAG Support",
             *[_bool_cell(_repo_has(repo, "rag", "retrieval")) for repo in display],
             project_rag),
        _row("Agent Framework",
             *[_bool_cell(_repo_has(repo, "agent")) for repo in display],
             project_agent),
        _row("Vector Store",
             *[_bool_cell(_repo_has(repo, "vector", "embedding")) for repo in display],
             project_vector),
        _row("Multi-Agent",
             *[_bool_cell(_repo_has(repo, "multi-agent", "orchestrat")) for repo in display],
             project_multi_agent),
        _row("API Server",
             *[_bool_cell(_repo_has(repo, "api", "server", "rest")) for repo in display],
             project_api),
        _row("UI/Dashboard",
             *[_bool_cell(_repo_has(repo, "ui", "dashboard", "frontend", "web")) for repo in display],
             project_ui),
        _row("MCP Support",
             *[_bool_cell(_repo_has(repo, "mcp", "model context protocol")) for repo in display],
             project_mcp),
        _row("Active Development",
             *[_fmt_activity(repo) for repo in display],
             "-"),
        _row("Stack Compatible",
             *[_fmt_stack_compat(repo, profile) for repo in display],
             "-"),
    ]

    header_line = "| Feature | " + col_header + " |"
    sep_line = "|---------|" + separator

    lines = ["## Feature Comparison", "", header_line, sep_line] + rows + [""]
    return "\n".join(lines)


def generate_recommendations_report(
    date: str,
    profile: dict,
    recommendations: list[dict],
    candidates: list[dict] | None = None,
) -> str:
    """
    Generate a markdown recommendations report.

    Each recommendation dict is expected to have at minimum:
      name, url, description, relevance, why, how_to_evaluate, effort

    Parameters
    ----------
    date:
        ISO date string for the report header.
    profile:
        Project profile dict as returned by scan_project().
    recommendations:
        List of recommendation dicts with relevance classification.
    candidates:
        Optional list of pre-filtered candidate repos used to build the
        feature comparison table.
    """
    lines: list[str] = [
        f"# AI Trend Recommendations — {date}",
        "",
        f"> Project: **{profile.get('name', 'Unknown')}**",
        "",
    ]

    if profile.get("description"):
        lines += [f"> {profile['description']}", ""]

    # ------------------------------------------------------------------
    # Recommended categories section
    # ------------------------------------------------------------------
    rec_cats = recommend_categories(profile)
    if rec_cats:
        lines += [
            "**Recommended categories for this project:** "
            + ", ".join(f"`{c}`" for c in rec_cats),
            "",
        ]

    if not recommendations:
        lines += [
            "No actionable recommendations today. "
            "No trending repositories matched this project's stack or interests.",
            "",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Feature comparison table (uses raw candidates for repo metadata)
    # ------------------------------------------------------------------
    if candidates:
        table = generate_comparison_table(candidates, profile)
        if table:
            lines += [table]

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
    report_md = generate_recommendations_report(date, profile, recommendations, candidates)

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

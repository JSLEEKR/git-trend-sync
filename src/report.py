"""
Generate English markdown trend reports from analysis data.
"""

import json
import re
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def extract_json_from_text(text: str) -> dict | None:
    """Try to extract JSON from Claude Code output text."""
    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find JSON block in markdown
    patterns = [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
        r'\{.*\}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if match.lastindex else match.group(0))
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def load_analysis(analysis_dir: Path, category: str) -> dict | None:
    """Load analysis result for a category."""
    safe_name = category.lower().replace(" ", "_")
    path = analysis_dir / f"{safe_name}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Claude Code --output-format json wraps in {"result": "..."}
    data = extract_json_from_text(content)
    if data and "result" in data:
        return extract_json_from_text(data["result"])
    return data


def score_bar(score: float) -> str:
    """Create a visual score bar."""
    filled = round(score)
    return "█" * filled + "░" * (10 - filled)


def _trend_emoji(trend_score: float) -> str:
    """Return an emoji indicator based on trend score."""
    if trend_score >= 7:
        return "🔥"
    if trend_score >= 4:
        return "📈"
    return ""


def _status(repo: dict) -> str:
    """Derive status label from repo trending data."""
    if repo.get("is_new_entry"):
        return "NEW ENTRY"
    if repo.get("days_of_data", 0) == 0:
        return "DAY 1"
    return "TRENDING"


def _age_label(age_days: int) -> str:
    """Format age in days or years."""
    if age_days >= 365:
        return f"{age_days // 365}y"
    return f"{age_days}d"


def _delta_1d(repo: dict) -> str:
    """Format 1-day star delta."""
    if repo.get("days_of_data", 0) == 0:
        return "N/A"
    return f"+{repo['star_delta_1d']}"


def _delta_7d(repo: dict) -> str:
    """Format 7-day average star delta."""
    if repo.get("days_of_data", 0) == 0:
        return "N/A"
    return f"+{repo['star_delta_7d_avg']}/d"


def generate_en_report(date: str, trending: dict, analyses: dict) -> str:
    """Generate English markdown report from trending data."""
    lines = [
        f"# AI Agent Trend Report — {date}",
        "",
        f"> Auto-generated on {date}. Velocity-based trending from GitHub Topics. "
        "Qualitative analysis powered by Claude Code.",
        "",
        "## Table of Contents",
        "",
    ]

    # TOC
    for cat_name in trending["categories"]:
        anchor = cat_name.lower().replace(" ", "-")
        lines.append(f"- [{cat_name}](#{anchor})")
    lines.append("- [Cross-Category Insights](#cross-category-insights)")
    lines.append("")

    # Per-category sections
    for cat_name, repos in trending["categories"].items():
        lines.append(f"## {cat_name}")
        lines.append("")

        # Trending table
        lines.append("### Trending Repositories")
        lines.append("")
        lines.append("| # | Repository | Trend | Stars | +1d | +7d avg | Age | Status |")
        lines.append("|---|-----------|-------|-------|-----|---------|-----|--------|")

        for i, r in enumerate(repos, 1):
            trend_score = r.get("trend_score", 0)
            emoji = _trend_emoji(trend_score)
            trend_cell = f"{emoji} {trend_score}" if emoji else str(trend_score)
            stars_fmt = f"{r['stars']:,}"
            age_label = _age_label(r.get("age_days", 0))
            status = _status(r)
            lines.append(
                f"| {i} | [{r['name']}]({r['url']}) | "
                f"{trend_cell} | "
                f"{stars_fmt} | "
                f"{_delta_1d(r)} | "
                f"{_delta_7d(r)} | "
                f"{age_label} | "
                f"{status} |"
            )
        lines.append("")

        # Qualitative analysis
        analysis = analyses.get(cat_name)
        if analysis and "error" not in analysis:
            # Individual analysis
            if "individual_analysis" in analysis:
                lines.append("### Individual Analysis")
                lines.append("")
                for item in analysis["individual_analysis"]:
                    lines.append(f"#### {item['name']}")
                    lines.append("")
                    lines.append("**Pros:**")
                    for pro in item.get("pros", []):
                        lines.append(f"- {pro}")
                    lines.append("")
                    lines.append("**Cons:**")
                    for con in item.get("cons", []):
                        lines.append(f"- {con}")
                    lines.append("")

            # Good combinations
            if "good_combinations" in analysis:
                lines.append("### Recommended Combinations")
                lines.append("")
                for combo in analysis["good_combinations"]:
                    repos_str = " + ".join(combo["repos"])
                    lines.append(f"- **{repos_str}**: {combo['reason']}")
                lines.append("")

            # Bad combinations
            if "bad_combinations" in analysis:
                lines.append("### Avoid Combining")
                lines.append("")
                for combo in analysis["bad_combinations"]:
                    repos_str = " + ".join(combo["repos"])
                    lines.append(f"- **{repos_str}**: {combo['reason']}")
                lines.append("")

            # Ranking
            if "ranking" in analysis:
                lines.append("### Ranking")
                lines.append("")
                for item in analysis["ranking"]:
                    lines.append(f"{item['rank']}. **{item['name']}** — {item['justification']}")
                lines.append("")
        else:
            lines.append("*Qualitative analysis not available for this category.*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Cross-category insights
    lines.append("## Cross-Category Insights")
    lines.append("")
    lines.append("### Top Repositories Across All Categories")
    lines.append("")

    all_repos = []
    for cat_name, repos in trending["categories"].items():
        for r in repos:
            all_repos.append({**r, "category": cat_name})
    all_repos.sort(key=lambda x: x.get("trend_score", 0), reverse=True)

    lines.append("| Rank | Repository | Category | Trend Score |")
    lines.append("|------|-----------|----------|-------------|")
    for i, r in enumerate(all_repos[:10], 1):
        trend_score = r.get("trend_score", 0)
        emoji = _trend_emoji(trend_score)
        trend_cell = f"{emoji} {trend_score}" if emoji else str(trend_score)
        lines.append(
            f"| {i} | [{r['name']}]({r['url']}) | {r['category']} | **{trend_cell}** |"
        )
    lines.append("")

    return "\n".join(lines)


def generate_reports(date: str = None) -> Path:
    """Generate English-only report."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    data_dir = BASE_DIR / "data" / date
    trending_path = data_dir / "trending.json"
    metrics_path = data_dir / "metrics.json"
    analysis_dir = data_dir / "analysis"

    # Prefer trending.json; fall back to metrics.json
    if trending_path.exists():
        with open(trending_path, "r", encoding="utf-8") as f:
            trending = json.load(f)
    else:
        with open(metrics_path, "r", encoding="utf-8") as f:
            trending = json.load(f)

    # Load analyses
    analyses = {}
    for cat_name in trending["categories"]:
        analysis = load_analysis(analysis_dir, cat_name)
        if analysis:
            analyses[cat_name] = analysis

    # Generate report
    en_report = generate_en_report(date, trending, analyses)

    # Save
    report_dir = BASE_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"{date}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(en_report)

    print(f"Report generated: {report_path}")
    return report_path


if __name__ == "__main__":
    generate_reports()

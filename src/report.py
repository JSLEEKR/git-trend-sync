"""
Generate English markdown trend reports from multi-signal analysis data.
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


def _signal_emoji(signal_type: str) -> str:
    """Return an emoji indicator based on signal type."""
    mapping = {
        "surge": "🔥",
        "newcomer": "🌱",
        "momentum": "📈",
    }
    return mapping.get(signal_type, "")


def _signal_detail(repo: dict) -> str:
    """Return detail string based on signal_type."""
    signal_type = repo.get("signal_type", "")
    if signal_type == "surge":
        ratio = repo.get("surge_ratio", 0)
        return f"x{ratio} this week"
    if signal_type == "newcomer":
        age = repo.get("age_days", 0)
        spd = repo.get("stars_per_day_avg", 0)
        return f"{age}d, {spd}/day"
    if signal_type == "momentum":
        commits = repo.get("recent_commits_7d", 0)
        return f"{commits} commits/7d"
    return ""


def _age_label(age_days: int) -> str:
    """Format age in days or years."""
    if age_days >= 365:
        return f"{age_days // 365}y"
    return f"{age_days}d"


def _last_push_label(repo: dict) -> str:
    """Format pushed_at as 'X days ago'."""
    from datetime import datetime, timezone
    pushed_at = repo.get("pushed_at", "")
    if not pushed_at:
        return "unknown"
    try:
        dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
        if days == 0:
            return "today"
        if days == 1:
            return "1d ago"
        return f"{days}d ago"
    except (ValueError, TypeError):
        return "unknown"


def _collect_all_repos(trending: dict) -> list[dict]:
    """Flatten repos across categories, adding _category field."""
    all_repos = []
    for cat_name, repos in trending.get("categories", {}).items():
        for r in repos:
            all_repos.append({**r, "_category": cat_name})
    return all_repos


def _render_signal_table(title: str, repos: list[dict], score_key: str, limit: int) -> list[str]:
    """Render a ranked signal table."""
    lines = [f"### {title}", ""]
    lines.append("| # | Repository | Category | Signal | Score | Detail |")
    lines.append("|---|-----------|----------|--------|-------|--------|")
    for i, r in enumerate(repos[:limit], 1):
        emoji = _signal_emoji(r.get("signal_type", ""))
        detail = _signal_detail(r)
        score = r.get(score_key, 0)
        cat = r.get("_category", "")
        lines.append(
            f"| {i} | [{r['name']}]({r['url']}) | {cat} | {emoji} | {score} | {detail} |"
        )
    lines.append("")
    return lines


def generate_en_report(date: str, trending: dict, analyses: dict) -> str:
    """Generate English markdown report from trending data."""
    lines = [
        f"# AI Agent Trend Report — {date}",
        "",
        f"> Auto-generated on {date}. Multi-signal scoring (surge, newcomer, momentum) from GitHub Topics. "
        "Qualitative analysis powered by Claude Code.",
        "",
    ]

    # --- Cross-Category Highlights ---
    all_repos = _collect_all_repos(trending)

    lines.append("## Cross-Category Highlights")
    lines.append("")

    # Top 10 Surging
    surging = sorted(all_repos, key=lambda x: x.get("surge_score", 0), reverse=True)
    lines.extend(_render_signal_table("Top 10 Surging", surging, "surge_score", 10))

    # Top 10 Rising Stars
    rising = [r for r in all_repos if r.get("newcomer_score", 0) > 0]
    rising.sort(key=lambda x: x.get("newcomer_score", 0), reverse=True)
    if rising:
        lines.extend(_render_signal_table("Top 10 Rising Stars", rising, "newcomer_score", 10))

    # Top 10 Momentum
    momentum = sorted(all_repos, key=lambda x: x.get("momentum_score", 0), reverse=True)
    lines.extend(_render_signal_table("Top 10 Momentum", momentum, "momentum_score", 10))

    # Top 10 Overall
    overall = sorted(all_repos, key=lambda x: x.get("trend_score", 0), reverse=True)
    lines.extend(_render_signal_table("Top 10 Overall", overall, "trend_score", 10))

    lines.append("---")
    lines.append("")

    # --- Per-Category Sections ---
    for cat_name, repos in trending["categories"].items():
        lines.append(f"## {cat_name}")
        lines.append("")

        # Surging top 3
        cat_surging = sorted(repos, key=lambda x: x.get("surge_score", 0), reverse=True)[:3]
        if cat_surging:
            lines.append("### Surging")
            lines.append("")
            lines.append("| # | Repository | Score | Detail |")
            lines.append("|---|-----------|-------|--------|")
            for i, r in enumerate(cat_surging, 1):
                lines.append(
                    f"| {i} | [{r['name']}]({r['url']}) | {r.get('surge_score', 0)} | {_signal_detail({**r, 'signal_type': 'surge'})} |"
                )
            lines.append("")

        # Rising Stars top 3
        cat_rising = [r for r in repos if r.get("newcomer_score", 0) > 0]
        cat_rising.sort(key=lambda x: x.get("newcomer_score", 0), reverse=True)
        cat_rising = cat_rising[:3]
        if cat_rising:
            lines.append("### Rising Stars")
            lines.append("")
            lines.append("| # | Repository | Score | Detail |")
            lines.append("|---|-----------|-------|--------|")
            for i, r in enumerate(cat_rising, 1):
                lines.append(
                    f"| {i} | [{r['name']}]({r['url']}) | {r.get('newcomer_score', 0)} | {_signal_detail({**r, 'signal_type': 'newcomer'})} |"
                )
            lines.append("")

        # Gaining Momentum top 3
        cat_momentum = sorted(repos, key=lambda x: x.get("momentum_score", 0), reverse=True)[:3]
        if cat_momentum:
            lines.append("### Gaining Momentum")
            lines.append("")
            lines.append("| # | Repository | Score | Detail |")
            lines.append("|---|-----------|-------|--------|")
            for i, r in enumerate(cat_momentum, 1):
                lines.append(
                    f"| {i} | [{r['name']}]({r['url']}) | {r.get('momentum_score', 0)} | {_signal_detail({**r, 'signal_type': 'momentum'})} |"
                )
            lines.append("")

        # Overall Top 5
        cat_overall = sorted(repos, key=lambda x: x.get("trend_score", 0), reverse=True)[:5]
        if cat_overall:
            lines.append("### Overall Top 5")
            lines.append("")
            lines.append("| # | Repository | Trend | Surge | Newcomer | Momentum | Signal |")
            lines.append("|---|-----------|-------|-------|----------|----------|--------|")
            for i, r in enumerate(cat_overall, 1):
                emoji = _signal_emoji(r.get("signal_type", ""))
                lines.append(
                    f"| {i} | [{r['name']}]({r['url']}) | "
                    f"{r.get('trend_score', 0)} | "
                    f"{r.get('surge_score', 0)} | "
                    f"{r.get('newcomer_score', 0)} | "
                    f"{r.get('momentum_score', 0)} | "
                    f"{emoji} |"
                )
            lines.append("")

        # AI Analysis Ranking
        analysis = analyses.get(cat_name)
        if analysis and "error" not in analysis:
            if "ranking" in analysis:
                lines.append("### AI Analysis Ranking")
                lines.append("")
                for item in analysis["ranking"]:
                    lines.append(f"{item['rank']}. **{item['name']}** — {item['justification']}")
                lines.append("")
        else:
            lines.append("*Qualitative analysis not available for this category.*")
            lines.append("")

        lines.append("---")
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

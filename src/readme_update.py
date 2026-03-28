"""Auto-update README.md with today's trending data."""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TREND_START = "<!-- TREND-START -->"
TREND_END = "<!-- TREND-END -->"


def _format_stars(stars: int) -> str:
    """Format star count with comma separators."""
    return f"{stars:,}"


def _get_top_repos(categories: dict, top_n: int = 10) -> list:
    """Collect the top N repos across all categories by trend score."""
    all_repos = []
    for cat_name, repos in categories.items():
        for repo in repos:
            all_repos.append({**repo, "_category": cat_name})

    # Deduplicate by full_name, keeping highest score
    seen = {}
    for repo in all_repos:
        key = repo.get("full_name", repo["name"])
        if key not in seen or repo["trend_score"] > seen[key]["trend_score"]:
            seen[key] = repo

    sorted_repos = sorted(seen.values(), key=lambda r: r["trend_score"], reverse=True)
    return sorted_repos[:top_n]


def _signal_emoji(signal_type: str) -> str:
    """Return emoji for a signal type."""
    return {"surge": "🔥", "newcomer": "🆕", "momentum": "📈"}.get(signal_type, "➡️")


def _signal_detail(repo: dict) -> str:
    """Return context-specific detail string based on signal_type."""
    signal = repo.get("signal_type", "")
    if signal == "surge":
        ratio = repo.get("surge_ratio", 0)
        return f"x{ratio:.1f} this week"
    elif signal == "newcomer":
        age = repo.get("age_days", 0)
        spd = repo.get("stars_per_day_avg", 0)
        return f"{age}d, {spd:.1f}/day"
    elif signal == "momentum":
        commits = repo.get("recent_commits_7d", 0)
        return f"{commits} commits/7d"
    return "—"


def _build_trend_section(date: str, repos: list) -> str:
    """Build the markdown content to insert between the trend markers."""
    header = f"### Today's Top Trending ({date})\n"

    table_rows = [
        "| # | Repository | Category | Score | Signal | Detail |",
        "|---|-----------|----------|-------|--------|--------|",
    ]
    for rank, repo in enumerate(repos, 1):
        name = repo["name"]
        url = repo.get("url", f"https://github.com/{repo.get('full_name', name)}")
        category = repo.get("_category", "—")
        score = repo.get("trend_score", 0)
        signal_type = repo.get("signal_type", "")
        signal = f"{_signal_emoji(signal_type)} {signal_type}" if signal_type else "—"
        detail = _signal_detail(repo)
        table_rows.append(
            f"| {rank} | [{name}]({url}) | {category} | {score:.1f} | {signal} | {detail} |"
        )

    table = "\n".join(table_rows)
    footer = f"\n> Last updated: {date} — [Full Report](reports/{date}.md)"

    return f"{header}\n{table}\n{footer}\n"


def update_readme(date: str = None) -> Path:
    """Update README.md with the latest trending top 10.

    Args:
        date: Date string in YYYY-MM-DD format. Defaults to today.

    Returns:
        Path to the updated README.md file.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    trending_path = BASE_DIR / "data" / date / "trending.json"
    if not trending_path.exists():
        print(f"No trending data found for {date} at {trending_path}")
        readme_path = BASE_DIR / "README.md"
        return readme_path

    with open(trending_path, "r", encoding="utf-8") as f:
        trending = json.load(f)

    categories = trending.get("categories", {})
    top_repos = _get_top_repos(categories, top_n=10)
    trend_section = _build_trend_section(date, top_repos)

    readme_path = BASE_DIR / "README.md"
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_idx = content.find(TREND_START)
    end_idx = content.find(TREND_END)

    if start_idx == -1 or end_idx == -1:
        print("Trend markers not found in README.md — skipping update.")
        return readme_path

    # Replace everything between (and including) the markers
    before = content[: start_idx + len(TREND_START)]
    after = content[end_idx:]
    new_content = f"{before}\n{trend_section}{after}"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"README.md updated with trending data for {date}")
    return readme_path


if __name__ == "__main__":
    update_readme()

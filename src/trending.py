"""
Activity-based trend scoring.
Sorts repos by recent 30-day commit activity with stars as tiebreaker.
Minimum 1000 stars enforced at collection time.
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


def compute_activity_scores(raw_data: dict) -> dict:
    """Score repos by commits_30d (normalized 0-10), sort, take top 10 per category."""
    # Load previous day's trending.json to detect new entries
    prev_repo_set: set[str] = set()
    data_root = BASE_DIR / "data"
    target_date = raw_data.get("date", "")
    if target_date and data_root.exists():
        # Find the most recent date directory before today
        date_dirs = sorted(
            [
                d.name
                for d in data_root.iterdir()
                if d.is_dir() and d.name < target_date
            ],
            reverse=True,
        )
        if date_dirs:
            prev_trending = data_root / date_dirs[0] / "trending.json"
            if prev_trending.exists():
                try:
                    with open(prev_trending, encoding="utf-8") as f:
                        prev_data = json.load(f)
                    for repos in prev_data.get("categories", {}).values():
                        for r in repos:
                            prev_repo_set.add(r.get("full_name", ""))
                except (json.JSONDecodeError, OSError):
                    pass

    result: dict[str, list[dict]] = {}

    for cat_name, repos in raw_data["categories"].items():
        if not repos:
            result[cat_name] = []
            continue

        # Sort by commits_30d descending, stars as tiebreaker
        sorted_repos = sorted(
            repos,
            key=lambda r: (r.get("recent_commits_30d", 0), r.get("stars", 0)),
            reverse=True,
        )

        # Min-max normalization of commits_30d within category (0-10 scale)
        commit_values = [r.get("recent_commits_30d", 0) for r in sorted_repos]
        min_commits = min(commit_values)
        max_commits = max(commit_values)
        commit_range = max_commits - min_commits

        scored: list[dict] = []
        for r in sorted_repos:
            commits = r.get("recent_commits_30d", 0)
            if commit_range > 0:
                trend_score = round((commits - min_commits) / commit_range * 10, 1)
            else:
                trend_score = 10.0 if commits > 0 else 0.0

            age_days = days_since(r.get("created_at", ""))
            stars = r.get("stars", 0)
            stars_per_day_avg = round(stars / max(age_days, 1), 1)

            scored.append(
                {
                    **r,
                    "trend_score": trend_score,
                    "stars_per_day_avg": stars_per_day_avg,
                    "age_days": age_days,
                    "is_new_entry": r.get("full_name", "") not in prev_repo_set,
                }
            )

        result[cat_name] = scored[:10]

    return {"date": raw_data["date"], "categories": result}


def run_trending(date: str = None) -> dict:
    """Load raw data and compute activity-based trend scores."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    raw_path = BASE_DIR / "data" / date / "raw.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    trending = compute_activity_scores(raw_data)

    output_path = BASE_DIR / "data" / date / "trending.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(trending, f, ensure_ascii=False, indent=2)

    print(f"Trending scores saved to {output_path}")
    return trending


if __name__ == "__main__":
    run_trending()

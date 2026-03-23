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
        + min(commits / 30, 10) * 0.15,
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
    accel_norm = max(min(acceleration / 50, 1), -1) * 5 + 5

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
    prev_repo_set = set()
    for snap in snapshots[:-1]:
        prev_repo_set.update(snap["repos"].keys())

    result = {}
    for cat_name, repos in raw_data["categories"].items():
        scored = []
        for r in repos:
            instant = compute_instant_score(r)
            vel = compute_velocity_score(r["full_name"], snapshots)

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

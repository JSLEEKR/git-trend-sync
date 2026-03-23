"""
수집된 데이터에서 정량 메트릭을 계산하고 카테고리 내 정규화합니다.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def normalize(values: list[float]) -> list[float]:
    """Min-max normalize to 0-10 scale."""
    if not values:
        return values
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [5.0] * len(values)
    return [round((v - min_v) / (max_v - min_v) * 10, 1) for v in values]


def days_since(date_str: str) -> int:
    """Calculate days since a given ISO date string."""
    if not date_str:
        return 9999
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return 9999


def compute_metrics(raw_data: dict) -> dict:
    """Compute normalized metrics for each category."""
    result = {}

    for cat_name, repos in raw_data["categories"].items():
        if not repos:
            result[cat_name] = []
            continue

        # Raw metric extraction
        popularity_raw = [r["stars"] + r["forks"] for r in repos]
        activity_raw = [
            r["recent_commits_30d"] * 10 + max(0, 30 - days_since(r["pushed_at"]))
            for r in repos
        ]
        # Community health: lower open issues ratio is better
        community_raw = []
        for r in repos:
            open_issues = r["open_issues"]
            stars = max(r["stars"], 1)
            # Fewer open issues per star = healthier
            community_raw.append(max(0, 10 - (open_issues / stars) * 100))
        growth_raw = [r["recent_commits_30d"] + r["stars"] * 0.01 for r in repos]
        maturity_raw = [days_since(r["created_at"]) for r in repos]

        # Normalize
        pop_norm = normalize(popularity_raw)
        act_norm = normalize(activity_raw)
        com_norm = normalize(community_raw)
        gro_norm = normalize(growth_raw)
        mat_norm = normalize(maturity_raw)

        category_repos = []
        for i, r in enumerate(repos):
            scores = {
                "popularity": pop_norm[i],
                "activity": act_norm[i],
                "community_health": com_norm[i],
                "growth": gro_norm[i],
                "maturity": mat_norm[i],
                "overall": round(
                    pop_norm[i] * 0.25
                    + act_norm[i] * 0.25
                    + com_norm[i] * 0.2
                    + gro_norm[i] * 0.15
                    + mat_norm[i] * 0.15,
                    1,
                ),
            }
            category_repos.append({
                "name": r["name"],
                "full_name": r["full_name"],
                "url": r["url"],
                "description": r["description"],
                "language": r["language"],
                "license": r["license"],
                "scores": scores,
                "raw_metrics": {
                    "stars": r["stars"],
                    "forks": r["forks"],
                    "open_issues": r["open_issues"],
                    "recent_commits_30d": r["recent_commits_30d"],
                    "created_at": r["created_at"],
                    "pushed_at": r["pushed_at"],
                },
                "readme_excerpt": r.get("readme_excerpt", ""),
            })

        # Sort by overall score
        category_repos.sort(key=lambda x: x["scores"]["overall"], reverse=True)
        result[cat_name] = category_repos

    return {"date": raw_data["date"], "categories": result}


def run_metrics(date: str = None) -> dict:
    """Load raw data and compute metrics."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    raw_path = BASE_DIR / "data" / date / "raw.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    metrics = compute_metrics(raw_data)

    output_path = BASE_DIR / "data" / date / "metrics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"Metrics saved to {output_path}")
    return metrics


if __name__ == "__main__":
    run_metrics()

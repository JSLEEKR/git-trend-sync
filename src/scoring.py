"""
Multi-signal trend scoring engine.

Three signals:
  - Surge (40%): detects sudden commit spikes vs baseline
  - Newcomer (30%): rewards young repos with fast star growth
  - Momentum (30%): measures week-over-week acceleration

Each signal is percentile-ranked (0-10) within its category,
then combined into a composite trend_score.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Signal computations
# ---------------------------------------------------------------------------

def days_since(date_str: str) -> int:
    """Return number of days between date_str and now (UTC)."""
    if not date_str:
        return 9999
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return 9999


def compute_surge_ratio(commits_7d: int, commits_30d: int) -> float:
    """Ratio of 7-day commits to the average weekly rate of the remaining 23 days."""
    if commits_7d == 0 and commits_30d == 0:
        return 0.0
    avg_weekly_rest = (commits_30d - commits_7d) / 3
    return commits_7d / max(avg_weekly_rest, 1)


def compute_newcomer_raw(stars: int, age_days: int) -> float:
    """Stars-per-day weighted by freshness. Zero for repos >= 180 days old."""
    if age_days >= 180:
        return 0.0
    stars_per_day = stars / max(age_days, 1)
    freshness_bonus = (180 - age_days) / 180
    return round(stars_per_day * freshness_bonus, 1)


def compute_momentum_raw(
    commits_7d: int,
    commits_30d: int,
    prev_commits_30d: int | None,
    prev_stars: int | None,
    stars: int,
) -> float:
    """Week-over-week acceleration. Uses previous snapshot when available."""
    if prev_commits_30d is not None and prev_stars is not None:
        prev_commits_7d_estimate = max(0, prev_commits_30d - commits_30d + commits_7d)
        commit_delta = commits_7d - prev_commits_7d_estimate
        star_delta = stars - prev_stars
        return commit_delta + star_delta * 0.1
    else:
        avg_weekly_rest = (commits_30d - commits_7d) / 3
        return commits_7d - avg_weekly_rest


# ---------------------------------------------------------------------------
# Percentile ranking
# ---------------------------------------------------------------------------

def percentile_scores(values: list[float]) -> list[float]:
    """Map raw values to 0-10 percentile scores."""
    if not values:
        return []
    if len(values) == 1:
        return [10.0]
    sorted_vals = sorted(values)
    return [round(sorted_vals.index(v) / (len(values) - 1) * 10, 1) for v in values]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _determine_signal_type(surge: float, newcomer: float, momentum: float) -> str:
    """Return the name of the dominant signal."""
    signals = {"surge": surge, "newcomer": newcomer, "momentum": momentum}
    return max(signals, key=signals.get)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def compute_scores(raw_data: dict, prev_data: dict | None = None) -> dict:
    """Compute multi-signal scores for every repo in raw_data.

    Returns a dict with the same structure: {date, categories: {name: [repo...]}}.
    Each repo gets surge_score, newcomer_score, momentum_score, trend_score,
    surge_ratio, signal_type, stars_per_day_avg, age_days, is_new_entry.
    """
    # Build lookup for previous data
    prev_lookup: dict[str, dict] = {}
    prev_repo_set: set[str] = set()
    if prev_data:
        for repos in prev_data.get("categories", {}).values():
            for r in repos:
                fn = r.get("full_name", "")
                prev_lookup[fn] = r
                prev_repo_set.add(fn)

    result: dict[str, list[dict]] = {}

    for cat_name, repos in raw_data.get("categories", {}).items():
        if not repos:
            result[cat_name] = []
            continue

        # --- compute raw signals ---
        surge_raws: list[float] = []
        newcomer_raws: list[float] = []
        momentum_raws: list[float] = []
        enriched: list[dict] = []

        for r in repos:
            stars = r.get("stars", 0)
            commits_30d = r.get("recent_commits_30d", 0)
            commits_7d = r.get("recent_commits_7d", 0)
            age = days_since(r.get("created_at", ""))
            stars_per_day_avg = round(stars / max(age, 1), 1)

            surge_raw = compute_surge_ratio(commits_7d, commits_30d)
            newcomer_raw = compute_newcomer_raw(stars, age)

            prev = prev_lookup.get(r.get("full_name", ""))
            prev_commits_30d = prev.get("recent_commits_30d") if prev else None
            prev_stars = prev.get("stars") if prev else None
            momentum_raw = compute_momentum_raw(
                commits_7d, commits_30d, prev_commits_30d, prev_stars, stars
            )

            surge_raws.append(surge_raw)
            newcomer_raws.append(newcomer_raw)
            momentum_raws.append(momentum_raw)
            enriched.append(
                {
                    **r,
                    "surge_ratio": round(surge_raw, 2),
                    "stars_per_day_avg": stars_per_day_avg,
                    "age_days": age,
                    "is_new_entry": r.get("full_name", "") not in prev_repo_set,
                }
            )

        # --- percentile rank ---
        surge_pcts = percentile_scores(surge_raws)
        newcomer_pcts = percentile_scores(newcomer_raws)
        momentum_pcts = percentile_scores(momentum_raws)

        scored: list[dict] = []
        for i, r in enumerate(enriched):
            s = surge_pcts[i]
            n = newcomer_pcts[i]
            m = momentum_pcts[i]
            composite = round(s * 0.4 + n * 0.3 + m * 0.3, 1)
            signal_type = _determine_signal_type(s, n, m)
            scored.append(
                {
                    **r,
                    "surge_score": s,
                    "newcomer_score": n,
                    "momentum_score": m,
                    "trend_score": composite,
                    "signal_type": signal_type,
                }
            )

        # Sort descending by composite, take top 10
        scored.sort(key=lambda x: x["trend_score"], reverse=True)
        result[cat_name] = scored[:10]

    return {"date": raw_data.get("date", ""), "categories": result}


def run_scoring(date: str | None = None) -> dict:
    """Load raw.json, compute multi-signal scores, save to trending.json."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    raw_path = BASE_DIR / "data" / date / "raw.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Try loading previous day's raw.json for momentum
    prev_data: dict | None = None
    data_root = BASE_DIR / "data"
    if data_root.exists():
        date_dirs = sorted(
            [
                d.name
                for d in data_root.iterdir()
                if d.is_dir() and d.name < date
            ],
            reverse=True,
        )
        if date_dirs:
            prev_raw = data_root / date_dirs[0] / "raw.json"
            if prev_raw.exists():
                try:
                    with open(prev_raw, encoding="utf-8") as f:
                        prev_data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass

    trending = compute_scores(raw_data, prev_data)

    output_path = BASE_DIR / "data" / date / "trending.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(trending, f, ensure_ascii=False, indent=2)

    print(f"Scoring complete → {output_path}")
    return trending


if __name__ == "__main__":
    run_scoring()

"""
Historical activity analysis for AI trend data.

Scans data/YYYY-MM-DD/trending.json files to track repo activity scores
and commit counts over time, then generates activity history reports.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# Sparkline block characters mapped to 8 levels (index 0–7)
_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _spark_char(value: float, min_val: float, max_val: float) -> str:
    """Map a value to a sparkline block character."""
    if max_val == min_val:
        return _SPARK_CHARS[0]
    ratio = (value - min_val) / (max_val - min_val)
    index = min(int(ratio * len(_SPARK_CHARS)), len(_SPARK_CHARS) - 1)
    return _SPARK_CHARS[index]


def _activity_emoji(trend_score: float) -> str:
    """Return an emoji indicator based on activity score."""
    if trend_score >= 7:
        return "🔥"
    if trend_score >= 4:
        return "📈"
    return ""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_all_trending_data() -> list[dict]:
    """Scan data/YYYY-MM-DD/trending.json files and return sorted records.

    Returns:
        List of dicts with keys ``date`` (str) and ``categories`` (dict),
        sorted ascending by date.
    """
    data_root = BASE_DIR / "data"
    records: list[dict] = []

    if not data_root.exists():
        return records

    for date_dir in sorted(data_root.iterdir()):
        if not date_dir.is_dir():
            continue
        # Directory name must look like YYYY-MM-DD
        name = date_dir.name
        try:
            datetime.strptime(name, "%Y-%m-%d")
        except ValueError:
            continue

        trending_path = date_dir / "trending.json"
        if not trending_path.exists():
            continue

        try:
            with open(trending_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            continue

        records.append({"date": name, "categories": categories})

    records.sort(key=lambda r: r["date"])
    return records


# ---------------------------------------------------------------------------
# Per-repo history
# ---------------------------------------------------------------------------


def get_repo_history(repo_name: str) -> list[dict]:
    """Return a repo's metrics across all dates it appeared.

    Args:
        repo_name: The short ``name`` field of the repository (case-insensitive).

    Returns:
        List of dicts with keys ``date``, ``trend_score``, ``stars``,
        ``commits_30d``, sorted ascending by date.
    """
    all_data = load_all_trending_data()
    history: list[dict] = []
    repo_name_lower = repo_name.lower()

    for record in all_data:
        for _cat, repos in record["categories"].items():
            if not isinstance(repos, list):
                continue
            for repo in repos:
                if repo.get("name", "").lower() == repo_name_lower:
                    history.append(
                        {
                            "date": record["date"],
                            "trend_score": repo.get("trend_score", 0.0),
                            "stars": repo.get("stars", 0),
                            "commits_30d": repo.get("recent_commits_30d", 0),
                        }
                    )
                    break  # found in this date's categories; move to next date

    history.sort(key=lambda r: r["date"])
    return history


# ---------------------------------------------------------------------------
# ASCII sparkline
# ---------------------------------------------------------------------------


def generate_activity_chart(repo_name: str) -> str:
    """Return an ASCII sparkline of activity score over time for a repo.

    Uses block characters ▁▂▃▄▅▆▇█ mapped to the observed min/max range.

    Args:
        repo_name: The short ``name`` field of the repository.

    Returns:
        A string of sparkline characters, or an empty string if no data.
    """
    history = get_repo_history(repo_name)
    if not history:
        return ""

    scores = [entry["trend_score"] for entry in history]
    min_score = min(scores)
    max_score = max(scores)

    return "".join(_spark_char(s, min_score, max_score) for s in scores)


def _build_sparkline(scores: list[float], window: int = 30) -> str:
    """Build a sparkline string for the last *window* score values."""
    tail = scores[-window:] if len(scores) > window else scores
    if not tail:
        return ""
    min_s = min(tail)
    max_s = max(tail)
    return "".join(_spark_char(s, min_s, max_s) for s in tail)


# ---------------------------------------------------------------------------
# History report generation
# ---------------------------------------------------------------------------


def _collect_all_repo_scores(
    all_data: list[dict],
) -> dict[str, list[tuple[str, float]]]:
    """Return mapping of repo_name -> [(date, trend_score), ...] sorted by date."""
    repo_scores: dict[str, list[tuple[str, float]]] = {}

    for record in all_data:
        date = record["date"]
        seen_in_date: set[str] = set()
        for _cat, repos in record["categories"].items():
            if not isinstance(repos, list):
                continue
            for repo in repos:
                name = repo.get("name", "")
                if not name or name in seen_in_date:
                    continue
                seen_in_date.add(name)
                repo_scores.setdefault(name, []).append(
                    (date, repo.get("trend_score", 0.0))
                )

    # Ensure each repo's list is sorted by date
    for name in repo_scores:
        repo_scores[name].sort(key=lambda t: t[0])

    return repo_scores


def _collect_all_repo_latest(all_data: list[dict]) -> dict[str, dict]:
    """Return mapping of repo_name -> full repo dict from the most recent date."""
    latest: dict[str, dict] = {}

    for record in all_data:
        for _cat, repos in record["categories"].items():
            if not isinstance(repos, list):
                continue
            for repo in repos:
                name = repo.get("name", "")
                if name:
                    latest[name] = repo  # later records overwrite earlier ones

    return latest


def generate_history_report(date: str = None) -> Path:
    """Generate reports/YYYY-MM-DD-history.md with activity trend sections.

    Sections produced:
    - ## Activity Trends       — repos with biggest activity score changes
    - ## Most Active           — repos whose score increased most in last 7 days
    - ## Slowing Down          — repos whose score decreased most in last 7 days
    - ## Historical Sparklines — sparklines for top 20 repos across all categories

    Args:
        date: ISO date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Path to the generated report file.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    all_data = load_all_trending_data()

    # Filter records up to and including the target date
    all_data = [r for r in all_data if r["date"] <= date]

    report_dir = BASE_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{date}-history.md"

    lines: list[str] = []
    lines.append(f"# AI Trend Activity History — {date}")
    lines.append("")
    lines.append(
        f"> Auto-generated on {date}. Tracks activity scores (30-day commits) "
        "across historical snapshots."
    )
    lines.append("")

    if not all_data:
        lines.append("*No historical data available.*")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"History report generated: {report_path}")
        return report_path

    # Build per-repo score histories
    repo_scores = _collect_all_repo_scores(all_data)
    repo_latest = _collect_all_repo_latest(all_data)

    # Determine the cutoff date 7 days before target
    target_dt = datetime.strptime(date, "%Y-%m-%d")
    cutoff_7d = (target_dt - timedelta(days=7)).strftime("%Y-%m-%d")

    # Compute activity change metrics per repo
    activity: list[dict] = []
    for name, score_series in repo_scores.items():
        if len(score_series) < 1:
            continue

        current_score = score_series[-1][1]

        # Score 7 days ago (most recent snapshot at or before cutoff)
        past_snapshots = [(d, s) for d, s in score_series if d <= cutoff_7d]
        score_7d_ago = past_snapshots[-1][1] if past_snapshots else score_series[0][1]

        change_7d = current_score - score_7d_ago

        # Overall change (first vs last)
        overall_change = current_score - score_series[0][1]

        scores_only = [s for _, s in score_series]

        activity.append(
            {
                "name": name,
                "current_score": current_score,
                "change_7d": change_7d,
                "overall_change": overall_change,
                "scores": scores_only,
                "series": score_series,
            }
        )

    # -----------------------------------------------------------------------
    # ## Activity Trends — biggest absolute change overall
    # -----------------------------------------------------------------------
    lines.append("## Activity Trends")
    lines.append("")
    lines.append(
        "Repositories with the biggest activity score change since first appearance."
    )
    lines.append("")
    lines.append("| Repository | Current Activity | Overall Change | Sparkline |")
    lines.append("|-----------|-----------------|----------------|-----------|")

    biggest_movers = sorted(
        activity, key=lambda x: abs(x["overall_change"]), reverse=True
    )[:20]

    for v in biggest_movers:
        repo = repo_latest.get(v["name"], {})
        score = v["current_score"]
        emoji = _activity_emoji(score)
        activity_cell = f"{emoji} {score:.1f}" if emoji else f"{score:.1f}"
        change = v["overall_change"]
        change_str = f"+{change:.1f}" if change >= 0 else f"{change:.1f}"
        spark = _build_sparkline(v["scores"])
        lines.append(
            f"| [{v['name']}]({repo.get('url', '#')}) "
            f"| {activity_cell} | {change_str} | {spark} |"
        )
    lines.append("")

    # -----------------------------------------------------------------------
    # ## Most Active
    # -----------------------------------------------------------------------
    lines.append("## Most Active")
    lines.append("")
    lines.append("Repositories whose activity score increased most in the last 7 days.")
    lines.append("")
    lines.append("| Repository | Activity | 7d Change | 30-Day Sparkline |")
    lines.append("|-----------|----------|-----------|-----------------|")

    most_active = sorted(
        [v for v in activity if v["change_7d"] > 0],
        key=lambda x: x["change_7d"],
        reverse=True,
    )[:20]

    for v in most_active:
        repo = repo_latest.get(v["name"], {})
        score = v["current_score"]
        emoji = _activity_emoji(score)
        activity_cell = f"{emoji} {score:.1f}" if emoji else f"{score:.1f}"
        change_str = f"+{v['change_7d']:.1f}"
        spark = _build_sparkline(v["scores"], window=30)
        lines.append(
            f"| [{v['name']}]({repo.get('url', '#')}) "
            f"| {activity_cell} | {change_str} | {spark} |"
        )
    lines.append("")

    # -----------------------------------------------------------------------
    # ## Slowing Down
    # -----------------------------------------------------------------------
    lines.append("## Slowing Down")
    lines.append("")
    lines.append("Repositories whose activity score decreased most in the last 7 days.")
    lines.append("")
    lines.append("| Repository | Activity | 7d Change | 30-Day Sparkline |")
    lines.append("|-----------|----------|-----------|-----------------|")

    slowing = sorted(
        [v for v in activity if v["change_7d"] < 0],
        key=lambda x: x["change_7d"],
    )[:20]

    for v in slowing:
        repo = repo_latest.get(v["name"], {})
        score = v["current_score"]
        emoji = _activity_emoji(score)
        activity_cell = f"{emoji} {score:.1f}" if emoji else f"{score:.1f}"
        change_str = f"{v['change_7d']:.1f}"
        spark = _build_sparkline(v["scores"], window=30)
        lines.append(
            f"| [{v['name']}]({repo.get('url', '#')}) "
            f"| {activity_cell} | {change_str} | {spark} |"
        )
    lines.append("")

    # -----------------------------------------------------------------------
    # ## Historical Sparklines — top 20 repos by current activity score
    # -----------------------------------------------------------------------
    lines.append("## Historical Sparklines")
    lines.append("")
    lines.append("Top 20 repositories by current activity score with 30-day sparklines.")
    lines.append("")
    lines.append(
        "| Repository | Activity | 7d Change | 30-Day Sparkline |"
    )
    lines.append("|-----------|----------|-----------|-----------------|")

    top20 = sorted(activity, key=lambda x: x["current_score"], reverse=True)[:20]

    for v in top20:
        repo = repo_latest.get(v["name"], {})
        score = v["current_score"]
        emoji = _activity_emoji(score)
        activity_cell = f"{emoji} {score:.1f}" if emoji else f"{score:.1f}"
        change = v["change_7d"]
        change_str = f"+{change:.1f}" if change >= 0 else f"{change:.1f}"
        spark = _build_sparkline(v["scores"], window=30)
        lines.append(
            f"| [{v['name']}]({repo.get('url', '#')}) "
            f"| {activity_cell} | {change_str} | {spark} |"
        )
    lines.append("")

    # Write report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"History report generated: {report_path}")
    return report_path


if __name__ == "__main__":
    generate_history_report()

"""
Star history tracking — fetch stargazer timeline and generate growth charts.
Uses GitHub API stargazers endpoint with 'application/vnd.github.star+json' accept header
to get timestamps of when stars were given.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
GITHUB_API = "https://api.github.com"


def get_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github.star+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_recent_stars(full_name: str, days: int = 30) -> list[str]:
    """Fetch star dates for the last N days. Returns list of date strings."""
    headers = get_headers()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    all_dates = []
    page = 1
    while page <= 10:  # Cap at 10 pages (1000 stars) to avoid rate limits
        url = f"{GITHUB_API}/repos/{full_name}/stargazers"
        params = {"per_page": 100, "page": page}

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            break

        data = resp.json()
        if not data:
            break

        for item in data:
            starred_at = item.get("starred_at", "")
            if starred_at and starred_at >= since:
                all_dates.append(starred_at[:10])  # YYYY-MM-DD

        # If the oldest star on this page is before our window, stop
        if data[0].get("starred_at", "") < since:
            break

        page += 1

    return all_dates


def stars_per_day(dates: list[str], days: int = 30) -> dict[str, int]:
    """Count stars per day, filling in zeros for missing days."""
    counter = Counter(dates)
    result = {}
    today = datetime.now(timezone.utc).date()
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        result[d] = counter.get(d, 0)
    return result


def generate_sparkline(daily_counts: dict[str, int]) -> str:
    """Generate ASCII sparkline from daily star counts."""
    chars = "▁▂▃▄▅▆▇█"
    values = list(daily_counts.values())
    if not values or max(values) == 0:
        return "▁" * len(values)
    max_val = max(values)
    return "".join(chars[min(int(v / max_val * 7), 7)] for v in values)


def generate_star_history_report(date: str = None, top_n: int = 15) -> Path:
    """Generate star history report for top trending repos."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    trending_path = BASE_DIR / "data" / date / "trending.json"
    if not trending_path.exists():
        print(f"No trending data for {date}")
        return None

    with open(trending_path, "r", encoding="utf-8") as f:
        trending = json.load(f)

    # Collect top repos across all categories
    all_repos = []
    for cat_name, repos in trending["categories"].items():
        for r in repos[:5]:  # Top 5 per category
            all_repos.append({**r, "category": cat_name})
    all_repos.sort(key=lambda x: x.get("trend_score", 0), reverse=True)
    all_repos = all_repos[:top_n]

    lines = [
        f"# Star History — {date}",
        "",
        "30-day star growth for top trending repositories.",
        "",
        "| Repository | Category | Stars | 30d Sparkline | Peak Day |",
        "|-----------|----------|-------|---------------|----------|",
    ]

    for r in all_repos:
        print(f"  Fetching star history for {r['full_name']}...")
        try:
            dates = fetch_recent_stars(r["full_name"], days=30)
            daily = stars_per_day(dates, days=30)
            sparkline = generate_sparkline(daily)

            # Find peak day
            if daily:
                peak_day = max(daily, key=daily.get)
                peak_count = daily[peak_day]
                peak_str = f"{peak_day} (+{peak_count})"
            else:
                peak_str = "N/A"

            lines.append(
                f"| [{r['name']}]({r['url']}) | {r['category']} | "
                f"{r.get('stars', 0):,} | {sparkline} | {peak_str} |"
            )
        except Exception as e:
            lines.append(
                f"| [{r['name']}]({r['url']}) | {r['category']} | "
                f"{r.get('stars', 0):,} | _fetch failed_ | N/A |"
            )

        import time
        time.sleep(0.5)  # Rate limit

    lines.append("")
    lines.append(f"> Generated on {date}. Sparklines show relative daily star activity over 30 days.")

    report_path = BASE_DIR / "reports" / f"{date}-star-history.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Star history report: {report_path}")
    return report_path


if __name__ == "__main__":
    generate_star_history_report()

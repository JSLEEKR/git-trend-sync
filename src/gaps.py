"""
GitHub Issue 스캔을 통해 트렌딩 레포의 미충족 도구/CLI 수요를 분석합니다.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.collect import get_headers

BASE_DIR = Path(__file__).resolve().parent.parent
GITHUB_API = "https://api.github.com"
TOOL_KEYWORDS = ["cli", "tool", "command-line", "command line"]
PLUGIN_KEYWORDS = ["plugin", "extension", "integration"]
PAIN_PATTERNS = ["i wish", "would be nice", "how do i", "is there a way"]
FEATURE_LABELS = ["feature-request", "enhancement"]
STOP_WORDS = {
    "the", "a", "an", "is", "for", "to", "in", "of", "and", "or",
    "it", "this", "that", "with", "from", "need", "want", "would",
    "should", "could", "please", "add", "support",
}


def classify_gap(issue_title: str, labels: list[str]) -> str | None:
    """Classify an issue into a gap type based on title and labels."""
    title_lower = issue_title.lower()

    # Check tool keywords
    for kw in TOOL_KEYWORDS:
        if kw in title_lower:
            return "missing_tool"

    # Check plugin keywords
    for kw in PLUGIN_KEYWORDS:
        if kw in title_lower:
            return "missing_plugin"

    # Check feature labels
    labels_lower = [l.lower() for l in labels]
    for fl in FEATURE_LABELS:
        if fl in labels_lower:
            return "missing_feature"

    # Check pain patterns
    for pattern in PAIN_PATTERNS:
        if pattern in title_lower:
            return "pain_point"

    return None


def extract_keywords(title: str) -> list[str]:
    """Extract meaningful keywords from issue title."""
    words = re.findall(r"[a-zA-Z0-9-]+", title.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) >= 3]


def compute_demand(reactions: int, comments: int) -> float:
    """Compute demand score from reactions and comments."""
    return float(reactions * 2 + comments)


def fetch_repo_issues(full_name: str, headers: dict) -> list[dict]:
    """Fetch relevant open issues from a GitHub repo."""
    url = f"{GITHUB_API}/search/issues"
    q = (
        f"repo:{full_name}+is:issue+is:open+"
        f'(CLI OR tool OR plugin OR "feature request" OR "I wish")'
    )
    params = {
        "q": q,
        "per_page": 10,
        "sort": "reactions",
        "order": "desc",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        results = []
        for item in items:
            results.append({
                "number": item["number"],
                "title": item["title"],
                "url": item["html_url"],
                "reactions": item.get("reactions", {}).get("total_count", 0),
                "comments": item.get("comments", 0),
                "labels": [l["name"] for l in item.get("labels", [])],
                "created_at": item.get("created_at", ""),
            })
        return results
    except (requests.RequestException, KeyError, ValueError):
        return []


def scan_gaps(trending: dict, headers: dict) -> dict:
    """Scan trending repos for gap signals in their issues."""
    date = trending.get("date", "")
    categories = trending.get("categories", {})
    result_categories = {}

    for cat_name, repos in categories.items():
        top_repos = repos[:10]
        all_gaps = []

        for repo in top_repos:
            full_name = repo.get("full_name", "")
            issues = fetch_repo_issues(full_name, headers)

            for issue in issues:
                gap_type = classify_gap(issue["title"], issue["labels"])
                if gap_type is None:
                    continue

                demand = compute_demand(issue["reactions"], issue["comments"])
                keywords = extract_keywords(issue["title"])

                all_gaps.append({
                    "source_repo": full_name,
                    "source_repo_stars": repo.get("stars", 0),
                    "source_repo_surge": repo.get("trend_score", 0.0),
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "issue_url": issue["url"],
                    "reactions": issue["reactions"],
                    "comments": issue["comments"],
                    "demand_score": demand,
                    "gap_type": gap_type,
                    "keywords": keywords,
                    "created_at": issue["created_at"],
                })

        # Sort by demand descending, keep top 10
        all_gaps.sort(key=lambda g: g["demand_score"], reverse=True)
        top_gaps = all_gaps[:10]

        result_categories[cat_name] = {
            "total_signals": len(all_gaps),
            "top_gaps": top_gaps,
        }

    return {
        "date": date,
        "categories": result_categories,
    }


def run_gaps(date: str = None) -> dict:
    """Load trending data, scan for gaps, and save results."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    trending_path = BASE_DIR / "data" / date / "trending.json"
    with open(trending_path, "r", encoding="utf-8") as f:
        trending = json.load(f)

    headers = get_headers()

    gaps = scan_gaps(trending, headers)

    output_dir = BASE_DIR / "data" / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "gaps.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(gaps, f, indent=2, ensure_ascii=False)

    print(f"Gaps saved to {output_path} ({sum(c['total_signals'] for c in gaps['categories'].values())} signals)")
    return gaps

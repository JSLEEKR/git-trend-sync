"""
GitHub Topics에서 카테고리별 상위 레포지토리를 수집합니다.
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "categories.yaml"
GITHUB_API = "https://api.github.com"


def load_categories() -> list[dict]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["categories"]


def get_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_repos(topic: str, limit: int, headers: dict) -> list[dict]:
    """Search trending repositories by topic. Only repos with 1000+ stars."""
    url = f"{GITHUB_API}/search/repositories"
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    q = f"topic:{topic} stars:>1000 pushed:>{since}"
    params = {"q": q, "sort": "stars", "order": "desc", "per_page": limit}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("items", [])


def get_readme(owner: str, repo: str, headers: dict) -> str:
    """Fetch README content for a repository."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return ""
    import base64
    content = resp.json().get("content", "")
    try:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:
        return ""


def get_recent_commits_count(owner: str, repo: str, headers: dict) -> int:
    """Get number of commits in the last 30 days."""
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    params = {"since": since, "per_page": 1}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        return 0
    # Use Link header to get total count
    if "Link" in resp.headers:
        links = resp.headers["Link"]
        if 'rel="last"' in links:
            import re
            match = re.search(r'page=(\d+)>; rel="last"', links)
            if match:
                return int(match.group(1))
    return len(resp.json())


def get_closed_issues_count(owner: str, repo: str, headers: dict) -> int:
    """Get total closed issues count."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return 0
    data = resp.json()
    # open_issues_count includes PRs, so we approximate
    return data.get("open_issues_count", 0)


def extract_repo_data(item: dict, headers: dict) -> dict:
    """Extract relevant data from a GitHub API repo item."""
    owner = item["owner"]["login"]
    name = item["name"]

    print(f"  Fetching details for {owner}/{name}...")

    readme = get_readme(owner, name, headers)
    # Truncate README to first 3000 chars for analysis
    readme_truncated = readme[:3000] if readme else ""

    recent_commits = get_recent_commits_count(owner, name, headers)
    # Brief pause to respect rate limits
    time.sleep(0.5)

    return {
        "name": item["name"],
        "full_name": item["full_name"],
        "url": item["html_url"],
        "description": item.get("description", ""),
        "language": item.get("language", ""),
        "license": (item.get("license") or {}).get("spdx_id", "Unknown"),
        "stars": item.get("stargazers_count", 0),
        "forks": item.get("forks_count", 0),
        "open_issues": item.get("open_issues_count", 0),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
        "pushed_at": item.get("pushed_at", ""),
        "topics": item.get("topics", []),
        "recent_commits_30d": recent_commits,
        "readme_excerpt": readme_truncated,
    }


def collect_all() -> dict:
    """Collect repos for all categories. Returns structured data."""
    categories = load_categories()
    headers = get_headers()
    seen_repos = set()
    result = {}
    today = datetime.now().strftime("%Y-%m-%d")

    for cat in categories:
        cat_name = cat["name"]
        limit = cat.get("limit", 10)
        print(f"\n[{cat_name}] Collecting repos...")

        repos = []
        for topic in cat["topics"]:
            print(f"  Searching topic: {topic}")
            try:
                items = search_repos(topic, limit, headers)
            except requests.exceptions.RequestException as e:
                print(f"  Error searching {topic}: {e}")
                continue

            for item in items:
                if item["full_name"] in seen_repos:
                    continue
                if len(repos) >= limit:
                    break
                seen_repos.add(item["full_name"])
                repo_data = extract_repo_data(item, headers)
                repos.append(repo_data)

            # Rate limit pause between topic searches
            time.sleep(1)

            if len(repos) >= limit:
                break

        result[cat_name] = repos[:limit]
        print(f"  Collected {len(result[cat_name])} repos for {cat_name}")

    # Save raw data
    data_dir = BASE_DIR / "data" / today
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "raw.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "categories": result}, f, ensure_ascii=False, indent=2)

    print(f"\nData saved to {output_path}")

    return {"date": today, "categories": result}


if __name__ == "__main__":
    collect_all()

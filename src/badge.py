"""Generate trending badges for repositories."""

from pathlib import Path
import json
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent


def get_badge_url(repo_name: str, rank: int, category: str) -> str:
    """Generate a shields.io badge URL for a trending repo."""
    color = "brightgreen" if rank <= 3 else "green" if rank <= 5 else "yellow"
    label = f"git--trend--sync"
    message = f"#{rank} in {category.replace(' ', '%20')}"
    return f"https://img.shields.io/badge/{label}-{message}-{color}?style=flat-square"


def get_badge_markdown(repo_name: str, rank: int, category: str) -> str:
    """Generate markdown badge for a trending repo."""
    url = get_badge_url(repo_name, rank, category)
    return f"[![git-trend-sync](  {url})](https://github.com/JSLEEKR/git-trend-sync)"


def generate_badges_file(date: str = None):
    """Generate a badges.md file listing badges for all trending repos."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    trending_path = BASE_DIR / "data" / date / "trending.json"
    if not trending_path.exists():
        print(f"No trending data for {date}")
        return

    with open(trending_path, "r", encoding="utf-8") as f:
        trending = json.load(f)

    lines = [
        f"# Trending Badges — {date}",
        "",
        "Add these badges to your repository's README to show trending status.",
        "",
    ]

    for cat_name, repos in trending["categories"].items():
        lines.append(f"## {cat_name}")
        lines.append("")
        for i, r in enumerate(repos, 1):
            badge_md = get_badge_markdown(r["name"], i, cat_name)
            lines.append(f"**{r['name']}:** `{badge_md}`")
            lines.append("")

    output_path = BASE_DIR / "reports" / f"{date}-badges.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Badges file generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_badges_file()

"""
apply.py — deep integration analysis for a single trending repo.

Given a repo name and a target project directory, generates:
  - data/YYYY-MM-DD/apply_prompt_{repo_name}.md  (filled-in prompt)
  - reports/apply-{repo_name}-YYYY-MM-DD.md       (summary report with run instructions)
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.scan_project import scan_project

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if missing or malformed."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _all_repos(data: dict) -> list[dict]:
    """Flatten all repos from a categories dict."""
    repos = []
    for cat_repos in data.get("categories", {}).values():
        repos.extend(cat_repos)
    return repos


def _match_repo(repos: list[dict], repo_name: str) -> dict | None:
    """Case-insensitive match against 'name' or 'full_name'."""
    needle = repo_name.lower()
    for repo in repos:
        if repo.get("name", "").lower() == needle:
            return repo
        if repo.get("full_name", "").lower() == needle:
            return repo
    return None


def find_repo_in_trending(repo_name: str, date: str) -> dict | None:
    """
    Search data/YYYY-MM-DD/trending.json for a repo by name or full_name
    (case-insensitive).  Returns the matching repo dict, or None.
    """
    path = BASE_DIR / "data" / date / "trending.json"
    data = _load_json(path)
    if data is None:
        return None
    return _match_repo(_all_repos(data), repo_name)


def find_repo_in_raw(repo_name: str, date: str) -> dict | None:
    """
    Fallback: search data/YYYY-MM-DD/raw.json for a repo by name or full_name
    (case-insensitive).  Returns the matching repo dict, or None.
    """
    path = BASE_DIR / "data" / date / "raw.json"
    data = _load_json(path)
    if data is None:
        return None
    return _match_repo(_all_repos(data), repo_name)


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_apply_report(repo: dict, profile: dict, date: str) -> Path:
    """
    Creates two files and returns the path to the report.

    data/YYYY-MM-DD/apply_prompt_{repo_name}.md
        The apply.md prompt template filled in with repo + project data.

    reports/apply-{repo_name}-YYYY-MM-DD.md
        A human-readable summary with repository info, project info, and
        instructions for running the full Claude Code analysis.
    """
    # ---- Safe repo name for file paths --------------------------------
    repo_name = repo.get("name", "unknown")
    safe_name = repo_name.lower().replace("/", "-").replace(" ", "-")

    # ---- Load the prompt template -------------------------------------
    template_path = BASE_DIR / "config" / "prompts" / "apply.md"
    template = template_path.read_text(encoding="utf-8")

    # ---- Build substitution strings -----------------------------------
    # Repo data: strip readme_excerpt to keep prompt manageable
    repo_clean = {k: v for k, v in repo.items() if k != "readme_excerpt"}
    repo_data_str = json.dumps(repo_clean, ensure_ascii=False, indent=2)

    # Project profile
    profile_str = json.dumps(profile, ensure_ascii=False, indent=2)

    # ---- Fill the template --------------------------------------------
    prompt_content = (
        template
        .replace("{{repo_data}}", repo_data_str)
        .replace("{{project_profile}}", profile_str)
    )

    # ---- Write prompt file --------------------------------------------
    data_dir = BASE_DIR / "data" / date
    data_dir.mkdir(parents=True, exist_ok=True)

    prompt_filename = f"apply_prompt_{safe_name}.md"
    prompt_path = data_dir / prompt_filename
    prompt_path.write_text(prompt_content, encoding="utf-8")

    # ---- Build the report ---------------------------------------------
    stack = profile.get("detected_stack") or []
    frameworks = profile.get("detected_frameworks") or []
    interests = profile.get("declared_interests") or []

    stack_str = ", ".join(stack) if stack else "unknown"
    frameworks_str = ", ".join(frameworks) if frameworks else "none detected"
    interests_str = ", ".join(interests) if interests else "none declared"

    stars = repo.get("stars", "N/A")
    trend_score = repo.get("trend_score")
    trend_score_str = str(trend_score) if trend_score is not None else "N/A"

    # Relative prompt path for the CLI instruction (forward slashes)
    prompt_rel = f"data/{date}/{prompt_filename}"

    report_lines = [
        f"# Apply Report: {repo_name} — {date}",
        "",
        "## Repository",
        "",
        f"- **Name:** {repo.get('full_name', repo_name)}",
        f"- **URL:** {repo.get('url', 'N/A')}",
        f"- **Description:** {repo.get('description', 'N/A')}",
        f"- **Language:** {repo.get('language', 'N/A')}",
        f"- **Stars:** {stars:,}" if isinstance(stars, int) else f"- **Stars:** {stars}",
        f"- **Trend Score:** {trend_score_str}",
        "",
        "## Target Project",
        "",
        f"- **Name:** {profile.get('name', 'unknown')}",
        f"- **Stack:** {stack_str}",
        f"- **Frameworks:** {frameworks_str}",
        f"- **Interests:** {interests_str}",
        "",
        "## How to Run the Analysis",
        "",
        "Run the following command to get a detailed integration analysis from Claude Code:",
        "",
        "```bash",
        f'claude -p "$(cat {prompt_rel})"',
        "```",
        "",
        "> The prompt has been saved to:",
        f"> `{prompt_path}`",
        "",
    ]

    report_content = "\n".join(report_lines)

    # ---- Write report file --------------------------------------------
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / f"apply-{safe_name}-{date}.md"
    report_path.write_text(report_content, encoding="utf-8")

    return report_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a deep integration analysis report for a trending repo.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository name or full_name to analyse (e.g. 'langchain' or 'langchain-ai/langchain').",
    )
    parser.add_argument(
        "--project",
        default=".",
        help="Path to the target project directory (default: current directory).",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date of trending data to use, YYYY-MM-DD (default: today).",
    )
    args = parser.parse_args()

    # ---- Find repo ----------------------------------------------------
    repo = find_repo_in_trending(args.repo, args.date)
    source = "trending.json"

    if repo is None:
        repo = find_repo_in_raw(args.repo, args.date)
        source = "raw.json"

    if repo is None:
        print(f"Repository '{args.repo}' not found in data for {args.date}.")
        print()

        # Show available repos as a helpful hint
        raw_path = BASE_DIR / "data" / args.date / "raw.json"
        data = _load_json(raw_path)
        if data:
            print("Available repositories:")
            for cat_name, cat_repos in data.get("categories", {}).items():
                print(f"\n  [{cat_name}]")
                for r in cat_repos:
                    print(f"    {r.get('full_name', r.get('name', '?'))}")
        else:
            print(f"No data found at data/{args.date}/raw.json")
        return

    print(f"Found '{repo.get('full_name', repo.get('name'))}' in {source}.")

    # ---- Scan project ------------------------------------------------
    profile = scan_project(args.project)
    print(f"Scanned project: {profile.get('name')} ({args.project})")

    # ---- Generate report ---------------------------------------------
    report_path = generate_apply_report(repo, profile, args.date)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()

"""
AI Agent Trend Report v2 — Main Orchestrator

Pipeline:
1. Collect trending repos from GitHub Topics (stars>1000, active in 7d)
2. Compute velocity-based trend scores
3. Qualitative analysis (optional)
4. Generate trend report
5. Project-specific recommendations (optional)

Usage:
    python run.py                           # Full pipeline
    python run.py --skip-analysis           # Skip qualitative analysis
    python run.py --no-recommend            # Skip recommendations
    python run.py --project /path/to/proj   # Recommendations for specific project
    python run.py --report-only             # Regenerate from existing data
    python run.py --no-push                 # Skip git push
"""

import argparse
import io
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def run_step(name: str, func, *args):
    """Run a pipeline step with status logging."""
    print(f"\n{'='*50}")
    print(f"  Step: {name}")
    print(f"{'='*50}")
    try:
        result = func(*args)
        print(f"  ✓ {name} complete")
        return result
    except Exception as e:
        print(f"  ✗ {name} failed: {e}")
        raise


def step_collect():
    """Step 1: Collect repos from GitHub Topics."""
    from src.collect import collect_all
    return collect_all()


def step_metrics(date: str):
    """Step 2: Compute quantitative metrics."""
    from src.metrics import run_metrics
    return run_metrics(date)


def step_analyze(date: str):
    """Step 3: Run Claude Code analysis."""
    from src.analyze import run_analysis
    return run_analysis(date)


def step_report(date: str):
    """Step 4: Generate markdown reports."""
    from src.report import generate_reports
    return generate_reports(date)


def step_trending(date: str):
    """Step 2b: Compute trend scores."""
    from src.trending import run_trending
    return run_trending(date)


def step_recommend(date: str, project_path: str):
    """Step 5: Generate project recommendations."""
    from src.recommend import run_recommendations
    return run_recommendations(date, project_path)


def step_publish(date: str):
    """Step 6: Git commit & push."""
    script = BASE_DIR / "src" / "publish.sh"
    result = subprocess.run(
        ["bash", str(script), date],
        cwd=str(BASE_DIR),
        capture_output=False,
    )
    if result.returncode != 0:
        print("  Warning: Git publish may have failed")


def main():
    parser = argparse.ArgumentParser(description="AI Agent Trend Report Generator")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date for the report (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip Claude Code analysis step",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only generate report from existing data",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip git commit & push step",
    )
    parser.add_argument(
        "--project",
        default=".",
        help="Path to your project for recommendations",
    )
    parser.add_argument(
        "--no-recommend",
        action="store_true",
        help="Skip project recommendation step",
    )
    args = parser.parse_args()

    print(f"AI Agent Trend Report — {args.date}")
    print(f"Base directory: {BASE_DIR}")

    if args.report_only:
        run_step("Generate Reports", step_report, args.date)
    else:
        # Full pipeline
        raw_data = run_step("Collect Repositories", step_collect)
        date = raw_data["date"]

        run_step("Compute Trend Scores", step_trending, date)

        run_step("Compute Metrics", step_metrics, date)

        if not args.skip_analysis:
            run_step("Claude Code Analysis", step_analyze, date)
        else:
            print("\n  Skipping Claude Code analysis (--skip-analysis)")

        run_step("Generate Reports", step_report, date)

        if not args.no_recommend:
            run_step("Project Recommendations", step_recommend, date, args.project)
        else:
            print("\n  Skipping recommendations (--no-recommend)")

    # Git commit & push
    if not args.no_push:
        run_step("Git Publish", step_publish, args.date)
    else:
        print("\n  Skipping git publish (--no-push)")

    print(f"\n{'='*50}")
    print(f"  Pipeline complete!")
    print(f"  Report: reports/{args.date}.md")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

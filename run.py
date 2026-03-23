"""
AI Agent Trend Report — 메인 오케스트레이터

전체 파이프라인을 순서대로 실행합니다:
1. GitHub Topics에서 카테고리별 레포 수집
2. 정량 메트릭 계산
3. Claude Code CLI로 정성적 분석
4. 한국어/영어 마크다운 리포트 생성

Usage:
    python run.py              # 전체 파이프라인
    python run.py --skip-analysis  # Claude Code 분석 건너뛰기 (메트릭만)
    python run.py --date 2026-03-23  # 특정 날짜 데이터로 리포트 재생성
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


def step_publish(date: str):
    """Step 5: Git commit & push."""
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
    args = parser.parse_args()

    print(f"AI Agent Trend Report — {args.date}")
    print(f"Base directory: {BASE_DIR}")

    if args.report_only:
        run_step("Generate Reports", step_report, args.date)
    else:
        # Full pipeline
        raw_data = run_step("Collect Repositories", step_collect)
        date = raw_data["date"]

        run_step("Compute Metrics", step_metrics, date)

        if not args.skip_analysis:
            run_step("Claude Code Analysis", step_analyze, date)
        else:
            print("\n  Skipping Claude Code analysis (--skip-analysis)")

        run_step("Generate Reports", step_report, date)

    # Git commit & push
    if not args.no_push:
        run_step("Git Publish", step_publish, args.date)
    else:
        print("\n  Skipping git publish (--no-push)")

    print(f"\n{'='*50}")
    print(f"  Pipeline complete!")
    print(f"  Reports: reports/ko/{args.date}.md, reports/en/{args.date}.md")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

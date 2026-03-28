"""Tests for src/readme_update.py"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.readme_update import (
    _format_stars,
    _get_top_repos,
    _build_trend_section,
    update_readme,
)


class TestFormatStars:
    def test_thousands(self):
        assert _format_stars(50000) == "50,000"

    def test_zero(self):
        assert _format_stars(0) == "0"


class TestGetTopRepos:
    def test_basic_sorting(self):
        categories = {
            "Cat1": [
                {"name": "r1", "full_name": "o/r1", "trend_score": 10},
                {"name": "r2", "full_name": "o/r2", "trend_score": 5},
            ],
            "Cat2": [
                {"name": "r3", "full_name": "o/r3", "trend_score": 8},
            ],
        }
        result = _get_top_repos(categories, top_n=2)
        assert len(result) == 2
        assert result[0]["trend_score"] >= result[1]["trend_score"]

    def test_deduplication(self):
        categories = {
            "Cat1": [{"name": "r1", "full_name": "o/r1", "trend_score": 10}],
            "Cat2": [{"name": "r1", "full_name": "o/r1", "trend_score": 8}],
        }
        result = _get_top_repos(categories, top_n=10)
        assert len(result) == 1
        assert result[0]["trend_score"] == 10  # keeps highest


class TestBuildTrendSection:
    def test_has_signal_and_detail_columns(self):
        repos = [
            {
                "name": "r1",
                "full_name": "o/r1",
                "url": "https://github.com/o/r1",
                "_category": "AI",
                "trend_score": 9.0,
                "signal_type": "surge",
                "surge_ratio": 2.5,
                "stars_per_day_avg": 55.0,
                "age_days": 900,
                "recent_commits_7d": 60,
            },
        ]
        section = _build_trend_section("2025-03-28", repos)
        assert "Signal" in section
        assert "Detail" in section
        assert "surge" in section
        assert "x2.5 this week" in section

    def test_has_score_column(self):
        repos = [
            {
                "name": "r1",
                "full_name": "o/r1",
                "url": "https://github.com/o/r1",
                "_category": "AI",
                "trend_score": 9.0,
                "signal_type": "momentum",
                "surge_ratio": 1.0,
                "stars_per_day_avg": 10.0,
                "age_days": 300,
                "recent_commits_7d": 42,
            },
        ]
        section = _build_trend_section("2025-03-28", repos)
        assert "Score" in section
        assert "9.0" in section
        assert "42 commits/7d" in section

    def test_newcomer_detail(self):
        repos = [
            {
                "name": "new-repo",
                "full_name": "o/new-repo",
                "url": "https://github.com/o/new-repo",
                "_category": "ML",
                "trend_score": 7.0,
                "signal_type": "newcomer",
                "surge_ratio": 1.0,
                "stars_per_day_avg": 25.3,
                "age_days": 30,
                "recent_commits_7d": 20,
            },
        ]
        section = _build_trend_section("2025-03-28", repos)
        assert "30d, 25.3/day" in section

    def test_header_no_fire_emoji(self):
        section = _build_trend_section("2025-03-28", [])
        assert "### Today's Top Trending" in section
        assert "🔥" not in section


class TestUpdateReadme:
    def test_updates_between_markers(self, tmp_path):
        data_dir = tmp_path / "data" / "2025-03-28"
        data_dir.mkdir(parents=True)
        trending = {
            "categories": {
                "AI": [
                    {
                        "name": "r1",
                        "full_name": "o/r1",
                        "url": "https://github.com/o/r1",
                        "trend_score": 9.0,
                        "stars": 50000,
                        "signal_type": "surge",
                        "surge_ratio": 2.0,
                        "stars_per_day_avg": 55.0,
                        "age_days": 900,
                        "recent_commits_7d": 60,
                    }
                ],
            }
        }
        (data_dir / "trending.json").write_text(json.dumps(trending))

        readme = tmp_path / "README.md"
        readme.write_text(
            "# My Project\n\n<!-- TREND-START -->\nold content\n<!-- TREND-END -->\n\nFooter\n"
        )

        with patch("src.readme_update.BASE_DIR", tmp_path):
            update_readme("2025-03-28")
            content = readme.read_text(encoding="utf-8")
            assert "Signal" in content
            assert "old content" not in content
            assert "Footer" in content

    def test_handles_no_markers(self, tmp_path):
        data_dir = tmp_path / "data" / "2025-03-28"
        data_dir.mkdir(parents=True)
        trending = {
            "categories": {
                "A": [
                    {
                        "name": "r",
                        "full_name": "o/r",
                        "url": "#",
                        "trend_score": 5,
                        "stars": 100,
                        "signal_type": "surge",
                        "surge_ratio": 1.0,
                        "stars_per_day_avg": 10.0,
                        "age_days": 100,
                        "recent_commits_7d": 10,
                    }
                ]
            }
        }
        (data_dir / "trending.json").write_text(json.dumps(trending))

        readme = tmp_path / "README.md"
        readme.write_text("# No markers here\n")

        with patch("src.readme_update.BASE_DIR", tmp_path):
            update_readme("2025-03-28")
            content = readme.read_text(encoding="utf-8")
            assert content == "# No markers here\n"

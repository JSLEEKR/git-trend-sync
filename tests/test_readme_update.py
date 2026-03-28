"""Tests for src/readme_update.py"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.readme_update import (
    _activity_emoji,
    _format_stars,
    _get_top_repos,
    _build_trend_section,
    update_readme,
)


class TestActivityEmojiReadme:
    def test_fire(self):
        result = _activity_emoji(9.5)
        assert "🔥" in result

    def test_lightning(self):
        result = _activity_emoji(7.5)
        assert "⚡" in result

    def test_chart(self):
        result = _activity_emoji(5.5)
        assert "📈" in result

    def test_arrow(self):
        result = _activity_emoji(3.0)
        assert "➡️" in result


class TestFormatStars:
    def test_thousands(self):
        assert _format_stars(50000) == "50,000"

    def test_zero(self):
        assert _format_stars(0) == "0"

    def test_small(self):
        assert _format_stars(42) == "42"


class TestGetTopRepos:
    def test_basic(self):
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

    def test_empty(self):
        result = _get_top_repos({}, top_n=10)
        assert result == []


class TestBuildTrendSection:
    def test_contains_table(self):
        repos = [
            {"name": "r1", "full_name": "o/r1", "url": "https://github.com/o/r1",
             "_category": "AI", "trend_score": 9.0, "stars": 50000, "recent_commits_30d": 100},
        ]
        section = _build_trend_section("2025-03-28", repos)
        assert "Today's Top Trending" in section
        assert "r1" in section
        assert "50,000" in section


class TestUpdateReadme:
    def test_updates_content(self, tmp_path):
        # Setup trending data
        data_dir = tmp_path / "data" / "2025-03-28"
        data_dir.mkdir(parents=True)
        trending = {
            "categories": {
                "AI": [{"name": "r1", "full_name": "o/r1", "url": "https://github.com/o/r1",
                         "trend_score": 9.0, "stars": 50000, "recent_commits_30d": 100}],
            }
        }
        (data_dir / "trending.json").write_text(json.dumps(trending))

        # Setup README with markers
        readme = tmp_path / "README.md"
        readme.write_text(
            "# My Project\n\n<!-- TREND-START -->\nold content\n<!-- TREND-END -->\n\nFooter\n"
        )

        with patch("src.readme_update.BASE_DIR", tmp_path):
            result = update_readme("2025-03-28")
            content = readme.read_text(encoding="utf-8")
            assert "r1" in content
            assert "old content" not in content
            assert "Footer" in content

    def test_missing_markers(self, tmp_path):
        data_dir = tmp_path / "data" / "2025-03-28"
        data_dir.mkdir(parents=True)
        (data_dir / "trending.json").write_text(json.dumps({"categories": {"A": [{"name": "r", "full_name": "o/r", "url": "#", "trend_score": 5, "stars": 100, "recent_commits_30d": 10}]}}))

        readme = tmp_path / "README.md"
        readme.write_text("# No markers here\n")

        with patch("src.readme_update.BASE_DIR", tmp_path):
            update_readme("2025-03-28")
            content = readme.read_text(encoding="utf-8")
            assert content == "# No markers here\n"

    def test_missing_trending_data(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n")

        with patch("src.readme_update.BASE_DIR", tmp_path):
            result = update_readme("2025-03-28")
            assert result is not None

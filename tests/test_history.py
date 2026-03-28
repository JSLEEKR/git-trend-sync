"""Tests for src/history.py"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.history import (
    _spark_char,
    _activity_emoji,
    load_all_trending_data,
    get_repo_history,
    generate_activity_chart,
    _build_sparkline,
)


class TestSparkChar:
    def test_min_value(self):
        assert _spark_char(0, 0, 10) == "▁"

    def test_max_value(self):
        assert _spark_char(10, 0, 10) == "█"

    def test_equal_min_max(self):
        assert _spark_char(5, 5, 5) == "▁"

    def test_mid_value(self):
        char = _spark_char(5, 0, 10)
        assert char in "▁▂▃▄▅▆▇█"


class TestActivityEmojiHistory:
    def test_high(self):
        assert _activity_emoji(8.0) == "🔥"

    def test_medium(self):
        assert _activity_emoji(5.0) == "📈"

    def test_low(self):
        assert _activity_emoji(2.0) == ""


class TestBuildSparkline:
    def test_basic(self):
        result = _build_sparkline([0, 5, 10])
        assert len(result) == 3
        assert result[0] == "▁"
        assert result[2] == "█"

    def test_empty(self):
        assert _build_sparkline([]) == ""

    def test_window(self):
        scores = list(range(50))
        result = _build_sparkline(scores, window=10)
        assert len(result) == 10

    def test_all_same(self):
        result = _build_sparkline([5, 5, 5])
        assert len(result) == 3


class TestLoadAllTrendingData:
    def test_loads_data(self, tmp_path):
        date_dir = tmp_path / "data" / "2025-03-28"
        date_dir.mkdir(parents=True)
        trending = {"categories": {"Cat": [{"name": "r1", "trend_score": 5.0}]}}
        (date_dir / "trending.json").write_text(json.dumps(trending))

        with patch("src.history.BASE_DIR", tmp_path):
            records = load_all_trending_data()
        assert len(records) == 1
        assert records[0]["date"] == "2025-03-28"

    def test_skips_non_date_dirs(self, tmp_path):
        (tmp_path / "data" / "not-a-date").mkdir(parents=True)
        (tmp_path / "data" / "2025-03-28").mkdir(parents=True)
        trending = {"categories": {}}
        (tmp_path / "data" / "2025-03-28" / "trending.json").write_text(json.dumps(trending))

        with patch("src.history.BASE_DIR", tmp_path):
            records = load_all_trending_data()
        assert len(records) == 1

    def test_no_data_dir(self, tmp_path):
        with patch("src.history.BASE_DIR", tmp_path):
            records = load_all_trending_data()
        assert records == []

    def test_skips_malformed_json(self, tmp_path):
        date_dir = tmp_path / "data" / "2025-03-28"
        date_dir.mkdir(parents=True)
        (date_dir / "trending.json").write_text("not json")

        with patch("src.history.BASE_DIR", tmp_path):
            records = load_all_trending_data()
        assert records == []


class TestGetRepoHistory:
    def test_finds_repo(self, tmp_path):
        for d in ["2025-03-27", "2025-03-28"]:
            date_dir = tmp_path / "data" / d
            date_dir.mkdir(parents=True)
            trending = {
                "categories": {"Cat": [{"name": "langchain", "trend_score": 5.0, "stars": 50000, "recent_commits_30d": 100}]}
            }
            (date_dir / "trending.json").write_text(json.dumps(trending))

        with patch("src.history.BASE_DIR", tmp_path):
            history = get_repo_history("langchain")
        assert len(history) == 2
        assert history[0]["date"] < history[1]["date"]

    def test_repo_not_found(self, tmp_path):
        date_dir = tmp_path / "data" / "2025-03-28"
        date_dir.mkdir(parents=True)
        (date_dir / "trending.json").write_text(json.dumps({"categories": {"Cat": [{"name": "other"}]}}))

        with patch("src.history.BASE_DIR", tmp_path):
            history = get_repo_history("langchain")
        assert history == []


class TestGenerateActivityChart:
    def test_generates_chart(self, tmp_path):
        date_dir = tmp_path / "data" / "2025-03-28"
        date_dir.mkdir(parents=True)
        trending = {"categories": {"Cat": [{"name": "repo1", "trend_score": 8.0, "stars": 1000, "recent_commits_30d": 50}]}}
        (date_dir / "trending.json").write_text(json.dumps(trending))

        with patch("src.history.BASE_DIR", tmp_path):
            chart = generate_activity_chart("repo1")
        assert len(chart) == 1

    def test_no_data(self, tmp_path):
        with patch("src.history.BASE_DIR", tmp_path):
            chart = generate_activity_chart("nonexistent")
        assert chart == ""

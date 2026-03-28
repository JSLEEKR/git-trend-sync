"""Tests for src/trending.py"""

import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

import pytest

from src.trending import days_since, compute_activity_scores


class TestDaysSince:
    def test_recent_date(self):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        assert days_since(yesterday) == 1

    def test_z_suffix(self):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert days_since(yesterday) == 1

    def test_empty_string(self):
        assert days_since("") == 9999

    def test_none(self):
        assert days_since(None) == 9999

    def test_invalid_format(self):
        assert days_since("not-a-date") == 9999

    def test_today(self):
        today = datetime.now(timezone.utc).isoformat()
        assert days_since(today) == 0


class TestComputeActivityScores:
    def test_basic_scoring(self, sample_raw_data):
        with patch("src.trending.BASE_DIR") as mock_base:
            mock_base.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
            result = compute_activity_scores(sample_raw_data)

        assert "date" in result
        assert "categories" in result
        repos = result["categories"]["AI Agent Framework"]
        assert len(repos) == 3
        # Higher commits should have higher trend_score
        assert repos[0]["trend_score"] >= repos[1]["trend_score"]

    def test_empty_category(self):
        raw = {"date": "2025-03-28", "categories": {"Empty": []}}
        with patch("src.trending.BASE_DIR") as mock_base:
            mock_base.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
            result = compute_activity_scores(raw)
        assert result["categories"]["Empty"] == []

    def test_single_repo_category(self, sample_repo):
        raw = {"date": "2025-03-28", "categories": {"Solo": [sample_repo]}}
        with patch("src.trending.BASE_DIR") as mock_base:
            mock_base.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
            result = compute_activity_scores(raw)
        repos = result["categories"]["Solo"]
        assert len(repos) == 1
        # Single repo with commits > 0 gets score 10.0
        assert repos[0]["trend_score"] == 10.0

    def test_all_zero_commits(self):
        repos = [
            {"name": "a", "full_name": "o/a", "recent_commits_30d": 0, "stars": 100, "created_at": "2024-01-01T00:00:00Z"},
            {"name": "b", "full_name": "o/b", "recent_commits_30d": 0, "stars": 200, "created_at": "2024-01-01T00:00:00Z"},
        ]
        raw = {"date": "2025-03-28", "categories": {"ZeroCommits": repos}}
        with patch("src.trending.BASE_DIR") as mock_base:
            mock_base.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
            result = compute_activity_scores(raw)
        for r in result["categories"]["ZeroCommits"]:
            assert r["trend_score"] == 0.0

    def test_top10_limit(self, sample_repo):
        repos = []
        for i in range(15):
            r = {**sample_repo, "name": f"repo-{i}", "full_name": f"o/repo-{i}", "recent_commits_30d": i * 10}
            repos.append(r)
        raw = {"date": "2025-03-28", "categories": {"Big": repos}}
        with patch("src.trending.BASE_DIR") as mock_base:
            mock_base.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
            result = compute_activity_scores(raw)
        assert len(result["categories"]["Big"]) == 10

    def test_is_new_entry_all_new(self, sample_raw_data):
        """When no previous data exists, all repos should be new entries."""
        with patch("src.trending.BASE_DIR") as mock_base:
            mock_base.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
            result = compute_activity_scores(sample_raw_data)
        for r in result["categories"]["AI Agent Framework"]:
            assert r["is_new_entry"] is True

    def test_stars_per_day_avg(self, sample_repo):
        raw = {"date": "2025-03-28", "categories": {"Test": [sample_repo]}}
        with patch("src.trending.BASE_DIR") as mock_base:
            mock_base.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
            result = compute_activity_scores(raw)
        repo = result["categories"]["Test"][0]
        assert "stars_per_day_avg" in repo
        assert repo["stars_per_day_avg"] > 0

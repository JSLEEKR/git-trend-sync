"""Tests for src/metrics.py"""

import pytest

from src.metrics import normalize, days_since, compute_metrics


class TestNormalize:
    def test_basic_normalization(self):
        result = normalize([0, 5, 10])
        assert result == [0.0, 5.0, 10.0]

    def test_all_same_values(self):
        result = normalize([5, 5, 5])
        assert result == [5.0, 5.0, 5.0]

    def test_empty_list(self):
        result = normalize([])
        assert result == []

    def test_single_value(self):
        result = normalize([42])
        assert result == [5.0]

    def test_negative_values(self):
        result = normalize([-10, 0, 10])
        assert result[0] == 0.0
        assert result[2] == 10.0

    def test_float_precision(self):
        result = normalize([0, 3, 10])
        assert result[1] == 3.0


class TestDaysSinceMetrics:
    def test_empty_returns_9999(self):
        assert days_since("") == 9999

    def test_none_returns_9999(self):
        assert days_since(None) == 9999

    def test_invalid_date(self):
        assert days_since("not-a-date") == 9999


class TestComputeMetrics:
    def test_basic_metrics(self, sample_raw_data):
        result = compute_metrics(sample_raw_data)
        assert "date" in result
        assert "categories" in result
        repos = result["categories"]["AI Agent Framework"]
        assert len(repos) == 2
        for r in repos:
            assert "scores" in r
            scores = r["scores"]
            for key in ["popularity", "activity", "community_health", "growth", "maturity", "overall"]:
                assert key in scores
                assert 0 <= scores[key] <= 10

    def test_empty_category(self):
        raw = {"date": "2025-03-28", "categories": {"Empty": []}}
        result = compute_metrics(raw)
        assert result["categories"]["Empty"] == []

    def test_sorted_by_overall(self, sample_raw_data):
        result = compute_metrics(sample_raw_data)
        repos = result["categories"]["AI Agent Framework"]
        if len(repos) >= 2:
            assert repos[0]["scores"]["overall"] >= repos[1]["scores"]["overall"]

    def test_output_fields(self, sample_raw_data):
        result = compute_metrics(sample_raw_data)
        repo = result["categories"]["AI Agent Framework"][0]
        assert "name" in repo
        assert "full_name" in repo
        assert "url" in repo
        assert "raw_metrics" in repo
        assert "stars" in repo["raw_metrics"]

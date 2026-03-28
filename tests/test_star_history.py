"""Tests for src/star_history.py"""

import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from src.star_history import (
    get_headers,
    stars_per_day,
    generate_sparkline,
)


class TestGetHeadersStarHistory:
    def test_with_token(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}):
            headers = get_headers()
            assert headers["Authorization"] == "Bearer ghp_test"
            assert "star+json" in headers["Accept"]

    def test_without_token(self):
        with patch.dict(os.environ, {}, clear=True):
            headers = get_headers()
            assert "Authorization" not in headers


class TestStarsPerDay:
    def test_basic_counting(self):
        today = datetime.now(timezone.utc).date()
        dates = [today.isoformat(), today.isoformat(), (today - timedelta(days=1)).isoformat()]
        result = stars_per_day(dates, days=3)
        assert len(result) == 3
        assert result[today.isoformat()] == 2

    def test_empty_dates(self):
        result = stars_per_day([], days=5)
        assert len(result) == 5
        assert all(v == 0 for v in result.values())

    def test_fills_zeros(self):
        result = stars_per_day([], days=30)
        assert len(result) == 30
        assert sum(result.values()) == 0


class TestGenerateSparkline:
    def test_basic_sparkline(self):
        daily = {"2025-03-26": 0, "2025-03-27": 5, "2025-03-28": 10}
        result = generate_sparkline(daily)
        assert len(result) == 3
        assert result[0] == "▁"
        assert result[2] == "█"

    def test_all_zeros(self):
        daily = {"2025-03-26": 0, "2025-03-27": 0, "2025-03-28": 0}
        result = generate_sparkline(daily)
        assert result == "▁▁▁"

    def test_empty_dict(self):
        result = generate_sparkline({})
        assert result == ""

    def test_single_day(self):
        daily = {"2025-03-28": 5}
        result = generate_sparkline(daily)
        assert len(result) == 1

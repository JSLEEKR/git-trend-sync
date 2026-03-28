"""Tests for src/scoring.py — multi-signal scoring engine."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.scoring import (
    compute_surge_ratio,
    compute_newcomer_raw,
    compute_momentum_raw,
    percentile_scores,
    compute_scores,
    run_scoring,
    days_since,
    _determine_signal_type,
)


# ===================================================================
# Signal 1: Surge
# ===================================================================


class TestComputeSurgeRatio:
    """Tests for compute_surge_ratio."""

    def test_spike(self):
        """7d commits much higher than weekly average => high ratio."""
        ratio = compute_surge_ratio(100, 130)
        # avg_weekly_rest = (130-100)/3 = 10, ratio = 100/10 = 10.0
        assert ratio == 10.0

    def test_steady(self):
        """Commits spread evenly across 30 days => ratio ~1."""
        # 30d=120, 7d=30 => rest=90/3=30, ratio=30/30=1.0
        ratio = compute_surge_ratio(30, 120)
        assert ratio == 1.0

    def test_slowing(self):
        """Fewer 7d commits than weekly baseline => ratio < 1."""
        # 30d=120, 7d=10 => rest=110/3≈36.67, ratio=10/36.67≈0.27
        ratio = compute_surge_ratio(10, 120)
        assert ratio < 1.0

    def test_zero_rest(self):
        """All commits in 7d (rest=0) => denominator clamped to 1."""
        ratio = compute_surge_ratio(50, 50)
        # avg_weekly_rest = 0/3 = 0 => max(0,1)=1, ratio=50
        assert ratio == 50.0

    def test_zero_commits(self):
        """No commits at all => 0.0."""
        assert compute_surge_ratio(0, 0) == 0.0

    def test_7d_greater_than_30d(self):
        """Edge: 7d > 30d (data anomaly) => negative rest, clamp to 1."""
        ratio = compute_surge_ratio(50, 30)
        # rest = (30-50)/3 = -6.67, max(-6.67, 1) = 1, ratio = 50/1 = 50
        assert ratio == 50.0

    def test_small_numbers(self):
        """Small but nonzero commits."""
        ratio = compute_surge_ratio(1, 4)
        # rest = (4-1)/3 = 1, ratio = 1/1 = 1.0
        assert ratio == 1.0

    def test_large_numbers(self):
        """Large commit counts still work."""
        ratio = compute_surge_ratio(10000, 13000)
        # rest = 3000/3 = 1000, ratio = 10000/1000 = 10
        assert ratio == 10.0

    def test_only_rest_commits(self):
        """0 commits in 7d but some in 30d."""
        ratio = compute_surge_ratio(0, 90)
        # rest = 90/3 = 30, ratio = 0/30 = 0
        assert ratio == 0.0


# ===================================================================
# Signal 2: Newcomer
# ===================================================================


class TestComputeNewcomerRaw:
    """Tests for compute_newcomer_raw."""

    def test_young_popular(self):
        """Young repo with many stars => high score."""
        score = compute_newcomer_raw(3000, 30)
        # stars_per_day = 100, freshness = 150/180 = 0.833, score ≈ 83.3
        assert score > 50

    def test_old_repo(self):
        """Repo >= 180 days => 0."""
        assert compute_newcomer_raw(50000, 365) == 0.0

    def test_exactly_180(self):
        """Boundary: exactly 180 days => 0."""
        assert compute_newcomer_raw(10000, 180) == 0.0

    def test_brand_new(self):
        """1 day old repo."""
        score = compute_newcomer_raw(100, 1)
        # stars_per_day = 100, freshness = 179/180 ≈ 0.994, score ≈ 99.4
        assert score > 90

    def test_zero_age(self):
        """0 days old => age clamped to 1."""
        score = compute_newcomer_raw(100, 0)
        # stars_per_day = 100/1 = 100, freshness = 180/180 = 1.0, score = 100.0
        assert score == 100.0

    def test_zero_stars(self):
        """No stars => 0."""
        assert compute_newcomer_raw(0, 30) == 0.0

    def test_179_days(self):
        """Just under 180 => small nonzero."""
        score = compute_newcomer_raw(1000, 179)
        # stars_per_day ≈ 5.59, freshness = 1/180 ≈ 0.0056, score ≈ 0.0
        assert score >= 0.0

    def test_returns_float(self):
        score = compute_newcomer_raw(500, 50)
        assert isinstance(score, float)


# ===================================================================
# Signal 3: Momentum
# ===================================================================


class TestComputeMomentumRaw:
    """Tests for compute_momentum_raw."""

    def test_with_prev_data_increasing(self):
        """With previous data, increasing activity => positive."""
        # prev_7d_est = max(0, 80 - 100 + 60) = 40, commit_delta = 60-40 = 20
        # star_delta = 1100-1000 = 100, momentum = 20 + 100*0.1 = 30
        result = compute_momentum_raw(60, 100, 80, 1000, 1100)
        assert result == 30.0

    def test_with_prev_data_decreasing(self):
        """Decreasing activity => negative."""
        # prev_7d_est = max(0, 120 - 50 + 20) = 90, commit_delta = 20-90 = -70
        # star_delta = 1000-1000 = 0, momentum = -70
        result = compute_momentum_raw(20, 50, 120, 1000, 1000)
        assert result == -70.0

    def test_without_prev_data(self):
        """No previous data => fallback to commit-based estimate."""
        # avg_weekly_rest = (100-60)/3 ≈ 13.33, momentum = 60-13.33 ≈ 46.67
        result = compute_momentum_raw(60, 100, None, None, 5000)
        assert abs(result - 46.667) < 0.01

    def test_negative_delta(self):
        """commit_delta can go negative."""
        # prev_7d_est = max(0, 200-100+30) = 130, delta = 30-130=-100
        result = compute_momentum_raw(30, 100, 200, 5000, 5000)
        assert result == -100.0

    def test_all_zero(self):
        """All zeros => 0."""
        result = compute_momentum_raw(0, 0, None, None, 0)
        assert result == 0.0

    def test_all_zero_with_prev(self):
        """All zeros with prev data => 0."""
        result = compute_momentum_raw(0, 0, 0, 0, 0)
        assert result == 0.0

    def test_star_delta_contribution(self):
        """Star delta contributes 0.1 weight."""
        # prev_7d_est = max(0, 100-100+50) = 50, delta = 50-50=0
        # star_delta = 2000-1000=1000, momentum = 0 + 1000*0.1 = 100
        result = compute_momentum_raw(50, 100, 100, 1000, 2000)
        assert result == 100.0

    def test_prev_7d_estimate_clamped(self):
        """prev_commits_7d_estimate is clamped to 0."""
        # prev_7d_est = max(0, 10-200+50) = max(0, -140) = 0
        # commit_delta = 50-0 = 50
        result = compute_momentum_raw(50, 200, 10, 1000, 1000)
        assert result == 50.0


# ===================================================================
# Percentile ranking
# ===================================================================


class TestPercentileScores:
    """Tests for percentile_scores."""

    def test_basic_ranking(self):
        """Ascending values map to ascending percentiles."""
        result = percentile_scores([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result == [0.0, 2.5, 5.0, 7.5, 10.0]

    def test_ties(self):
        """Tied values get the same (lowest) percentile."""
        result = percentile_scores([1.0, 1.0, 3.0])
        # sorted = [1,1,3]. index(1)=0 for both, index(3)=2
        assert result[0] == result[1]
        assert result[2] == 10.0

    def test_single_value(self):
        """Single value => 10.0."""
        assert percentile_scores([42.0]) == [10.0]

    def test_empty(self):
        """Empty list => empty list."""
        assert percentile_scores([]) == []

    def test_two_values(self):
        """Two values => 0.0 and 10.0."""
        result = percentile_scores([5.0, 10.0])
        assert result == [0.0, 10.0]

    def test_descending_input(self):
        """Input order preserved in output."""
        result = percentile_scores([5.0, 3.0, 1.0])
        # sorted = [1,3,5]. 5=>index2=>10, 3=>index1=>5, 1=>index0=>0
        assert result == [10.0, 5.0, 0.0]

    def test_all_same(self):
        """All same values => all get 0.0 (index 0)."""
        result = percentile_scores([7.0, 7.0, 7.0])
        assert result == [0.0, 0.0, 0.0]

    def test_negative_values(self):
        """Negative values are handled correctly."""
        result = percentile_scores([-10.0, 0.0, 10.0])
        assert result == [0.0, 5.0, 10.0]


# ===================================================================
# Determine signal type
# ===================================================================


class TestDetermineSignalType:
    def test_surge_dominant(self):
        assert _determine_signal_type(9.0, 2.0, 3.0) == "surge"

    def test_newcomer_dominant(self):
        assert _determine_signal_type(2.0, 9.0, 3.0) == "newcomer"

    def test_momentum_dominant(self):
        assert _determine_signal_type(2.0, 3.0, 9.0) == "momentum"

    def test_tie_surge_newcomer(self):
        """Tie between surge and newcomer — max picks first key."""
        result = _determine_signal_type(5.0, 5.0, 0.0)
        assert result in ("surge", "newcomer")

    def test_all_zero(self):
        result = _determine_signal_type(0.0, 0.0, 0.0)
        assert result in ("surge", "newcomer", "momentum")


# ===================================================================
# days_since
# ===================================================================


class TestDaysSince:
    def test_recent_date(self):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        assert days_since(yesterday) == 1

    def test_empty(self):
        assert days_since("") == 9999

    def test_none(self):
        assert days_since(None) == 9999

    def test_invalid(self):
        assert days_since("not-a-date") == 9999

    def test_z_suffix(self):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        assert days_since(yesterday) == 1


# ===================================================================
# compute_scores (integration)
# ===================================================================


class TestComputeScores:
    def _make_repo(self, name, stars=1000, commits_30d=50, commits_7d=20,
                   created_at="2024-01-01T00:00:00Z"):
        return {
            "name": name,
            "full_name": f"org/{name}",
            "url": f"https://github.com/org/{name}",
            "description": f"Repo {name}",
            "language": "Python",
            "license": "MIT",
            "stars": stars,
            "forks": 100,
            "open_issues": 10,
            "created_at": created_at,
            "updated_at": "2026-03-28T00:00:00Z",
            "pushed_at": "2026-03-28T00:00:00Z",
            "topics": [],
            "recent_commits_30d": commits_30d,
            "recent_commits_7d": commits_7d,
            "readme_excerpt": "",
        }

    def test_output_schema(self):
        """Every repo in output has all required fields."""
        raw = {
            "date": "2026-03-28",
            "categories": {"Cat": [self._make_repo("a"), self._make_repo("b")]},
        }
        result = compute_scores(raw)
        for repo in result["categories"]["Cat"]:
            assert "trend_score" in repo
            assert "surge_score" in repo
            assert "newcomer_score" in repo
            assert "momentum_score" in repo
            assert "surge_ratio" in repo
            assert "signal_type" in repo
            assert "stars_per_day_avg" in repo
            assert "age_days" in repo
            assert "is_new_entry" in repo
            assert "recent_commits_7d" in repo

    def test_scores_0_to_10(self):
        """All percentile scores are in [0, 10]."""
        repos = [self._make_repo(f"r{i}", commits_7d=i * 10, commits_30d=i * 20)
                 for i in range(5)]
        raw = {"date": "2026-03-28", "categories": {"Cat": repos}}
        result = compute_scores(raw)
        for repo in result["categories"]["Cat"]:
            assert 0 <= repo["surge_score"] <= 10
            assert 0 <= repo["newcomer_score"] <= 10
            assert 0 <= repo["momentum_score"] <= 10
            assert 0 <= repo["trend_score"] <= 10

    def test_sorted_by_composite(self):
        """Output repos are sorted by trend_score descending."""
        repos = [self._make_repo(f"r{i}", commits_7d=i * 5, commits_30d=i * 20 + 10)
                 for i in range(5)]
        raw = {"date": "2026-03-28", "categories": {"Cat": repos}}
        result = compute_scores(raw)
        scores = [r["trend_score"] for r in result["categories"]["Cat"]]
        assert scores == sorted(scores, reverse=True)

    def test_signal_type_valid(self):
        """signal_type is one of surge/newcomer/momentum."""
        repos = [self._make_repo("a"), self._make_repo("b")]
        raw = {"date": "2026-03-28", "categories": {"Cat": repos}}
        result = compute_scores(raw)
        for repo in result["categories"]["Cat"]:
            assert repo["signal_type"] in ("surge", "newcomer", "momentum")

    def test_empty_category(self):
        """Empty category list => empty output."""
        raw = {"date": "2026-03-28", "categories": {"Empty": []}}
        result = compute_scores(raw)
        assert result["categories"]["Empty"] == []

    def test_single_repo(self):
        """Single repo in category => scores are 10.0 for all signals."""
        raw = {"date": "2026-03-28", "categories": {"Solo": [self._make_repo("solo")]}}
        result = compute_scores(raw)
        repo = result["categories"]["Solo"][0]
        assert repo["surge_score"] == 10.0
        assert repo["newcomer_score"] == 10.0
        assert repo["momentum_score"] == 10.0
        assert repo["trend_score"] == 10.0

    def test_backwards_compat_trend_score(self):
        """trend_score field exists for backwards compatibility."""
        raw = {"date": "2026-03-28", "categories": {"Cat": [self._make_repo("a")]}}
        result = compute_scores(raw)
        assert "trend_score" in result["categories"]["Cat"][0]

    def test_top_10_limit(self):
        """Maximum 10 repos per category in output."""
        repos = [self._make_repo(f"r{i}", commits_7d=i) for i in range(15)]
        raw = {"date": "2026-03-28", "categories": {"Big": repos}}
        result = compute_scores(raw)
        assert len(result["categories"]["Big"]) == 10

    def test_date_preserved(self):
        """Date field is preserved in output."""
        raw = {"date": "2026-03-28", "categories": {"Cat": [self._make_repo("a")]}}
        result = compute_scores(raw)
        assert result["date"] == "2026-03-28"

    def test_multiple_categories(self):
        """Handles multiple categories independently."""
        raw = {
            "date": "2026-03-28",
            "categories": {
                "Cat1": [self._make_repo("a")],
                "Cat2": [self._make_repo("b"), self._make_repo("c")],
            },
        }
        result = compute_scores(raw)
        assert len(result["categories"]["Cat1"]) == 1
        assert len(result["categories"]["Cat2"]) == 2

    def test_is_new_entry_no_prev(self):
        """Without previous data, all repos are new entries."""
        raw = {"date": "2026-03-28", "categories": {"Cat": [self._make_repo("a")]}}
        result = compute_scores(raw)
        assert result["categories"]["Cat"][0]["is_new_entry"] is True

    def test_is_new_entry_with_prev(self):
        """With previous data, known repos are not new."""
        repo = self._make_repo("known")
        raw = {"date": "2026-03-28", "categories": {"Cat": [repo]}}
        prev = {"categories": {"Cat": [repo]}}
        result = compute_scores(raw, prev)
        assert result["categories"]["Cat"][0]["is_new_entry"] is False

    def test_is_new_entry_mixed(self):
        """Mix of new and known repos."""
        known = self._make_repo("known")
        new = self._make_repo("new")
        raw = {"date": "2026-03-28", "categories": {"Cat": [known, new]}}
        prev = {"categories": {"Cat": [known]}}
        result = compute_scores(raw, prev)
        by_name = {r["name"]: r for r in result["categories"]["Cat"]}
        assert by_name["known"]["is_new_entry"] is False
        assert by_name["new"]["is_new_entry"] is True

    def test_surge_ratio_in_output(self):
        """surge_ratio raw value is preserved."""
        repo = self._make_repo("a", commits_7d=100, commits_30d=130)
        raw = {"date": "2026-03-28", "categories": {"Cat": [repo]}}
        result = compute_scores(raw)
        # avg_weekly_rest = 30/3 = 10, ratio = 100/10 = 10.0
        assert result["categories"]["Cat"][0]["surge_ratio"] == 10.0

    def test_newcomer_signal_for_young_repo(self):
        """Young repo gets nonzero newcomer_score."""
        young = self._make_repo("young", stars=5000,
                                created_at=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat())
        old = self._make_repo("old", stars=5000, created_at="2020-01-01T00:00:00Z")
        raw = {"date": "2026-03-28", "categories": {"Cat": [young, old]}}
        result = compute_scores(raw)
        by_name = {r["name"]: r for r in result["categories"]["Cat"]}
        assert by_name["young"]["newcomer_score"] > by_name["old"]["newcomer_score"]

    def test_momentum_with_prev_data(self):
        """momentum uses previous data when available."""
        repo = self._make_repo("a", commits_7d=60, commits_30d=100, stars=2000)
        prev_repo = {**repo, "recent_commits_30d": 80, "stars": 1500}
        raw = {"date": "2026-03-28", "categories": {"Cat": [repo]}}
        prev = {"categories": {"Cat": [prev_repo]}}
        result = compute_scores(raw, prev)
        # Should produce a scored result without error
        assert "momentum_score" in result["categories"]["Cat"][0]

    def test_composite_is_weighted_sum(self):
        """trend_score = surge*0.4 + newcomer*0.3 + momentum*0.3."""
        repo = self._make_repo("a")
        raw = {"date": "2026-03-28", "categories": {"Cat": [repo]}}
        result = compute_scores(raw)
        r = result["categories"]["Cat"][0]
        expected = round(r["surge_score"] * 0.4 + r["newcomer_score"] * 0.3 + r["momentum_score"] * 0.3, 1)
        assert r["trend_score"] == expected

    def test_age_days_computed(self):
        """age_days is computed from created_at."""
        repo = self._make_repo("a", created_at="2024-01-01T00:00:00Z")
        raw = {"date": "2026-03-28", "categories": {"Cat": [repo]}}
        result = compute_scores(raw)
        assert result["categories"]["Cat"][0]["age_days"] > 300

    def test_stars_per_day_avg(self):
        """stars_per_day_avg = stars / max(age, 1)."""
        repo = self._make_repo("a", stars=10000, created_at="2024-01-01T00:00:00Z")
        raw = {"date": "2026-03-28", "categories": {"Cat": [repo]}}
        result = compute_scores(raw)
        r = result["categories"]["Cat"][0]
        assert r["stars_per_day_avg"] == round(10000 / r["age_days"], 1)


# ===================================================================
# run_scoring (file I/O)
# ===================================================================


class TestRunScoring:
    def test_loads_and_saves(self, tmp_path):
        """run_scoring loads raw.json and writes trending.json."""
        date_dir = tmp_path / "data" / "2026-03-28"
        date_dir.mkdir(parents=True)
        raw = {
            "date": "2026-03-28",
            "categories": {
                "Test": [
                    {
                        "name": "a",
                        "full_name": "org/a",
                        "stars": 100,
                        "recent_commits_30d": 10,
                        "recent_commits_7d": 5,
                        "created_at": "2025-01-01T00:00:00Z",
                    }
                ]
            },
        }
        (date_dir / "raw.json").write_text(json.dumps(raw), encoding="utf-8")

        with patch("src.scoring.BASE_DIR", tmp_path):
            result = run_scoring("2026-03-28")

        assert (date_dir / "trending.json").exists()
        saved = json.loads((date_dir / "trending.json").read_text(encoding="utf-8"))
        assert saved["date"] == "2026-03-28"
        assert "Test" in saved["categories"]

    def test_loads_prev_data(self, tmp_path):
        """run_scoring loads previous day raw.json for momentum."""
        prev_dir = tmp_path / "data" / "2026-03-27"
        prev_dir.mkdir(parents=True)
        today_dir = tmp_path / "data" / "2026-03-28"
        today_dir.mkdir(parents=True)

        repo = {
            "name": "a",
            "full_name": "org/a",
            "stars": 200,
            "recent_commits_30d": 50,
            "recent_commits_7d": 20,
            "created_at": "2025-01-01T00:00:00Z",
        }
        prev_repo = {**repo, "stars": 150, "recent_commits_30d": 40}
        prev_raw = {"date": "2026-03-27", "categories": {"T": [prev_repo]}}
        today_raw = {"date": "2026-03-28", "categories": {"T": [repo]}}

        (prev_dir / "raw.json").write_text(json.dumps(prev_raw), encoding="utf-8")
        (today_dir / "raw.json").write_text(json.dumps(today_raw), encoding="utf-8")

        with patch("src.scoring.BASE_DIR", tmp_path):
            result = run_scoring("2026-03-28")

        assert result["categories"]["T"][0]["momentum_score"] == 10.0

    def test_no_prev_data(self, tmp_path):
        """Works fine when no previous data exists."""
        date_dir = tmp_path / "data" / "2026-03-28"
        date_dir.mkdir(parents=True)
        raw = {
            "date": "2026-03-28",
            "categories": {
                "T": [
                    {
                        "name": "a",
                        "full_name": "org/a",
                        "stars": 100,
                        "recent_commits_30d": 10,
                        "recent_commits_7d": 5,
                        "created_at": "2025-01-01T00:00:00Z",
                    }
                ]
            },
        }
        (date_dir / "raw.json").write_text(json.dumps(raw), encoding="utf-8")

        with patch("src.scoring.BASE_DIR", tmp_path):
            result = run_scoring("2026-03-28")

        assert "T" in result["categories"]

    def test_default_date(self, tmp_path):
        """run_scoring uses today's date when none provided."""
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = tmp_path / "data" / today
        date_dir.mkdir(parents=True)
        raw = {
            "date": today,
            "categories": {
                "T": [
                    {
                        "name": "a",
                        "full_name": "org/a",
                        "stars": 100,
                        "recent_commits_30d": 10,
                        "recent_commits_7d": 5,
                        "created_at": "2025-01-01T00:00:00Z",
                    }
                ]
            },
        }
        (date_dir / "raw.json").write_text(json.dumps(raw), encoding="utf-8")

        with patch("src.scoring.BASE_DIR", tmp_path):
            result = run_scoring()

        assert result["date"] == today


# ===================================================================
# Integration with conftest fixtures
# ===================================================================


class TestWithFixtures:
    def test_sample_raw_data(self, sample_raw_data):
        """compute_scores works with sample_raw_data fixture."""
        result = compute_scores(sample_raw_data)
        cat = result["categories"]["AI Agent Framework"]
        assert len(cat) == 3
        for repo in cat:
            assert "trend_score" in repo
            assert "surge_score" in repo

    def test_sample_newcomer_repo(self, sample_newcomer_repo):
        """Newcomer repo fixture has expected fields."""
        assert sample_newcomer_repo["recent_commits_7d"] == 150
        assert sample_newcomer_repo["recent_commits_30d"] == 200

    def test_newcomer_gets_high_newcomer_score(self, sample_newcomer_repo, sample_repo):
        """Newcomer repo scores higher on newcomer signal than old repo."""
        raw = {
            "date": "2026-03-28",
            "categories": {"Cat": [sample_newcomer_repo, sample_repo]},
        }
        result = compute_scores(raw)
        by_name = {r["name"]: r for r in result["categories"]["Cat"]}
        assert by_name["new-hotness"]["newcomer_score"] > by_name["langchain"]["newcomer_score"]

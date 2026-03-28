"""Tests for src/report.py — multi-signal scoring system."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.report import (
    score_bar,
    extract_json_from_text,
    generate_en_report,
    generate_reports,
    _signal_emoji,
    _signal_detail,
    _collect_all_repos,
    _age_label,
    _last_push_label,
)


class TestSignalEmoji:
    def test_surge(self):
        assert _signal_emoji("surge") == "\U0001f525"

    def test_newcomer(self):
        assert _signal_emoji("newcomer") == "\U0001f331"

    def test_momentum(self):
        assert _signal_emoji("momentum") == "\U0001f4c8"

    def test_unknown(self):
        assert _signal_emoji("unknown") == ""

    def test_empty(self):
        assert _signal_emoji("") == ""


class TestSignalDetail:
    def test_surge_detail(self):
        repo = {"signal_type": "surge", "surge_ratio": 2.5}
        result = _signal_detail(repo)
        assert result == "x2.5 this week"

    def test_newcomer_detail(self):
        repo = {"signal_type": "newcomer", "age_days": 30, "stars_per_day_avg": 12.5}
        result = _signal_detail(repo)
        assert result == "30d, 12.5/day"

    def test_momentum_detail(self):
        repo = {"signal_type": "momentum", "recent_commits_7d": 45}
        result = _signal_detail(repo)
        assert result == "45 commits/7d"

    def test_unknown_signal(self):
        repo = {"signal_type": "unknown"}
        assert _signal_detail(repo) == ""

    def test_missing_signal_type(self):
        assert _signal_detail({}) == ""


class TestCollectAllRepos:
    def test_flattens_categories(self, sample_trending_data):
        result = _collect_all_repos(sample_trending_data)
        assert len(result) == 2
        assert all("_category" in r for r in result)
        assert result[0]["_category"] == "AI Agent Framework"

    def test_empty_categories(self):
        result = _collect_all_repos({"categories": {}})
        assert result == []

    def test_missing_categories_key(self):
        result = _collect_all_repos({})
        assert result == []


class TestScoreBar:
    def test_full_score(self):
        result = score_bar(10.0)
        assert result == "\u2588" * 10

    def test_zero_score(self):
        result = score_bar(0.0)
        assert result == "\u2591" * 10

    def test_mid_score(self):
        result = score_bar(5.0)
        assert "\u2588" in result
        assert "\u2591" in result
        assert len(result) == 10


class TestAgeLabel:
    def test_days(self):
        assert _age_label(30) == "30d"

    def test_years(self):
        assert _age_label(730) == "2y"

    def test_exactly_one_year(self):
        assert _age_label(365) == "1y"

    def test_zero_days(self):
        assert _age_label(0) == "0d"


class TestLastPushLabel:
    def test_missing_pushed_at(self):
        assert _last_push_label({}) == "unknown"

    def test_empty_pushed_at(self):
        assert _last_push_label({"pushed_at": ""}) == "unknown"

    def test_invalid_date(self):
        assert _last_push_label({"pushed_at": "not-a-date"}) == "unknown"


class TestExtractJsonFromText:
    def test_direct_json(self):
        result = extract_json_from_text('{"key": "val"}')
        assert result == {"key": "val"}

    def test_json_in_code_block(self):
        text = '```json\n{"a": 1}\n```'
        result = extract_json_from_text(text)
        assert result == {"a": 1}

    def test_none_input(self):
        with pytest.raises(TypeError):
            extract_json_from_text(None)

    def test_garbage(self):
        result = extract_json_from_text("random text no json here")
        assert result is None


class TestGenerateEnReport:
    def test_has_cross_category_sections(self, sample_trending_data):
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        assert "## Cross-Category Highlights" in report
        assert "### Top 10 Surging" in report
        assert "### Top 10 Momentum" in report
        assert "### Top 10 Overall" in report

    def test_has_per_category_signals(self, sample_trending_data, sample_analysis):
        analyses = {"AI Agent Framework": sample_analysis}
        report = generate_en_report("2025-03-28", sample_trending_data, analyses)
        assert "## AI Agent Framework" in report
        assert "### Surging" in report
        assert "### Gaining Momentum" in report
        assert "### Overall Top 5" in report
        assert "### AI Analysis Ranking" in report

    def test_contains_repo_names(self, sample_trending_data):
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        assert "langchain" in report
        assert "autogen" in report

    def test_empty_categories(self):
        trending = {"date": "2025-03-28", "categories": {}}
        report = generate_en_report("2025-03-28", trending, {})
        assert "## Cross-Category Highlights" in report
        # No per-category sections
        assert "## AI Agent Framework" not in report

    def test_no_rising_stars_when_zero_newcomer(self, sample_trending_data):
        """Rising Stars section should not appear if all newcomer_scores are 0."""
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        # Cross-category Rising Stars should not appear
        assert "### Top 10 Rising Stars" not in report

    def test_report_without_analysis(self, sample_trending_data):
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        assert "Qualitative analysis not available" in report

    def test_signal_emojis_in_report(self, sample_trending_data):
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        # surge signal repos should have fire emoji
        assert "\U0001f525" in report

    def test_multi_signal_scores_in_overall(self, sample_trending_data):
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        # Overall Top 5 table has Surge/Newcomer/Momentum columns
        assert "| Trend | Surge | Newcomer | Momentum |" in report


class TestGenerateReports:
    def test_creates_report_file(self, tmp_path, sample_trending_data, sample_analysis):
        """generate_reports creates a .md file with correct content."""
        date = "2025-03-28"
        data_dir = tmp_path / "data" / date
        data_dir.mkdir(parents=True)
        analysis_dir = data_dir / "analysis"
        analysis_dir.mkdir()

        # Write trending.json
        with open(data_dir / "trending.json", "w", encoding="utf-8") as f:
            json.dump(sample_trending_data, f)

        # Write analysis
        with open(analysis_dir / "ai_agent_framework.json", "w", encoding="utf-8") as f:
            json.dump(sample_analysis, f)

        # Patch BASE_DIR
        with patch("src.report.BASE_DIR", tmp_path):
            result = generate_reports(date)

        assert result.exists()
        assert result.name == f"{date}.md"
        content = result.read_text(encoding="utf-8")
        assert "Cross-Category Highlights" in content
        assert "langchain" in content
        assert "AI Agent Framework" in content

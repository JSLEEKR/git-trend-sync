"""Tests for src/report.py"""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.report import (
    score_bar,
    extract_json_from_text,
    generate_en_report,
    _activity_emoji,
    _status,
    _age_label,
    _last_push_label,
)


class TestScoreBar:
    def test_full_score(self):
        result = score_bar(10.0)
        assert "█" in result
        assert len(result) == 10

    def test_zero_score(self):
        result = score_bar(0.0)
        assert result == "░" * 10

    def test_mid_score(self):
        result = score_bar(5.0)
        assert "█" in result
        assert "░" in result
        assert len(result) == 10


class TestActivityEmoji:
    def test_high_score(self):
        assert _activity_emoji(8.0) == "🔥"

    def test_medium_score(self):
        assert _activity_emoji(5.0) == "📈"

    def test_low_score(self):
        assert _activity_emoji(2.0) == ""


class TestStatus:
    def test_new_entry(self):
        assert _status({"is_new_entry": True}) == "NEW ENTRY"

    def test_active(self):
        assert _status({"is_new_entry": False}) == "ACTIVE"

    def test_missing_key(self):
        assert _status({}) == "ACTIVE"


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
        import pytest
        with pytest.raises(TypeError):
            extract_json_from_text(None)

    def test_garbage(self):
        result = extract_json_from_text("random text no json here")
        assert result is None


class TestGenerateEnReport:
    def test_basic_report(self, sample_trending_data, sample_analysis):
        analyses = {"AI Agent Framework": sample_analysis}
        report = generate_en_report("2025-03-28", sample_trending_data, analyses)
        assert "# AI Agent Trend Report" in report
        assert "AI Agent Framework" in report
        assert "langchain" in report
        assert "Table of Contents" in report

    def test_report_without_analysis(self, sample_trending_data):
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        assert "Qualitative analysis not available" in report

    def test_cross_category_insights(self, sample_trending_data):
        report = generate_en_report("2025-03-28", sample_trending_data, {})
        assert "Cross-Category Insights" in report
        assert "Top Repositories Across All Categories" in report

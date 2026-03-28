"""Tests for src/gaps.py"""

import json
import os
from unittest.mock import patch, MagicMock, mock_open

import pytest
import requests

from src.gaps import (
    classify_gap,
    extract_keywords,
    compute_demand,
    fetch_repo_issues,
    scan_gaps,
    run_gaps,
    STOP_WORDS,
)


class TestClassifyGap:
    def test_missing_tool_cli(self):
        assert classify_gap("Need a CLI for debugging", []) == "missing_tool"

    def test_missing_tool_tool(self):
        assert classify_gap("Add a tool for profiling", []) == "missing_tool"

    def test_missing_tool_command_line(self):
        assert classify_gap("command-line interface needed", []) == "missing_tool"

    def test_missing_tool_command_line_space(self):
        assert classify_gap("command line option missing", []) == "missing_tool"

    def test_missing_plugin(self):
        assert classify_gap("VSCode plugin for linting", []) == "missing_plugin"

    def test_missing_plugin_extension(self):
        assert classify_gap("Browser extension support", []) == "missing_plugin"

    def test_missing_plugin_integration(self):
        assert classify_gap("Slack integration wanted", []) == "missing_plugin"

    def test_missing_feature_label(self):
        assert classify_gap("Some title", ["feature-request"]) == "missing_feature"

    def test_missing_feature_enhancement_label(self):
        assert classify_gap("Some title", ["enhancement"]) == "missing_feature"

    def test_pain_point_i_wish(self):
        assert classify_gap("I wish there was a way to export", []) == "pain_point"

    def test_pain_point_would_be_nice(self):
        assert classify_gap("It would be nice to have autocomplete", []) == "pain_point"

    def test_pain_point_how_do_i(self):
        assert classify_gap("How do I run tests in parallel?", []) == "pain_point"

    def test_pain_point_is_there_a_way(self):
        assert classify_gap("Is there a way to disable logging?", []) == "pain_point"

    def test_none_no_match(self):
        assert classify_gap("Fix typo in docs", []) is None

    def test_case_insensitive_tool(self):
        assert classify_gap("CLI Tool for Debugging", []) == "missing_tool"

    def test_case_insensitive_pain(self):
        assert classify_gap("I WISH this was easier", []) == "pain_point"

    def test_case_insensitive_labels(self):
        assert classify_gap("Something", ["Enhancement"]) == "missing_feature"

    def test_tool_takes_priority_over_plugin(self):
        """Tool keywords checked first."""
        assert classify_gap("CLI plugin integration", []) == "missing_tool"

    def test_plugin_takes_priority_over_feature(self):
        assert classify_gap("plugin for data", ["enhancement"]) == "missing_plugin"


class TestExtractKeywords:
    def test_basic(self):
        result = extract_keywords("Need CLI debugging chain")
        assert "cli" in result
        assert "debugging" in result
        assert "chain" in result

    def test_stop_words_filtered(self):
        result = extract_keywords("Add support for the plugin")
        assert "add" not in result
        assert "support" not in result
        assert "the" not in result
        assert "for" not in result
        assert "plugin" in result

    def test_short_words_filtered(self):
        result = extract_keywords("Go is ok but no")
        # "go" is 2 chars, "is" stop word, "ok" is 2 chars, "but" is 3 chars
        assert "but" in result
        assert "go" not in result
        assert "ok" not in result

    def test_empty(self):
        assert extract_keywords("") == []

    def test_all_stop_words(self):
        result = extract_keywords("the a an is for to in of")
        assert result == []

    def test_preserves_hyphenated(self):
        result = extract_keywords("command-line interface")
        assert "command-line" in result
        assert "interface" in result


class TestComputeDemand:
    def test_basic(self):
        assert compute_demand(10, 5) == 25.0

    def test_zero(self):
        assert compute_demand(0, 0) == 0.0

    def test_high_reactions(self):
        assert compute_demand(100, 50) == 250.0

    def test_only_reactions(self):
        assert compute_demand(5, 0) == 10.0

    def test_only_comments(self):
        assert compute_demand(0, 7) == 7.0


class TestFetchRepoIssues:
    @patch("src.gaps.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {
                    "number": 42,
                    "title": "Need CLI tool",
                    "html_url": "https://github.com/owner/repo/issues/42",
                    "reactions": {"total_count": 10},
                    "comments": 5,
                    "labels": [{"name": "enhancement"}],
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ]
        }
        mock_get.return_value = mock_resp

        result = fetch_repo_issues("owner/repo", {})
        assert len(result) == 1
        assert result[0]["number"] == 42
        assert result[0]["title"] == "Need CLI tool"
        assert result[0]["reactions"] == 10
        assert result[0]["comments"] == 5
        assert result[0]["labels"] == ["enhancement"]

    @patch("src.gaps.requests.get")
    def test_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.RequestException("403 Forbidden")
        result = fetch_repo_issues("owner/repo", {})
        assert result == []

    @patch("src.gaps.requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"items": []}
        mock_get.return_value = mock_resp

        result = fetch_repo_issues("owner/repo", {})
        assert result == []

    @patch("src.gaps.requests.get")
    def test_multiple_issues(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {
                    "number": 1,
                    "title": "CLI needed",
                    "html_url": "https://github.com/a/b/issues/1",
                    "reactions": {"total_count": 20},
                    "comments": 10,
                    "labels": [],
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "number": 2,
                    "title": "Plugin wanted",
                    "html_url": "https://github.com/a/b/issues/2",
                    "reactions": {"total_count": 5},
                    "comments": 2,
                    "labels": [{"name": "feature-request"}],
                    "created_at": "2026-02-01T00:00:00Z",
                },
            ]
        }
        mock_get.return_value = mock_resp

        result = fetch_repo_issues("a/b", {})
        assert len(result) == 2


class TestScanGaps:
    @patch("src.gaps.fetch_repo_issues")
    def test_basic(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "number": 1,
                "title": "Need CLI tool for debugging",
                "url": "https://github.com/org/repo/issues/1",
                "reactions": 10,
                "comments": 5,
                "labels": [],
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        trending = {
            "date": "2026-03-28",
            "categories": {
                "AI": [
                    {"full_name": "org/repo", "stars": 5000, "trend_score": 3.0},
                ]
            },
        }
        result = scan_gaps(trending, {})
        assert "AI" in result["categories"]
        assert result["categories"]["AI"]["total_signals"] == 1
        gap = result["categories"]["AI"]["top_gaps"][0]
        assert gap["source_repo"] == "org/repo"
        assert gap["gap_type"] == "missing_tool"
        assert gap["demand_score"] == 25.0

    @patch("src.gaps.fetch_repo_issues")
    def test_empty_trending(self, mock_fetch):
        trending = {"date": "2026-03-28", "categories": {}}
        result = scan_gaps(trending, {})
        assert result["categories"] == {}
        mock_fetch.assert_not_called()

    @patch("src.gaps.fetch_repo_issues")
    def test_sorts_by_demand(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "number": 1,
                "title": "CLI for low demand",
                "url": "https://github.com/org/repo/issues/1",
                "reactions": 1,
                "comments": 0,
                "labels": [],
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "number": 2,
                "title": "CLI for high demand",
                "url": "https://github.com/org/repo/issues/2",
                "reactions": 50,
                "comments": 20,
                "labels": [],
                "created_at": "2026-01-01T00:00:00Z",
            },
        ]
        trending = {
            "date": "2026-03-28",
            "categories": {
                "Tools": [
                    {"full_name": "org/repo", "stars": 1000, "trend_score": 2.0},
                ]
            },
        }
        result = scan_gaps(trending, {})
        gaps = result["categories"]["Tools"]["top_gaps"]
        assert gaps[0]["demand_score"] > gaps[1]["demand_score"]
        assert gaps[0]["issue_number"] == 2

    @patch("src.gaps.fetch_repo_issues")
    def test_skips_unclassified_issues(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "number": 1,
                "title": "Fix typo in docs",
                "url": "https://github.com/org/repo/issues/1",
                "reactions": 100,
                "comments": 50,
                "labels": [],
                "created_at": "2026-01-01T00:00:00Z",
            },
        ]
        trending = {
            "date": "2026-03-28",
            "categories": {
                "AI": [
                    {"full_name": "org/repo", "stars": 1000, "trend_score": 1.0},
                ]
            },
        }
        result = scan_gaps(trending, {})
        assert result["categories"]["AI"]["total_signals"] == 0
        assert result["categories"]["AI"]["top_gaps"] == []

    @patch("src.gaps.fetch_repo_issues")
    def test_limits_top_10_repos(self, mock_fetch):
        """Only top 10 repos per category are scanned."""
        mock_fetch.return_value = []
        repos = [{"full_name": f"org/repo{i}", "stars": 100, "trend_score": 1.0} for i in range(15)]
        trending = {"date": "2026-03-28", "categories": {"AI": repos}}
        scan_gaps(trending, {})
        assert mock_fetch.call_count == 10

    @patch("src.gaps.fetch_repo_issues")
    def test_limits_top_10_gaps(self, mock_fetch):
        """Only top 10 gaps per category are returned."""
        issues = [
            {
                "number": i,
                "title": f"CLI tool {i}",
                "url": f"https://github.com/org/repo/issues/{i}",
                "reactions": i,
                "comments": i,
                "labels": [],
                "created_at": "2026-01-01T00:00:00Z",
            }
            for i in range(15)
        ]
        mock_fetch.return_value = issues
        trending = {
            "date": "2026-03-28",
            "categories": {
                "AI": [{"full_name": "org/repo", "stars": 1000, "trend_score": 1.0}]
            },
        }
        result = scan_gaps(trending, {})
        assert len(result["categories"]["AI"]["top_gaps"]) == 10
        assert result["categories"]["AI"]["total_signals"] == 15


class TestRunGaps:
    @patch("src.gaps.scan_gaps")
    @patch("src.gaps.json.dump")
    @patch("builtins.open", new_callable=mock_open, read_data='{"date":"2026-03-28","categories":{}}')
    @patch("src.gaps.Path.mkdir")
    @patch("src.gaps.get_headers", return_value={"Accept": "application/vnd.github+json"})
    def test_loads_and_saves(self, mock_headers, mock_mkdir, mock_file, mock_dump, mock_scan):
        mock_scan.return_value = {"date": "2026-03-28", "categories": {}}

        result = run_gaps("2026-03-28")
        assert result["date"] == "2026-03-28"
        mock_scan.assert_called_once()
        mock_dump.assert_called_once()

    @patch("src.gaps.scan_gaps")
    @patch("builtins.open", new_callable=mock_open, read_data='{"date":"2026-03-28","categories":{"AI":[]}}')
    @patch("src.gaps.Path.mkdir")
    @patch("src.gaps.get_headers", return_value={})
    def test_creates_output_file(self, mock_headers, mock_mkdir, mock_file, mock_scan):
        mock_scan.return_value = {"date": "2026-03-28", "categories": {"AI": {"total_signals": 0, "top_gaps": []}}}
        run_gaps("2026-03-28")
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("src.gaps.scan_gaps")
    @patch("builtins.open", new_callable=mock_open, read_data='{"date":"2026-03-28","categories":{}}')
    @patch("src.gaps.Path.mkdir")
    @patch("src.gaps.get_headers", return_value={})
    @patch("builtins.print")
    def test_prints_status(self, mock_print, mock_headers, mock_mkdir, mock_file, mock_scan):
        mock_scan.return_value = {"date": "2026-03-28", "categories": {"AI": {"total_signals": 5, "top_gaps": []}}}
        run_gaps("2026-03-28")
        mock_print.assert_called_once()
        printed = mock_print.call_args[0][0]
        assert "5 signals" in printed

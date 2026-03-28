"""Tests for src/badge.py"""

import json
from unittest.mock import patch
from pathlib import Path

import pytest

from src.badge import get_badge_url, get_badge_markdown, generate_badges_file


class TestGetBadgeUrl:
    def test_top_rank(self):
        url = get_badge_url("langchain", 1, "AI Agent")
        assert "brightgreen" in url
        assert "shields.io" in url
        assert "#1" in url

    def test_mid_rank(self):
        url = get_badge_url("repo", 4, "RAG")
        assert "green" in url

    def test_low_rank(self):
        url = get_badge_url("repo", 7, "RAG")
        assert "yellow" in url

    def test_category_spaces_encoded(self):
        url = get_badge_url("repo", 1, "AI Agent Framework")
        assert "%20" in url


class TestGetBadgeMarkdown:
    def test_markdown_format(self):
        md = get_badge_markdown("langchain", 1, "AI Agent")
        assert md.startswith("[![")
        assert "shields.io" in md
        assert "git-trend-sync" in md


class TestGenerateBadgesFile:
    def test_generates_file(self, tmp_path):
        data_dir = tmp_path / "data" / "2025-03-28"
        data_dir.mkdir(parents=True)
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        trending = {
            "categories": {
                "AI Agent": [
                    {"name": "langchain"},
                    {"name": "autogen"},
                ],
            }
        }
        (data_dir / "trending.json").write_text(json.dumps(trending))

        with patch("src.badge.BASE_DIR", tmp_path):
            output = generate_badges_file("2025-03-28")
            assert output is not None
            content = output.read_text(encoding="utf-8")
            assert "langchain" in content
            assert "autogen" in content

    def test_missing_trending_data(self, tmp_path):
        with patch("src.badge.BASE_DIR", tmp_path):
            result = generate_badges_file("2025-03-28")
            assert result is None

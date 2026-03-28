"""Tests for src/apply.py"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.apply import (
    _load_json,
    _all_repos,
    _match_repo,
    find_repo_in_trending,
    generate_apply_report,
)


class TestLoadJson:
    def test_valid_json(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}')
        result = _load_json(p)
        assert result == {"key": "value"}

    def test_missing_file(self, tmp_path):
        p = tmp_path / "missing.json"
        result = _load_json(p)
        assert result is None

    def test_malformed_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json {")
        result = _load_json(p)
        assert result is None

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("")
        result = _load_json(p)
        assert result is None


class TestAllRepos:
    def test_flattens_categories(self):
        data = {
            "categories": {
                "A": [{"name": "r1"}, {"name": "r2"}],
                "B": [{"name": "r3"}],
            }
        }
        repos = _all_repos(data)
        assert len(repos) == 3

    def test_empty_categories(self):
        data = {"categories": {}}
        assert _all_repos(data) == []

    def test_no_categories_key(self):
        assert _all_repos({}) == []


class TestMatchRepo:
    def test_match_by_name(self):
        repos = [{"name": "langchain", "full_name": "lc-ai/langchain"}]
        result = _match_repo(repos, "langchain")
        assert result is not None
        assert result["name"] == "langchain"

    def test_match_by_full_name(self):
        repos = [{"name": "langchain", "full_name": "lc-ai/langchain"}]
        result = _match_repo(repos, "lc-ai/langchain")
        assert result is not None

    def test_case_insensitive(self):
        repos = [{"name": "LangChain", "full_name": "lc-ai/LangChain"}]
        result = _match_repo(repos, "langchain")
        assert result is not None

    def test_no_match(self):
        repos = [{"name": "other", "full_name": "o/other"}]
        result = _match_repo(repos, "langchain")
        assert result is None

    def test_empty_list(self):
        assert _match_repo([], "langchain") is None


class TestFindRepoInTrending:
    @patch("src.apply._load_json")
    def test_found(self, mock_load):
        mock_load.return_value = {
            "categories": {"Cat": [{"name": "langchain", "full_name": "lc/langchain"}]}
        }
        result = find_repo_in_trending("langchain", "2025-03-28")
        assert result is not None
        assert result["name"] == "langchain"

    @patch("src.apply._load_json")
    def test_not_found(self, mock_load):
        mock_load.return_value = {
            "categories": {"Cat": [{"name": "other", "full_name": "o/other"}]}
        }
        result = find_repo_in_trending("langchain", "2025-03-28")
        assert result is None

    @patch("src.apply._load_json")
    def test_no_data(self, mock_load):
        mock_load.return_value = None
        result = find_repo_in_trending("langchain", "2025-03-28")
        assert result is None


class TestGenerateApplyReport:
    def test_creates_report(self, tmp_path, sample_repo, sample_profile):
        with patch("src.apply.BASE_DIR", tmp_path):
            # Create needed dirs and template
            (tmp_path / "config" / "prompts").mkdir(parents=True)
            (tmp_path / "config" / "prompts" / "apply.md").write_text(
                "Repo: {{repo_data}}\nProject: {{project_profile}}"
            )

            report_path = generate_apply_report(sample_repo, sample_profile, "2025-03-28")
            assert report_path.exists()
            content = report_path.read_text(encoding="utf-8")
            assert "Apply Report" in content
            assert "langchain" in content

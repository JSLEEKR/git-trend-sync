"""Tests for src/collect.py"""

import json
import os
from unittest.mock import patch, MagicMock, mock_open

import pytest
import requests

from src.collect import (
    get_headers,
    search_repos,
    get_readme,
    get_recent_commits_count,
    extract_repo_data,
)


class TestGetHeaders:
    def test_with_token(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test123"}):
            headers = get_headers()
            assert headers["Authorization"] == "Bearer ghp_test123"
            assert "Accept" in headers

    def test_without_token(self):
        with patch.dict(os.environ, {}, clear=True):
            headers = get_headers()
            assert "Authorization" not in headers
            assert "Accept" in headers


class TestSearchRepos:
    @patch("src.collect.requests.get")
    def test_search_repos_returns_items(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"items": [{"name": "repo1"}, {"name": "repo2"}]}
        mock_get.return_value = mock_resp

        result = search_repos("ai", 10, {})
        assert len(result) == 2
        assert result[0]["name"] == "repo1"

    @patch("src.collect.requests.get")
    def test_search_repos_empty_items(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"items": []}
        mock_get.return_value = mock_resp

        result = search_repos("ai", 10, {})
        assert result == []

    @patch("src.collect.requests.get")
    def test_search_repos_no_items_key(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        result = search_repos("ai", 10, {})
        assert result == []

    @patch("src.collect.requests.get")
    def test_search_repos_raises_on_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.exceptions.HTTPError):
            search_repos("ai", 10, {})


class TestGetReadme:
    @patch("src.collect.requests.get")
    def test_get_readme_success(self, mock_get):
        import base64
        content = base64.b64encode(b"# Hello World").decode()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": content}
        mock_get.return_value = mock_resp

        result = get_readme("owner", "repo", {})
        assert "Hello World" in result

    @patch("src.collect.requests.get")
    def test_get_readme_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = get_readme("owner", "repo", {})
        assert result == ""

    @patch("src.collect.requests.get")
    def test_get_readme_empty_content(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": ""}
        mock_get.return_value = mock_resp

        result = get_readme("owner", "repo", {})
        assert result == ""


class TestGetRecentCommitsCount:
    @patch("src.collect.requests.get")
    def test_with_link_header(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {
            "Link": '<https://api.github.com/repos/o/r/commits?page=42>; rel="last"'
        }
        mock_resp.json.return_value = [{"sha": "abc"}]
        mock_get.return_value = mock_resp

        result = get_recent_commits_count("owner", "repo", {})
        assert result == 42

    @patch("src.collect.requests.get")
    def test_without_link_header(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.json.return_value = [{"sha": "abc"}]
        mock_get.return_value = mock_resp

        result = get_recent_commits_count("owner", "repo", {})
        assert result == 1

    @patch("src.collect.requests.get")
    def test_error_status(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp

        result = get_recent_commits_count("owner", "repo", {})
        assert result == 0


class TestExtractRepoData:
    @patch("src.collect.get_recent_commits_count", return_value=50)
    @patch("src.collect.get_readme", return_value="# Test README content")
    @patch("src.collect.time")
    def test_extracts_all_fields(self, mock_time, mock_readme, mock_commits, sample_repo):
        item = {
            "name": "langchain",
            "full_name": "langchain-ai/langchain",
            "html_url": "https://github.com/langchain-ai/langchain",
            "owner": {"login": "langchain-ai"},
            "description": "Build context-aware reasoning applications",
            "language": "Python",
            "license": {"spdx_id": "MIT"},
            "stargazers_count": 50000,
            "forks_count": 8000,
            "open_issues_count": 200,
            "created_at": "2022-10-01T00:00:00Z",
            "updated_at": "2025-03-28T00:00:00Z",
            "pushed_at": "2025-03-28T00:00:00Z",
            "topics": ["llm", "ai"],
        }
        result = extract_repo_data(item, {})
        assert result["name"] == "langchain"
        assert result["stars"] == 50000
        assert result["recent_commits_30d"] == 50
        assert result["readme_excerpt"] == "# Test README content"

    @patch("src.collect.get_recent_commits_count", return_value=0)
    @patch("src.collect.get_readme", return_value="")
    @patch("src.collect.time")
    def test_missing_optional_fields(self, mock_time, mock_readme, mock_commits):
        item = {
            "name": "test",
            "full_name": "owner/test",
            "html_url": "https://github.com/owner/test",
            "owner": {"login": "owner"},
        }
        result = extract_repo_data(item, {})
        assert result["description"] == ""
        assert result["language"] == ""
        assert result["license"] == "Unknown"
        assert result["stars"] == 0

    @patch("src.collect.get_recent_commits_count", return_value=0)
    @patch("src.collect.get_readme", return_value="x" * 5000)
    @patch("src.collect.time")
    def test_readme_truncation(self, mock_time, mock_readme, mock_commits):
        item = {
            "name": "test",
            "full_name": "o/t",
            "html_url": "https://github.com/o/t",
            "owner": {"login": "o"},
        }
        result = extract_repo_data(item, {})
        assert len(result["readme_excerpt"]) == 3000

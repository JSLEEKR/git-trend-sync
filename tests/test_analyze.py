"""Tests for src/analyze.py"""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from src.analyze import find_claude_cmd, extract_json


class TestFindClaudeCmd:
    @patch("src.analyze.shutil.which", return_value=None)
    @patch("src.analyze.Path")
    def test_fallback_to_claude(self, mock_path_cls, mock_which):
        # Make all candidate paths not exist
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)
        mock_path_cls.return_value = mock_path_instance
        mock_path_cls.home.return_value = mock_path_instance

        with patch.dict(os.environ, {"APPDATA": "/nonexistent"}, clear=False):
            result = find_claude_cmd()
        assert result == "claude"

    @patch("src.analyze.shutil.which", return_value="/usr/local/bin/claude")
    @patch("src.analyze.Path")
    def test_found_on_path(self, mock_path_cls, mock_which):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)
        mock_path_cls.return_value = mock_path_instance
        mock_path_cls.home.return_value = mock_path_instance

        with patch.dict(os.environ, {"APPDATA": "/nonexistent"}, clear=False):
            result = find_claude_cmd()
        assert result == "/usr/local/bin/claude"


class TestExtractJson:
    def test_direct_json(self):
        data = {"key": "value"}
        result = extract_json(json.dumps(data))
        assert result == data

    def test_json_in_markdown_block(self):
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_json_in_plain_code_block(self):
        text = 'Before\n```\n{"key": "value"}\n```\nAfter'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_json_with_individual_analysis(self):
        data = {"individual_analysis": [{"name": "test"}]}
        text = f"Some preamble {json.dumps(data)} trailing text"
        result = extract_json(text)
        assert result is not None
        assert "individual_analysis" in result

    def test_invalid_json(self):
        result = extract_json("not json at all")
        assert result is None

    def test_empty_string(self):
        result = extract_json("")
        assert result is None

    def test_none_input(self):
        import pytest
        with pytest.raises(TypeError):
            extract_json(None)

    def test_malformed_json_in_block(self):
        text = '```json\n{broken json\n```'
        result = extract_json(text)
        assert result is None

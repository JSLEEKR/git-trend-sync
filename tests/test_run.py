"""Tests for run.py"""

from unittest.mock import patch, MagicMock

import pytest

from run import run_step


class TestRunStep:
    def test_successful_step(self):
        mock_func = MagicMock(return_value="result")
        result = run_step("Test Step", mock_func, "arg1")
        assert result == "result"
        mock_func.assert_called_once_with("arg1")

    def test_failed_step(self):
        mock_func = MagicMock(side_effect=Exception("boom"))
        with pytest.raises(Exception, match="boom"):
            run_step("Failing Step", mock_func)

    def test_step_with_no_args(self):
        mock_func = MagicMock(return_value=42)
        result = run_step("No Args", mock_func)
        assert result == 42
        mock_func.assert_called_once_with()

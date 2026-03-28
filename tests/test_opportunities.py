"""Tests for src/opportunities.py"""

import json

import pytest

from src.opportunities import (
    normalize_scores,
    compute_opportunity_score,
    detect_cross_category_patterns,
    classify_opportunity,
    generate_opportunity_report,
    run_opportunities,
)


# ---------------------------------------------------------------------------
# TestNormalizeScores
# ---------------------------------------------------------------------------

class TestNormalizeScores:
    def test_basic(self):
        result = normalize_scores([0, 5, 10])
        assert result[0] == 0.0
        assert result[2] == 10.0
        assert 4.0 <= result[1] <= 6.0  # 5.0

    def test_empty(self):
        assert normalize_scores([]) == []

    def test_single(self):
        assert normalize_scores([42.0]) == [10.0]

    def test_all_same(self):
        result = normalize_scores([7, 7, 7])
        assert result == [5.0, 5.0, 5.0]

    def test_negative_values(self):
        result = normalize_scores([-10, 0, 10])
        assert result[0] == 0.0
        assert result[2] == 10.0
        assert 4.0 <= result[1] <= 6.0

    def test_two_values(self):
        result = normalize_scores([0, 100])
        assert result == [0.0, 10.0]

    def test_floats(self):
        result = normalize_scores([1.5, 3.0, 4.5])
        assert result[0] == 0.0
        assert result[2] == 10.0


# ---------------------------------------------------------------------------
# TestComputeOpportunityScore
# ---------------------------------------------------------------------------

class TestComputeOpportunityScore:
    def test_basic(self):
        score = compute_opportunity_score(6.0, 7.0, 5.0)
        assert score == 6.0

    def test_all_high(self):
        score = compute_opportunity_score(10.0, 10.0, 10.0)
        assert score == 10.0

    def test_all_zero(self):
        score = compute_opportunity_score(0.0, 0.0, 0.0)
        assert score == 0.0

    def test_rounding(self):
        score = compute_opportunity_score(3.0, 3.0, 3.0)
        assert score == 3.0

    def test_uneven(self):
        score = compute_opportunity_score(1.0, 2.0, 3.0)
        assert score == 2.0


# ---------------------------------------------------------------------------
# TestDetectCrossCategoryPatterns
# ---------------------------------------------------------------------------

class TestDetectCrossCategoryPatterns:
    def test_found(self):
        gaps = {
            "AI Agent": [{"keywords": ["debugging", "cli"]}],
            "RAG": [{"keywords": ["debugging", "vector"]}],
            "Multi-Agent": [{"keywords": ["debugging", "orchestration"]}],
        }
        result = detect_cross_category_patterns(gaps)
        assert len(result) == 1
        assert result[0]["keyword"] == "debugging"
        assert result[0]["total_count"] == 3
        assert len(result[0]["categories"]) == 3

    def test_none_found(self):
        gaps = {
            "AI Agent": [{"keywords": ["cli"]}],
            "RAG": [{"keywords": ["vector"]}],
            "Multi-Agent": [{"keywords": ["orchestration"]}],
        }
        result = detect_cross_category_patterns(gaps)
        assert result == []

    def test_keyword_in_two_cats_not_enough(self):
        gaps = {
            "AI Agent": [{"keywords": ["debugging"]}],
            "RAG": [{"keywords": ["debugging"]}],
        }
        result = detect_cross_category_patterns(gaps)
        assert result == []

    def test_empty(self):
        assert detect_cross_category_patterns({}) == []

    def test_multiple_patterns_sorted(self):
        gaps = {
            "A": [{"keywords": ["x", "y"]}],
            "B": [{"keywords": ["x", "y"]}],
            "C": [{"keywords": ["x", "y"]}],
            "D": [{"keywords": ["x"]}],
        }
        result = detect_cross_category_patterns(gaps)
        assert len(result) == 2
        # x has total_count=4, y has total_count=3
        assert result[0]["keyword"] == "x"
        assert result[0]["total_count"] == 4
        assert result[1]["keyword"] == "y"
        assert result[1]["total_count"] == 3

    def test_case_insensitive(self):
        gaps = {
            "A": [{"keywords": ["Debug"]}],
            "B": [{"keywords": ["debug"]}],
            "C": [{"keywords": ["DEBUG"]}],
        }
        result = detect_cross_category_patterns(gaps)
        assert len(result) == 1
        assert result[0]["keyword"] == "debug"


# ---------------------------------------------------------------------------
# TestClassifyOpportunity
# ---------------------------------------------------------------------------

class TestClassifyOpportunity:
    def test_hot(self):
        opp = {"trend_score": 7, "demand_normalized": 8, "signal_type": "momentum"}
        assert classify_opportunity(opp) == "hot"

    def test_rising(self):
        opp = {"trend_score": 3, "demand_normalized": 3, "signal_type": "newcomer"}
        assert classify_opportunity(opp) == "rising"

    def test_high_demand(self):
        opp = {"trend_score": 3, "demand_normalized": 9, "signal_type": "momentum"}
        assert classify_opportunity(opp) == "high_demand"

    def test_standard(self):
        opp = {"trend_score": 3, "demand_normalized": 3, "signal_type": "momentum"}
        assert classify_opportunity(opp) == "standard"

    def test_hot_takes_priority_over_high_demand(self):
        opp = {"trend_score": 8, "demand_normalized": 9, "signal_type": "momentum"}
        assert classify_opportunity(opp) == "hot"

    def test_hot_takes_priority_over_rising(self):
        opp = {"trend_score": 8, "demand_normalized": 8, "signal_type": "newcomer"}
        assert classify_opportunity(opp) == "hot"

    def test_rising_takes_priority_over_high_demand(self):
        opp = {"trend_score": 3, "demand_normalized": 9, "signal_type": "newcomer"}
        assert classify_opportunity(opp) == "rising"

    def test_boundary_hot(self):
        opp = {"trend_score": 6, "demand_normalized": 6, "signal_type": ""}
        assert classify_opportunity(opp) == "hot"

    def test_boundary_high_demand(self):
        opp = {"trend_score": 5, "demand_normalized": 8, "signal_type": ""}
        assert classify_opportunity(opp) == "high_demand"


# ---------------------------------------------------------------------------
# TestGenerateOpportunityReport
# ---------------------------------------------------------------------------

class TestGenerateOpportunityReport:
    def _sample_opps(self):
        return [
            {
                "category": "AI Agent",
                "gap_title": "CLI debugger",
                "opportunity_score": 8.0,
                "trend_score": 7.0,
                "demand_normalized": 9.0,
                "opportunity_type": "hot",
                "source_repo": "langchain-ai/langchain",
                "keywords": ["cli", "debugging"],
                "already_covered": False,
            },
            {
                "category": "RAG",
                "gap_title": "Vector store manager",
                "opportunity_score": 5.0,
                "trend_score": 3.0,
                "demand_normalized": 4.0,
                "opportunity_type": "rising",
                "source_repo": "new-project/vec",
                "keywords": ["vector"],
                "already_covered": False,
            },
            {
                "category": "Multi-Agent",
                "gap_title": "Orchestration tool",
                "opportunity_score": 6.0,
                "trend_score": 4.0,
                "demand_normalized": 8.5,
                "opportunity_type": "high_demand",
                "source_repo": "org/multi",
                "keywords": ["migra"],
                "already_covered": True,
            },
        ]

    def test_has_sections(self):
        report = generate_opportunity_report(
            "2026-03-28", self._sample_opps(), [], []
        )
        assert "## Hot Opportunities" in report
        assert "## Rising Opportunities" in report
        assert "## Cross-Category Patterns" in report
        assert "## High-Demand Gaps" in report
        assert "## Already Covered" in report

    def test_has_tables(self):
        report = generate_opportunity_report(
            "2026-03-28", self._sample_opps(), [], ["migra"]
        )
        assert "| Category |" in report
        assert "CLI debugger" in report
        assert "Vector store manager" in report

    def test_empty_data(self):
        report = generate_opportunity_report("2026-03-28", [], [], [])
        assert "## Hot Opportunities" in report
        assert "No hot opportunities found." in report
        assert "No rising opportunities found." in report

    def test_cross_patterns_table(self):
        patterns = [
            {"keyword": "debugging", "categories": ["A", "B", "C"], "total_count": 5}
        ]
        report = generate_opportunity_report("2026-03-28", [], patterns, [])
        assert "debugging" in report
        assert "A, B, C" in report

    def test_already_covered_shows_keyword(self):
        opps = self._sample_opps()
        report = generate_opportunity_report("2026-03-28", opps, [], ["migra"])
        assert "migra" in report


# ---------------------------------------------------------------------------
# TestRunOpportunities
# ---------------------------------------------------------------------------

class TestRunOpportunities:
    def _make_data(self, tmp_path):
        date = "2026-01-01"
        data_dir = tmp_path / "data" / date
        data_dir.mkdir(parents=True)
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir(parents=True)

        trending = {
            "date": date,
            "categories": {
                "AI Agent": [
                    {
                        "name": "langchain",
                        "full_name": "langchain-ai/langchain",
                        "surge_score": 8.0,
                        "trend_score": 7.5,
                        "signal_type": "momentum",
                    },
                    {
                        "name": "autogen",
                        "full_name": "microsoft/autogen",
                        "surge_score": 6.0,
                        "trend_score": 5.0,
                        "signal_type": "newcomer",
                    },
                ],
                "RAG": [
                    {
                        "name": "llamaindex",
                        "full_name": "run-llama/llama_index",
                        "surge_score": 4.0,
                        "trend_score": 3.0,
                        "signal_type": "momentum",
                    },
                ],
            },
        }

        gaps = {
            "AI Agent": [
                {
                    "title": "CLI debugger for chains",
                    "type": "missing_tool",
                    "demand_score": 95,
                    "keywords": ["cli", "debugging", "chain"],
                    "issue_url": "https://github.com/example/1",
                },
                {
                    "title": "Migra integration",
                    "type": "integration",
                    "demand_score": 40,
                    "keywords": ["migra", "database"],
                    "issue_url": "https://github.com/example/2",
                },
            ],
            "RAG": [
                {
                    "title": "Vector cache layer",
                    "type": "missing_tool",
                    "demand_score": 70,
                    "keywords": ["vector", "cache"],
                    "issue_url": "https://github.com/example/3",
                },
            ],
        }

        with open(data_dir / "trending.json", "w", encoding="utf-8") as f:
            json.dump(trending, f)
        with open(data_dir / "gaps.json", "w", encoding="utf-8") as f:
            json.dump(gaps, f)

        return date

    def test_loads_data(self, tmp_path, monkeypatch):
        date = self._make_data(tmp_path)
        monkeypatch.setattr(
            "src.opportunities.BASE_DIR", tmp_path
        )
        result = run_opportunities(date=date)
        assert result["date"] == date
        assert len(result["opportunities"]) == 3
        assert all("opportunity_score" in o for o in result["opportunities"])
        assert all("opportunity_type" in o for o in result["opportunities"])

        # Verify output files created
        assert (tmp_path / "data" / date / "opportunities.json").exists()
        assert (tmp_path / "reports" / f"{date}-opportunities.md").exists()

    def test_filters_portfolio(self, tmp_path, monkeypatch):
        date = self._make_data(tmp_path)
        monkeypatch.setattr(
            "src.opportunities.BASE_DIR", tmp_path
        )
        result = run_opportunities(date=date, portfolio=["migra"])
        covered = [o for o in result["opportunities"] if o["already_covered"]]
        assert len(covered) == 1
        assert "migra" in covered[0]["keywords"]

    def test_creates_output(self, tmp_path, monkeypatch):
        date = self._make_data(tmp_path)
        monkeypatch.setattr(
            "src.opportunities.BASE_DIR", tmp_path
        )
        run_opportunities(date=date)

        # Check JSON output structure
        out_path = tmp_path / "data" / date / "opportunities.json"
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "opportunities" in data
        assert "cross_category_patterns" in data
        assert data["date"] == date

        # Check report
        report_path = tmp_path / "reports" / f"{date}-opportunities.md"
        with open(report_path, "r", encoding="utf-8") as f:
            report = f.read()
        assert "## Hot Opportunities" in report

    def test_empty_portfolio_no_covered(self, tmp_path, monkeypatch):
        date = self._make_data(tmp_path)
        monkeypatch.setattr(
            "src.opportunities.BASE_DIR", tmp_path
        )
        result = run_opportunities(date=date, portfolio=[])
        covered = [o for o in result["opportunities"] if o["already_covered"]]
        assert len(covered) == 0

    def test_opportunity_scores_are_valid(self, tmp_path, monkeypatch):
        date = self._make_data(tmp_path)
        monkeypatch.setattr(
            "src.opportunities.BASE_DIR", tmp_path
        )
        result = run_opportunities(date=date)
        for opp in result["opportunities"]:
            assert opp["opportunity_score"] >= 0
            assert isinstance(opp["opportunity_score"], float)

    def test_sorted_by_score_descending(self, tmp_path, monkeypatch):
        date = self._make_data(tmp_path)
        monkeypatch.setattr(
            "src.opportunities.BASE_DIR", tmp_path
        )
        result = run_opportunities(date=date)
        scores = [o["opportunity_score"] for o in result["opportunities"]]
        assert scores == sorted(scores, reverse=True)

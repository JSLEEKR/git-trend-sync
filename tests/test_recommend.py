"""Tests for src/recommend.py"""

import pytest

from src.recommend import (
    match_trending_to_project,
    generate_comparison_table,
    generate_recommendations_report,
    _repo_ecosystem,
    _project_ecosystems,
    _is_new_entry,
    _interest_keywords,
    _repo_tokens,
)


class TestRepoEcosystem:
    def test_python(self):
        assert _repo_ecosystem({"language": "Python"}) == "python"

    def test_typescript(self):
        assert _repo_ecosystem({"language": "TypeScript"}) == "javascript"

    def test_unknown_language(self):
        assert _repo_ecosystem({"language": "Haskell"}) is None

    def test_no_language(self):
        assert _repo_ecosystem({}) is None

    def test_empty_language(self):
        assert _repo_ecosystem({"language": ""}) is None


class TestProjectEcosystems:
    def test_python_stack(self):
        profile = {"detected_stack": ["python"]}
        assert "python" in _project_ecosystems(profile)

    def test_override_takes_precedence(self):
        profile = {"detected_stack": ["python"], "tech_stack_override": ["go"]}
        ecosystems = _project_ecosystems(profile)
        assert "go" in ecosystems
        # override replaces detected_stack
        assert "python" not in ecosystems

    def test_empty_profile(self):
        assert _project_ecosystems({}) == set()


class TestIsNewEntry:
    def test_new_repo(self):
        repo = {"created_at": "2026-03-01T00:00:00Z"}
        assert _is_new_entry(repo, threshold_days=180) is True

    def test_old_repo(self):
        repo = {"created_at": "2020-01-01T00:00:00Z"}
        assert _is_new_entry(repo, threshold_days=180) is False

    def test_missing_date(self):
        assert _is_new_entry({}) is False

    def test_invalid_date(self):
        assert _is_new_entry({"created_at": "bad"}) is False


class TestInterestKeywords:
    def test_combines_sources(self, sample_profile):
        kws = _interest_keywords(sample_profile)
        assert "rag" in kws
        assert "langchain" in kws

    def test_empty_profile(self):
        kws = _interest_keywords({})
        assert kws == []


class TestRepoTokens:
    def test_extracts_tokens(self, sample_repo):
        tokens = _repo_tokens(sample_repo)
        assert "langchain" in tokens
        assert "llm" in tokens


class TestMatchTrendingToProject:
    def test_basic_matching(self, sample_trending_data, sample_profile):
        candidates = match_trending_to_project(sample_trending_data, sample_profile)
        assert isinstance(candidates, list)
        for c in candidates:
            assert "_match_score" in c
            assert c["_match_score"] >= 2

    def test_excluded_repos(self, sample_trending_data, sample_profile):
        sample_profile["exclude"] = ["python"]
        candidates = match_trending_to_project(sample_trending_data, sample_profile)
        # Python repos should be excluded
        for c in candidates:
            assert _repo_ecosystem(c) != "python"

    def test_empty_trending(self, sample_profile):
        trending = {"categories": {}}
        candidates = match_trending_to_project(trending, sample_profile)
        assert candidates == []

    def test_max_15_results(self, sample_profile):
        # Build 20 compatible repos
        repos = []
        for i in range(20):
            repos.append({
                "name": f"langchain-{i}",
                "full_name": f"o/langchain-{i}",
                "description": "LLM framework for RAG agent",
                "language": "Python",
                "topics": ["llm", "rag", "agent"],
                "created_at": "2025-01-01T00:00:00Z",
                "stars": 5000,
            })
        trending = {"categories": {"Test": repos}}
        candidates = match_trending_to_project(trending, sample_profile)
        assert len(candidates) <= 15


class TestGenerateComparisonTable:
    def test_generates_table(self, sample_profile):
        candidates = [
            {
                "name": "repo1",
                "description": "A rag vector agent tool",
                "language": "Python",
                "license": "MIT",
                "topics": ["rag"],
                "stars": 1000,
                "recent_commits_30d": 50,
            },
        ]
        table = generate_comparison_table(candidates, sample_profile)
        assert "## Feature Comparison" in table
        assert "repo1" in table

    def test_empty_candidates(self, sample_profile):
        table = generate_comparison_table([], sample_profile)
        assert table == ""


class TestGenerateRecommendationsReport:
    def test_basic_report(self, sample_profile):
        recommendations = [
            {
                "name": "cool-tool",
                "url": "https://github.com/o/cool-tool",
                "description": "A useful tool",
                "relevance": "high",
                "why": "Stack match",
                "how_to_evaluate": "Try it out",
                "effort": "small",
            },
        ]
        report = generate_recommendations_report("2025-03-28", sample_profile, recommendations)
        assert "# AI Trend Recommendations" in report
        assert "cool-tool" in report
        assert "High Relevance" in report

    def test_empty_recommendations(self, sample_profile):
        report = generate_recommendations_report("2025-03-28", sample_profile, [])
        assert "No actionable recommendations" in report

    def test_all_relevance_levels(self, sample_profile):
        recs = [
            {"name": "a", "url": "", "description": "", "relevance": "high", "why": "", "how_to_evaluate": "", "effort": ""},
            {"name": "b", "url": "", "description": "", "relevance": "watch", "why": "", "how_to_evaluate": "", "effort": ""},
            {"name": "c", "url": "", "description": "", "relevance": "new_entrant", "why": "", "how_to_evaluate": "", "effort": ""},
        ]
        report = generate_recommendations_report("2025-03-28", sample_profile, recs)
        assert "High Relevance" in report
        assert "Worth Watching" in report
        assert "New Entrants" in report

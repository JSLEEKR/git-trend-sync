"""Common fixtures for git-trend-sync tests."""

import pytest


@pytest.fixture
def sample_repo():
    """A single repo dict as returned by extract_repo_data."""
    return {
        "name": "langchain",
        "full_name": "langchain-ai/langchain",
        "url": "https://github.com/langchain-ai/langchain",
        "description": "Build context-aware reasoning applications",
        "language": "Python",
        "license": "MIT",
        "stars": 50000,
        "forks": 8000,
        "open_issues": 200,
        "created_at": "2022-10-01T00:00:00Z",
        "updated_at": "2025-03-28T00:00:00Z",
        "pushed_at": "2025-03-28T00:00:00Z",
        "topics": ["llm", "ai", "langchain"],
        "recent_commits_30d": 150,
        "recent_commits_7d": 60,
        "readme_excerpt": "# LangChain\nBuild context-aware reasoning applications.",
    }


@pytest.fixture
def sample_repo_2():
    """A second repo dict for testing with multiple repos."""
    return {
        "name": "autogen",
        "full_name": "microsoft/autogen",
        "url": "https://github.com/microsoft/autogen",
        "description": "Multi-agent framework",
        "language": "Python",
        "license": "MIT",
        "stars": 20000,
        "forks": 3000,
        "open_issues": 100,
        "created_at": "2023-06-01T00:00:00Z",
        "updated_at": "2025-03-27T00:00:00Z",
        "pushed_at": "2025-03-27T00:00:00Z",
        "topics": ["agent", "multi-agent", "ai"],
        "recent_commits_30d": 80,
        "recent_commits_7d": 45,
        "readme_excerpt": "# AutoGen\nMulti-agent conversations.",
    }


@pytest.fixture
def sample_newcomer_repo():
    """A newcomer repo (< 180 days old) for testing newcomer signal."""
    return {
        "name": "new-hotness",
        "full_name": "startup/new-hotness",
        "url": "https://github.com/startup/new-hotness",
        "description": "The next big thing in AI",
        "language": "Python",
        "license": "MIT",
        "stars": 3000,
        "forks": 200,
        "open_issues": 15,
        "created_at": "2026-03-01T00:00:00Z",
        "updated_at": "2026-03-28T00:00:00Z",
        "pushed_at": "2026-03-28T00:00:00Z",
        "topics": ["ai", "ml"],
        "recent_commits_30d": 200,
        "recent_commits_7d": 150,
        "readme_excerpt": "# New Hotness\nThe next big thing.",
    }


@pytest.fixture
def sample_raw_data(sample_repo, sample_repo_2, sample_newcomer_repo):
    """Raw data dict as returned by collect_all."""
    return {
        "date": "2025-03-28",
        "categories": {
            "AI Agent Framework": [sample_repo, sample_repo_2, sample_newcomer_repo],
        },
    }


@pytest.fixture
def sample_trending_data(sample_repo, sample_repo_2):
    """Trending data dict as returned by compute_scores."""
    return {
        "date": "2025-03-28",
        "categories": {
            "AI Agent Framework": [
                {
                    **sample_repo,
                    "trend_score": 10.0,
                    "surge_score": 10.0,
                    "newcomer_score": 0.0,
                    "momentum_score": 10.0,
                    "surge_ratio": 2.0,
                    "stars_per_day_avg": 55.6,
                    "age_days": 900,
                    "signal_type": "surge",
                    "is_new_entry": True,
                },
                {
                    **sample_repo_2,
                    "trend_score": 5.0,
                    "surge_score": 5.0,
                    "newcomer_score": 0.0,
                    "momentum_score": 5.0,
                    "surge_ratio": 1.5,
                    "stars_per_day_avg": 30.0,
                    "age_days": 665,
                    "signal_type": "surge",
                    "is_new_entry": False,
                },
            ],
        },
    }


@pytest.fixture
def sample_profile():
    """A project profile as returned by scan_project."""
    return {
        "name": "my-ai-project",
        "description": "An AI-powered application",
        "detected_stack": ["python"],
        "detected_frameworks": ["langchain", "fastapi"],
        "declared_interests": ["rag", "agent"],
        "exclude": [],
        "current_dependencies": ["langchain", "fastapi", "openai", "chromadb"],
        "architecture_hints": ["uses LLM framework (langchain)", "has API endpoints (fastapi)"],
        "tech_stack_override": [],
    }


@pytest.fixture
def sample_analysis():
    """A sample analysis dict as returned by Claude Code."""
    return {
        "individual_analysis": [
            {
                "name": "langchain",
                "pros": ["Large community", "Well documented"],
                "cons": ["Complex API", "Frequent breaking changes"],
            },
        ],
        "good_combinations": [
            {
                "repos": ["langchain", "chromadb"],
                "reason": "Natural RAG stack",
            },
        ],
        "bad_combinations": [
            {
                "repos": ["langchain", "llama-index"],
                "reason": "Overlapping functionality",
            },
        ],
        "ranking": [
            {
                "rank": 1,
                "name": "langchain",
                "justification": "Most versatile framework",
            },
        ],
    }

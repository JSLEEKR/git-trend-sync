"""Tests for src/scan_project.py"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.scan_project import (
    scan_project,
    recommend_categories,
    _extract_python_deps_from_requirements,
    _extract_js_deps_from_package_json,
    _extract_go_deps_from_go_mod,
    _extract_python_deps_from_pyproject,
)


class TestExtractPythonDeps:
    def test_requirements_txt(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("fastapi>=0.100\nlangchain\nopenai==1.0\n# comment\n\n")
        deps = _extract_python_deps_from_requirements(req)
        assert "fastapi" in deps
        assert "langchain" in deps
        assert "openai" in deps

    def test_requirements_with_extras(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("fastapi[all]>=0.100\n")
        deps = _extract_python_deps_from_requirements(req)
        assert "fastapi" in deps

    def test_requirements_with_env_markers(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text('pywin32; sys_platform == "win32"\n')
        deps = _extract_python_deps_from_requirements(req)
        assert "pywin32" in deps

    def test_empty_file(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("")
        deps = _extract_python_deps_from_requirements(req)
        assert deps == []

    def test_missing_file(self, tmp_path):
        req = tmp_path / "nonexistent.txt"
        deps = _extract_python_deps_from_requirements(req)
        assert deps == []


class TestExtractJsDeps:
    def test_package_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({
            "dependencies": {"react": "^18.0", "next": "^14.0"},
            "devDependencies": {"typescript": "^5.0"},
        }))
        deps = _extract_js_deps_from_package_json(pkg)
        assert "react" in deps
        assert "next" in deps
        assert "typescript" in deps

    def test_empty_package_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text("{}")
        deps = _extract_js_deps_from_package_json(pkg)
        assert deps == []

    def test_malformed_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text("not json")
        deps = _extract_js_deps_from_package_json(pkg)
        assert deps == []


class TestExtractGoDeps:
    def test_go_mod(self, tmp_path):
        go_mod = tmp_path / "go.mod"
        go_mod.write_text(
            "module example.com/mymod\n\ngo 1.21\n\n"
            "require (\n\tgithub.com/gin-gonic/gin v1.9.0\n\tgithub.com/lib/pq v1.10.0\n)\n"
        )
        deps = _extract_go_deps_from_go_mod(go_mod)
        assert "github.com/gin-gonic/gin" in deps
        assert "github.com/lib/pq" in deps

    def test_single_require(self, tmp_path):
        go_mod = tmp_path / "go.mod"
        go_mod.write_text("module example.com/m\n\nrequire github.com/pkg/errors v0.9.1\n")
        deps = _extract_go_deps_from_go_mod(go_mod)
        assert "github.com/pkg/errors" in deps

    def test_empty_go_mod(self, tmp_path):
        go_mod = tmp_path / "go.mod"
        go_mod.write_text("module example.com/m\n\ngo 1.21\n")
        deps = _extract_go_deps_from_go_mod(go_mod)
        assert deps == []


class TestScanProject:
    def test_python_project(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\nlangchain\n")
        (tmp_path / "README.md").write_text("# My Project\n\nA cool project.\n")
        profile = scan_project(str(tmp_path))
        assert "python" in profile["detected_stack"]
        assert "fastapi" in profile["current_dependencies"]
        assert "langchain" in profile["current_dependencies"]
        assert profile["description"] != ""

    def test_js_project(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "name": "my-app",
            "dependencies": {"react": "^18.0"},
        }))
        profile = scan_project(str(tmp_path))
        assert "javascript" in profile["detected_stack"]
        assert profile["name"] == "my-app"

    def test_typescript_project(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"name": "ts-app"}))
        (tmp_path / "tsconfig.json").write_text("{}")
        profile = scan_project(str(tmp_path))
        assert "typescript" in profile["detected_stack"]
        assert "javascript" in profile["detected_stack"]

    def test_empty_project(self, tmp_path):
        profile = scan_project(str(tmp_path))
        assert profile["detected_stack"] == []
        assert profile["current_dependencies"] == []
        assert profile["name"] == tmp_path.name


class TestRecommendCategories:
    def test_llm_deps(self):
        profile = {"current_dependencies": ["langchain"], "declared_interests": [], "detected_frameworks": [], "architecture_hints": []}
        cats = recommend_categories(profile)
        assert "RAG Framework" in cats
        assert "AI Agent Framework" in cats

    def test_web_deps(self):
        profile = {"current_dependencies": ["fastapi"], "declared_interests": [], "detected_frameworks": [], "architecture_hints": []}
        cats = recommend_categories(profile)
        assert "AI Workflow" in cats

    def test_agent_deps(self):
        profile = {"current_dependencies": ["crewai"], "declared_interests": [], "detected_frameworks": [], "architecture_hints": []}
        cats = recommend_categories(profile)
        assert "Multi-Agent" in cats

    def test_voice_interest(self):
        profile = {"current_dependencies": [], "declared_interests": ["voice"], "detected_frameworks": [], "architecture_hints": []}
        cats = recommend_categories(profile)
        assert "Voice Agent" in cats

    def test_empty_profile(self):
        profile = {"current_dependencies": [], "declared_interests": [], "detected_frameworks": [], "architecture_hints": []}
        cats = recommend_categories(profile)
        assert cats == []

    def test_mcp_interest(self):
        profile = {"current_dependencies": [], "declared_interests": ["mcp"], "detected_frameworks": [], "architecture_hints": []}
        cats = recommend_categories(profile)
        assert "MCP" in cats

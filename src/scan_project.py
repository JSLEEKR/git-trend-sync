"""
scan_project.py — project context scanner for ai-trend

Scans a project directory to detect its tech stack, frameworks, dependencies,
and architecture patterns. Optionally reads an ai-trend.yaml config file.
"""

import json
import sys
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Detection mappings
# ---------------------------------------------------------------------------

# Maps dependency names (lowercased) to architecture hints
ARCHITECTURE_HINTS_MAP = {
    # LLM frameworks
    "langchain": "uses LLM framework (langchain)",
    "langchain-core": "uses LLM framework (langchain)",
    "langchain-community": "uses LLM framework (langchain)",
    "llama-index": "uses LLM framework (llama-index)",
    "llama_index": "uses LLM framework (llama-index)",
    "openai": "calls OpenAI API",
    "anthropic": "calls Anthropic API",
    "google-generativeai": "calls Google Generative AI API",
    "cohere": "calls Cohere API",
    "transformers": "uses HuggingFace Transformers",
    "sentence-transformers": "uses sentence embeddings",
    "haystack-ai": "uses Haystack LLM framework",
    "haystack": "uses Haystack LLM framework",
    # Vector stores
    "chromadb": "uses vector store (chroma)",
    "pinecone-client": "uses vector store (pinecone)",
    "pinecone": "uses vector store (pinecone)",
    "weaviate-client": "uses vector store (weaviate)",
    "qdrant-client": "uses vector store (qdrant)",
    "faiss-cpu": "uses vector store (faiss)",
    "faiss-gpu": "uses vector store (faiss)",
    "faiss": "uses vector store (faiss)",
    "milvus": "uses vector store (milvus)",
    "pymilvus": "uses vector store (milvus)",
    "lancedb": "uses vector store (lancedb)",
    "pgvector": "uses vector store (pgvector)",
    # Agent frameworks
    "autogen": "uses agent framework (autogen)",
    "crewai": "uses agent framework (crewai)",
    "phidata": "uses agent framework (phidata)",
    "agentops": "uses agent observability",
    "dspy-ai": "uses DSPy agent framework",
    "dspy": "uses DSPy agent framework",
    # Web frameworks (Python)
    "fastapi": "has API endpoints (fastapi)",
    "flask": "has API endpoints (flask)",
    "django": "has API endpoints (django)",
    "starlette": "has API endpoints (starlette)",
    "aiohttp": "has async HTTP server",
    "tornado": "has async HTTP server",
    # Web frameworks (JS/TS)
    "express": "has API endpoints (express)",
    "next": "has Next.js frontend",
    "nextjs": "has Next.js frontend",
    "nuxt": "has Nuxt.js frontend",
    "react": "has React frontend",
    "vue": "has Vue.js frontend",
    "angular": "has Angular frontend",
    "svelte": "has Svelte frontend",
    "remix": "has Remix frontend",
    # Databases / ORMs
    "sqlalchemy": "uses relational database (sqlalchemy)",
    "alembic": "uses relational database migrations",
    "tortoise-orm": "uses relational database (tortoise)",
    "prisma": "uses relational database (prisma)",
    "mongoose": "uses MongoDB",
    "pymongo": "uses MongoDB",
    "motor": "uses MongoDB (async)",
    "redis": "uses Redis",
    "aioredis": "uses Redis (async)",
    "celery": "uses task queue (celery)",
    "dramatiq": "uses task queue (dramatiq)",
    # Streaming / messaging
    "kafka-python": "uses message streaming (kafka)",
    "confluent-kafka": "uses message streaming (kafka)",
    "pika": "uses message queue (rabbitmq)",
    # ML / data science
    "torch": "uses PyTorch",
    "pytorch": "uses PyTorch",
    "tensorflow": "uses TensorFlow",
    "keras": "uses Keras / TensorFlow",
    "scikit-learn": "uses scikit-learn",
    "sklearn": "uses scikit-learn",
    "pandas": "uses data processing (pandas)",
    "numpy": "uses numerical computing (numpy)",
    "xgboost": "uses gradient boosting (xgboost)",
    "lightgbm": "uses gradient boosting (lightgbm)",
    # Observability / MLOps
    "mlflow": "uses MLflow experiment tracking",
    "wandb": "uses Weights & Biases tracking",
    "prefect": "uses Prefect orchestration",
    "airflow": "uses Airflow orchestration",
    "apache-airflow": "uses Airflow orchestration",
    "dvc": "uses DVC data versioning",
}

# Maps dependency names to human-readable framework labels
FRAMEWORK_LABELS_MAP = {
    "langchain": "langchain",
    "langchain-core": "langchain",
    "langchain-community": "langchain",
    "llama-index": "llama-index",
    "llama_index": "llama-index",
    "openai": "openai",
    "anthropic": "anthropic",
    "transformers": "transformers",
    "sentence-transformers": "sentence-transformers",
    "haystack-ai": "haystack",
    "chromadb": "chromadb",
    "pinecone-client": "pinecone",
    "pinecone": "pinecone",
    "weaviate-client": "weaviate",
    "qdrant-client": "qdrant",
    "faiss-cpu": "faiss",
    "faiss-gpu": "faiss",
    "faiss": "faiss",
    "milvus": "milvus",
    "pymilvus": "milvus",
    "lancedb": "lancedb",
    "autogen": "autogen",
    "crewai": "crewai",
    "dspy-ai": "dspy",
    "dspy": "dspy",
    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",
    "starlette": "starlette",
    "express": "express",
    "react": "react",
    "vue": "vue",
    "angular": "angular",
    "next": "nextjs",
    "svelte": "svelte",
    "torch": "pytorch",
    "tensorflow": "tensorflow",
    "keras": "keras",
    "scikit-learn": "scikit-learn",
    "mlflow": "mlflow",
    "wandb": "wandb",
    "prefect": "prefect",
    "celery": "celery",
}

# Maps file names to detected tech stacks
STACK_INDICATORS = {
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "Pipfile": "python",
    "package.json": "javascript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
    "*.csproj": "csharp",
    "*.fsproj": "fsharp",
    "composer.json": "php",
    "Gemfile": "ruby",
    "mix.exs": "elixir",
    "build.sbt": "scala",
}


# ---------------------------------------------------------------------------
# Dependency extraction helpers
# ---------------------------------------------------------------------------

def _extract_python_deps_from_requirements(path: Path) -> list[str]:
    """Parse a requirements.txt file and return package names (lowercased)."""
    deps = []
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip version specifiers and extras: e.g. "fastapi[all]>=0.100"
            name = line.split(";")[0].strip()  # drop environment markers
            name = name.split("[")[0].strip()   # drop extras
            for op in (">=", "<=", "!=", "==", "~=", ">", "<"):
                name = name.split(op)[0].strip()
            if name:
                deps.append(name.lower())
    except OSError:
        pass
    return deps


def _extract_python_deps_from_pyproject(path: Path) -> list[str]:
    """Parse pyproject.toml (PEP 621 or poetry) and return dependency names."""
    deps = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore"))
        if not isinstance(data, dict):
            return deps
        # PEP 621: project.dependencies
        project = data.get("project", {}) or {}
        for dep in project.get("dependencies", []):
            name = str(dep).split(";")[0].split("[")[0]
            for op in (">=", "<=", "!=", "==", "~=", ">", "<", " "):
                name = name.split(op)[0]
            name = name.strip().lower()
            if name:
                deps.append(name)
        # Poetry: tool.poetry.dependencies
        poetry = (data.get("tool", {}) or {}).get("poetry", {}) or {}
        for name in poetry.get("dependencies", {}).keys():
            if name.lower() != "python":
                deps.append(name.lower())
        for name in poetry.get("dev-dependencies", {}).keys():
            deps.append(name.lower())
    except Exception:
        pass
    return deps


def _extract_js_deps_from_package_json(path: Path) -> list[str]:
    """Parse package.json and return dependency names (lowercased)."""
    deps = []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name in (data.get(section) or {}).keys():
                deps.append(name.lower())
    except Exception:
        pass
    return deps


def _extract_go_deps_from_go_mod(path: Path) -> list[str]:
    """Parse go.mod and return module paths (lowercased)."""
    deps = []
    try:
        in_require = False
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if in_require:
                if stripped == ")":
                    in_require = False
                    continue
                parts = stripped.split()
                if parts:
                    deps.append(parts[0].lower())
            elif stripped.startswith("require "):
                parts = stripped.split()
                if len(parts) >= 2:
                    deps.append(parts[1].lower())
    except OSError:
        pass
    return deps


def _extract_rust_deps_from_cargo_toml(path: Path) -> list[str]:
    """Parse Cargo.toml and return crate names (lowercased)."""
    deps = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore"))
        if not isinstance(data, dict):
            return deps
        for section in ("dependencies", "dev-dependencies", "build-dependencies"):
            for name in (data.get(section) or {}).keys():
                deps.append(name.lower())
    except Exception:
        pass
    return deps


def _extract_java_deps_from_pom_xml(path: Path) -> list[str]:
    """Parse pom.xml and return artifactId values (lowercased)."""
    deps = []
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(str(path))
        root = tree.getroot()
        ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
        for dep in root.iter(f"{ns}dependency"):
            artifact = dep.find(f"{ns}artifactId")
            if artifact is not None and artifact.text:
                deps.append(artifact.text.strip().lower())
    except Exception:
        pass
    return deps


def _extract_java_deps_from_build_gradle(path: Path) -> list[str]:
    """Parse build.gradle / build.gradle.kts and return dependency names (lowercased)."""
    deps = []
    try:
        import re
        content = path.read_text(encoding="utf-8", errors="ignore")
        # Match: implementation 'group:artifact:version' or "group:artifact:version"
        for match in re.finditer(r"""['"]([A-Za-z0-9._\-]+):([A-Za-z0-9._\-]+):[^'"]+['"]""", content):
            deps.append(match.group(2).lower())
    except Exception:
        pass
    return deps


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def scan_project(project_path: str) -> dict:
    """
    Scan a project directory and return a profile dict describing its
    tech stack, frameworks, dependencies, and architecture patterns.

    Parameters
    ----------
    project_path:
        Absolute or relative path to the project root.

    Returns
    -------
    dict with keys:
        name, description, detected_stack, detected_frameworks,
        declared_interests, exclude, current_dependencies,
        architecture_hints, tech_stack_override
    """
    root = Path(project_path).resolve()

    # ------------------------------------------------------------------
    # 1. Detect tech stack from presence of well-known manifest files
    # ------------------------------------------------------------------
    detected_stack: list[str] = []

    # Direct filename matches
    direct_map = {k: v for k, v in STACK_INDICATORS.items() if not k.startswith("*")}
    for filename, lang in direct_map.items():
        if (root / filename).exists() and lang not in detected_stack:
            detected_stack.append(lang)

    # TypeScript is a superset of JS — detect via tsconfig.json
    if (root / "tsconfig.json").exists() and "typescript" not in detected_stack:
        detected_stack.append("typescript")
        if "javascript" not in detected_stack:
            detected_stack.append("javascript")

    # Glob-based matches (e.g. *.csproj)
    glob_map = {k: v for k, v in STACK_INDICATORS.items() if k.startswith("*")}
    for pattern, lang in glob_map.items():
        if any(root.glob(pattern)) and lang not in detected_stack:
            detected_stack.append(lang)

    # ------------------------------------------------------------------
    # 2. Collect all dependencies from manifest files
    # ------------------------------------------------------------------
    all_deps: list[str] = []

    req_txt = root / "requirements.txt"
    if req_txt.exists():
        all_deps.extend(_extract_python_deps_from_requirements(req_txt))

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        all_deps.extend(_extract_python_deps_from_pyproject(pyproject))

    pkg_json = root / "package.json"
    if pkg_json.exists():
        all_deps.extend(_extract_js_deps_from_package_json(pkg_json))

    go_mod = root / "go.mod"
    if go_mod.exists():
        all_deps.extend(_extract_go_deps_from_go_mod(go_mod))

    cargo_toml = root / "Cargo.toml"
    if cargo_toml.exists():
        all_deps.extend(_extract_rust_deps_from_cargo_toml(cargo_toml))

    pom_xml = root / "pom.xml"
    if pom_xml.exists():
        all_deps.extend(_extract_java_deps_from_pom_xml(pom_xml))

    for gradle_file in ("build.gradle", "build.gradle.kts"):
        gradle_path = root / gradle_file
        if gradle_path.exists():
            all_deps.extend(_extract_java_deps_from_build_gradle(gradle_path))

    # Deduplicate while preserving order
    seen: set[str] = set()
    current_dependencies: list[str] = []
    for dep in all_deps:
        if dep not in seen:
            seen.add(dep)
            current_dependencies.append(dep)

    # ------------------------------------------------------------------
    # 3. Detect frameworks and architecture hints from dependencies
    # ------------------------------------------------------------------
    detected_frameworks: list[str] = []
    architecture_hints: list[str] = []

    seen_frameworks: set[str] = set()
    seen_hints: set[str] = set()

    for dep in current_dependencies:
        framework = FRAMEWORK_LABELS_MAP.get(dep)
        if framework and framework not in seen_frameworks:
            seen_frameworks.add(framework)
            detected_frameworks.append(framework)

        hint = ARCHITECTURE_HINTS_MAP.get(dep)
        if hint and hint not in seen_hints:
            seen_hints.add(hint)
            architecture_hints.append(hint)

    # ------------------------------------------------------------------
    # 4. Read project description from README.md
    # ------------------------------------------------------------------
    description = ""
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme_path = root / readme_name
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="ignore")
                # Use the first non-empty paragraph as the description
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                # Skip lines that are pure markdown headings or badges
                for para in paragraphs:
                    lines = [l for l in para.splitlines() if l.strip()]
                    # Skip if all lines are headings or badge lines
                    meaningful = [
                        l for l in lines
                        if not l.startswith("#")
                        and not l.startswith("![")
                        and not l.startswith("[![")
                        and not l.startswith("---")
                    ]
                    if meaningful:
                        description = " ".join(meaningful[:3])
                        break
            except OSError:
                pass
            break

    # ------------------------------------------------------------------
    # 5. Determine project name
    # ------------------------------------------------------------------
    name = root.name  # default: directory name

    # Try package.json "name" field
    if pkg_json.exists():
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(pkg_data, dict) and pkg_data.get("name"):
                name = pkg_data["name"]
        except Exception:
            pass

    # Try pyproject.toml project.name
    if pyproject.exists():
        try:
            pdata = yaml.safe_load(pyproject.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(pdata, dict):
                proj_name = (pdata.get("project") or {}).get("name")
                if not proj_name:
                    proj_name = ((pdata.get("tool") or {}).get("poetry") or {}).get("name")
                if proj_name:
                    name = proj_name
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 6. Load optional ai-trend.yaml config
    # ------------------------------------------------------------------
    declared_interests: list[str] = []
    exclude: list[str] = []
    tech_stack_override: list[str] = []

    ai_trend_config_path = root / "ai-trend.yaml"
    if not ai_trend_config_path.exists():
        ai_trend_config_path = root / "ai-trend.yml"

    if ai_trend_config_path.exists():
        try:
            config_data = yaml.safe_load(
                ai_trend_config_path.read_text(encoding="utf-8", errors="ignore")
            )
            if isinstance(config_data, dict):
                declared_interests = list(config_data.get("interests", []) or [])
                exclude = list(config_data.get("exclude", []) or [])
                tech_stack_override = list(config_data.get("tech_stack_override", []) or [])

                # Allow config to override name / description
                if config_data.get("name"):
                    name = str(config_data["name"])
                if config_data.get("description"):
                    description = str(config_data["description"])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 7. Assemble final profile
    # ------------------------------------------------------------------
    return {
        "name": name,
        "description": description,
        "detected_stack": detected_stack,
        "detected_frameworks": detected_frameworks,
        "declared_interests": declared_interests,
        "exclude": exclude,
        "current_dependencies": current_dependencies,
        "architecture_hints": architecture_hints,
        "tech_stack_override": tech_stack_override,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else "."
    profile = scan_project(path_arg)
    print(json.dumps(profile, indent=2))

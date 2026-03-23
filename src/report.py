"""
분석 결과를 한국어/영어 마크다운 리포트로 생성합니다.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "categories.yaml"


def load_categories_config() -> dict:
    """Load category config for Korean names."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cats = yaml.safe_load(f)["categories"]
    return {c["name"]: c.get("name_ko", c["name"]) for c in cats}


def extract_json_from_text(text: str) -> dict | None:
    """Try to extract JSON from Claude Code output text."""
    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find JSON block in markdown
    patterns = [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
        r'\{.*\}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if match.lastindex else match.group(0))
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def load_analysis(analysis_dir: Path, category: str) -> dict | None:
    """Load analysis result for a category."""
    safe_name = category.lower().replace(" ", "_")
    path = analysis_dir / f"{safe_name}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Claude Code --output-format json wraps in {"result": "..."}
    data = extract_json_from_text(content)
    if data and "result" in data:
        return extract_json_from_text(data["result"])
    return data


def score_bar(score: float) -> str:
    """Create a visual score bar."""
    filled = round(score)
    return "█" * filled + "░" * (10 - filled)


def generate_en_report(date: str, metrics: dict, analyses: dict) -> str:
    """Generate English markdown report."""
    lines = [
        f"# AI Agent Trend Report — {date}",
        "",
        f"> Auto-generated on {date}. Repositories sourced from GitHub Topics, "
        "ranked by stars. Qualitative analysis powered by Claude Code.",
        "",
        "## Table of Contents",
        "",
    ]

    # TOC
    for cat_name in metrics["categories"]:
        anchor = cat_name.lower().replace(" ", "-")
        lines.append(f"- [{cat_name}](#{anchor})")
    lines.append("- [Cross-Category Insights](#cross-category-insights)")
    lines.append("")

    # Per-category sections
    for cat_name, repos in metrics["categories"].items():
        lines.append(f"## {cat_name}")
        lines.append("")

        # Metrics table
        lines.append("### Quantitative Metrics")
        lines.append("")
        lines.append("| Rank | Repository | Stars | Activity | Community | Growth | Overall |")
        lines.append("|------|-----------|-------|----------|-----------|--------|---------|")

        for i, r in enumerate(repos, 1):
            s = r["scores"]
            lines.append(
                f"| {i} | [{r['name']}]({r['url']}) | "
                f"{score_bar(s['popularity'])} {s['popularity']} | "
                f"{score_bar(s['activity'])} {s['activity']} | "
                f"{score_bar(s['community_health'])} {s['community_health']} | "
                f"{score_bar(s['growth'])} {s['growth']} | "
                f"**{s['overall']}** |"
            )
        lines.append("")

        # Qualitative analysis
        analysis = analyses.get(cat_name)
        if analysis and "error" not in analysis:
            # Individual analysis
            if "individual_analysis" in analysis:
                lines.append("### Individual Analysis")
                lines.append("")
                for item in analysis["individual_analysis"]:
                    lines.append(f"#### {item['name']}")
                    lines.append("")
                    lines.append("**Pros:**")
                    for pro in item.get("pros", []):
                        lines.append(f"- {pro}")
                    lines.append("")
                    lines.append("**Cons:**")
                    for con in item.get("cons", []):
                        lines.append(f"- {con}")
                    lines.append("")

            # Good combinations
            if "good_combinations" in analysis:
                lines.append("### Recommended Combinations")
                lines.append("")
                for combo in analysis["good_combinations"]:
                    repos_str = " + ".join(combo["repos"])
                    lines.append(f"- **{repos_str}**: {combo['reason']}")
                lines.append("")

            # Bad combinations
            if "bad_combinations" in analysis:
                lines.append("### Avoid Combining")
                lines.append("")
                for combo in analysis["bad_combinations"]:
                    repos_str = " + ".join(combo["repos"])
                    lines.append(f"- **{repos_str}**: {combo['reason']}")
                lines.append("")

            # Ranking
            if "ranking" in analysis:
                lines.append("### Ranking")
                lines.append("")
                for item in analysis["ranking"]:
                    lines.append(f"{item['rank']}. **{item['name']}** — {item['justification']}")
                lines.append("")
        else:
            lines.append("*Qualitative analysis not available for this category.*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Cross-category insights
    lines.append("## Cross-Category Insights")
    lines.append("")
    lines.append("### Top Repositories Across All Categories")
    lines.append("")

    all_repos = []
    for cat_name, repos in metrics["categories"].items():
        for r in repos:
            all_repos.append({**r, "category": cat_name})
    all_repos.sort(key=lambda x: x["scores"]["overall"], reverse=True)

    lines.append("| Rank | Repository | Category | Overall Score |")
    lines.append("|------|-----------|----------|---------------|")
    for i, r in enumerate(all_repos[:10], 1):
        lines.append(f"| {i} | [{r['name']}]({r['url']}) | {r['category']} | **{r['scores']['overall']}** |")
    lines.append("")

    return "\n".join(lines)


def generate_ko_report(date: str, metrics: dict, analyses: dict) -> str:
    """Generate Korean markdown report."""
    cat_names_ko = load_categories_config()

    lines = [
        f"# AI 에이전트 트렌드 리포트 — {date}",
        "",
        f"> {date} 자동 생성. GitHub Topics 기준 스타 순 정렬. "
        "정성 분석은 Claude Code 기반.",
        "",
        "## 목차",
        "",
    ]

    for cat_name in metrics["categories"]:
        ko_name = cat_names_ko.get(cat_name, cat_name)
        anchor = cat_name.lower().replace(" ", "-")
        lines.append(f"- [{ko_name}](#{anchor})")
    lines.append("- [전체 카테고리 인사이트](#cross-category-insights)")
    lines.append("")

    for cat_name, repos in metrics["categories"].items():
        ko_name = cat_names_ko.get(cat_name, cat_name)
        lines.append(f"## {ko_name}")
        lines.append("")

        lines.append("### 정량 메트릭")
        lines.append("")
        lines.append("| 순위 | 레포지토리 | 인기도 | 활성도 | 커뮤니티 | 성장세 | 종합 |")
        lines.append("|------|-----------|--------|--------|----------|--------|------|")

        for i, r in enumerate(repos, 1):
            s = r["scores"]
            lines.append(
                f"| {i} | [{r['name']}]({r['url']}) | "
                f"{score_bar(s['popularity'])} {s['popularity']} | "
                f"{score_bar(s['activity'])} {s['activity']} | "
                f"{score_bar(s['community_health'])} {s['community_health']} | "
                f"{score_bar(s['growth'])} {s['growth']} | "
                f"**{s['overall']}** |"
            )
        lines.append("")

        analysis = analyses.get(cat_name)
        if analysis and "error" not in analysis:
            if "individual_analysis" in analysis:
                lines.append("### 개별 분석")
                lines.append("")
                for item in analysis["individual_analysis"]:
                    lines.append(f"#### {item['name']}")
                    lines.append("")
                    lines.append("**장점:**")
                    for pro in item.get("pros", []):
                        lines.append(f"- {pro}")
                    lines.append("")
                    lines.append("**단점:**")
                    for con in item.get("cons", []):
                        lines.append(f"- {con}")
                    lines.append("")

            if "good_combinations" in analysis:
                lines.append("### 추천 조합")
                lines.append("")
                for combo in analysis["good_combinations"]:
                    repos_str = " + ".join(combo["repos"])
                    lines.append(f"- **{repos_str}**: {combo['reason']}")
                lines.append("")

            if "bad_combinations" in analysis:
                lines.append("### 비추천 조합")
                lines.append("")
                for combo in analysis["bad_combinations"]:
                    repos_str = " + ".join(combo["repos"])
                    lines.append(f"- **{repos_str}**: {combo['reason']}")
                lines.append("")

            if "ranking" in analysis:
                lines.append("### 순위")
                lines.append("")
                for item in analysis["ranking"]:
                    lines.append(f"{item['rank']}. **{item['name']}** — {item['justification']}")
                lines.append("")
        else:
            lines.append("*이 카테고리의 정성 분석을 사용할 수 없습니다.*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Cross-category
    lines.append("## 전체 카테고리 인사이트")
    lines.append("")
    lines.append("### 전체 카테고리 상위 레포지토리")
    lines.append("")

    all_repos = []
    for cat_name, repos in metrics["categories"].items():
        for r in repos:
            all_repos.append({**r, "category": cat_names_ko.get(cat_name, cat_name)})
    all_repos.sort(key=lambda x: x["scores"]["overall"], reverse=True)

    lines.append("| 순위 | 레포지토리 | 카테고리 | 종합 점수 |")
    lines.append("|------|-----------|----------|-----------|")
    for i, r in enumerate(all_repos[:10], 1):
        lines.append(f"| {i} | [{r['name']}]({r['url']}) | {r['category']} | **{r['scores']['overall']}** |")
    lines.append("")

    return "\n".join(lines)


def generate_reports(date: str = None) -> tuple[Path, Path]:
    """Generate both EN and KO reports."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    data_dir = BASE_DIR / "data" / date
    metrics_path = data_dir / "metrics.json"
    analysis_dir = data_dir / "analysis"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Load analyses
    analyses = {}
    for cat_name in metrics["categories"]:
        analysis = load_analysis(analysis_dir, cat_name)
        if analysis:
            analyses[cat_name] = analysis

    # Generate reports
    en_report = generate_en_report(date, metrics, analyses)
    ko_report = generate_ko_report(date, metrics, analyses)

    # Save
    en_dir = BASE_DIR / "reports" / "en"
    ko_dir = BASE_DIR / "reports" / "ko"
    en_dir.mkdir(parents=True, exist_ok=True)
    ko_dir.mkdir(parents=True, exist_ok=True)

    en_path = en_dir / f"{date}.md"
    ko_path = ko_dir / f"{date}.md"

    with open(en_path, "w", encoding="utf-8") as f:
        f.write(en_report)
    with open(ko_path, "w", encoding="utf-8") as f:
        f.write(ko_report)

    print(f"Reports generated:")
    print(f"  EN: {en_path}")
    print(f"  KO: {ko_path}")

    return en_path, ko_path


if __name__ == "__main__":
    generate_reports()

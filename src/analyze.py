"""
Claude Code CLI를 사용하여 카테고리별 정성적 분석을 수행합니다.
"""

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def find_claude_cmd() -> str:
    """Find the claude CLI command."""
    # Explicit Windows path first
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    # Fallback to PATH
    for name in ["claude.cmd", "claude"]:
        found = shutil.which(name)
        if found:
            return found
    return "claude"


def load_prompt_template() -> str:
    template_path = BASE_DIR / "config" / "prompts" / "analyze.md"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def analyze_category(category: str, repos_data: list[dict], template: str) -> dict | None:
    """Run Claude Code CLI to analyze a single category."""
    # Remove readme_excerpt to keep prompt size manageable
    clean_data = []
    for r in repos_data:
        entry = {k: v for k, v in r.items() if k != "readme_excerpt"}
        clean_data.append(entry)

    data_str = json.dumps(clean_data, ensure_ascii=False, indent=2)
    prompt = template.replace("{{category}}", category).replace("{{data}}", data_str)

    print(f"  Running Claude Code analysis for {category}...")

    try:
        result = subprocess.run(
            [find_claude_cmd(), "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0 and result.stdout.strip():
            # Claude Code --output-format json returns {"result": "..."}
            try:
                outer = json.loads(result.stdout)
                content = outer.get("result", result.stdout)
            except json.JSONDecodeError:
                content = result.stdout

            # Try to extract JSON from the content
            return extract_json(content)

        # Fallback without --output-format json
        result = subprocess.run(
            [find_claude_cmd(), "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0 and result.stdout.strip():
            return extract_json(result.stdout)

        print(f"  Warning: Claude Code returned no output for {category}")
        return None

    except subprocess.TimeoutExpired:
        print(f"  Warning: Claude Code timed out for {category}")
        return None
    except FileNotFoundError:
        print("  Error: 'claude' command not found. Is Claude Code CLI installed?")
        return None


def extract_json(text: str) -> dict | None:
    """Extract JSON from Claude Code output."""
    import re

    # Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Find JSON in markdown code blocks
    patterns = [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                continue

    # Try to find raw JSON object
    match = re.search(r'\{[\s\S]*"individual_analysis"[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def run_analysis(date: str = None) -> dict:
    """Run analysis for all categories."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    metrics_path = BASE_DIR / "data" / date / "metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    template = load_prompt_template()
    analysis_dir = BASE_DIR / "data" / date / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for category, repos in metrics["categories"].items():
        print(f"\n{'='*40}")
        print(f"  Analyzing: {category}")
        print(f"{'='*40}")

        analysis = analyze_category(category, repos, template)

        output_path = analysis_dir / f"{category.lower().replace(' ', '_')}.json"
        if analysis:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            print(f"  Saved to {output_path}")
            results[category] = analysis
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"error": "analysis failed"}, f)
            print(f"  Analysis failed for {category}")

        # Rate limit pause
        time.sleep(2)

    return results


if __name__ == "__main__":
    run_analysis()

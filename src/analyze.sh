#!/bin/bash
# Claude Code CLI를 사용하여 카테고리별 정성적 분석을 수행합니다.
#
# Usage: bash src/analyze.sh <date>
# Example: bash src/analyze.sh 2026-03-23

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DATE="${1:-$(date +%Y-%m-%d)}"
DATA_DIR="$BASE_DIR/data/$DATE"
METRICS_FILE="$DATA_DIR/metrics.json"
PROMPT_TEMPLATE="$BASE_DIR/config/prompts/analyze.md"
ANALYSIS_DIR="$DATA_DIR/analysis"

if [ ! -f "$METRICS_FILE" ]; then
    echo "Error: $METRICS_FILE not found. Run collect.py and metrics.py first."
    exit 1
fi

mkdir -p "$ANALYSIS_DIR"

# Python으로 카테고리 목록 추출
CATEGORIES=$(python3 -c "
import json
with open('$METRICS_FILE', 'r', encoding='utf-8') as f:
    data = json.load(f)
for cat in data['categories']:
    print(cat)
")

for CATEGORY in $CATEGORIES; do
    echo ""
    echo "========================================="
    echo "Analyzing: $CATEGORY"
    echo "========================================="

    SAFE_NAME=$(echo "$CATEGORY" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    OUTPUT_FILE="$ANALYSIS_DIR/${SAFE_NAME}.json"

    # 해당 카테고리 데이터를 임시 파일로 추출
    TEMP_DATA=$(mktemp)
    python3 -c "
import json
with open('$METRICS_FILE', 'r', encoding='utf-8') as f:
    data = json.load(f)
cat_data = data['categories'].get('$CATEGORY', [])
# Remove readme_excerpt for prompt size management, keep summary
for repo in cat_data:
    repo.pop('readme_excerpt', None)
print(json.dumps(cat_data, ensure_ascii=False, indent=2))
" > "$TEMP_DATA"

    # 프롬프트 생성
    TEMP_PROMPT=$(mktemp)
    sed "s|{{category}}|$CATEGORY|g" "$PROMPT_TEMPLATE" > "$TEMP_PROMPT"

    # {{data}} 부분을 실제 데이터로 교체
    DATA_CONTENT=$(cat "$TEMP_DATA")
    python3 -c "
import sys
with open('$TEMP_PROMPT', 'r', encoding='utf-8') as f:
    content = f.read()
with open('$TEMP_DATA', 'r', encoding='utf-8') as f:
    data = f.read()
content = content.replace('{{data}}', data)
with open('$TEMP_PROMPT', 'w', encoding='utf-8') as f:
    f.write(content)
"

    # Claude Code CLI 호출
    echo "  Running Claude Code analysis..."
    if claude -p "$(cat "$TEMP_PROMPT")" --output-format json > "$OUTPUT_FILE" 2>/dev/null; then
        echo "  Analysis saved to $OUTPUT_FILE"
    else
        # Fallback: json 포맷 없이 재시도
        claude -p "$(cat "$TEMP_PROMPT")" > "$OUTPUT_FILE" 2>/dev/null || {
            echo "  Warning: Claude Code analysis failed for $CATEGORY"
            echo '{"error": "analysis failed"}' > "$OUTPUT_FILE"
        }
    fi

    # 임시 파일 정리
    rm -f "$TEMP_DATA" "$TEMP_PROMPT"

    echo "  Done with $CATEGORY"
    # Rate limit 대기
    sleep 2
done

echo ""
echo "All analyses complete. Results in $ANALYSIS_DIR"

#!/bin/bash
# 생성된 리포트와 데이터를 git에 커밋하고 push합니다.
#
# Usage: bash src/publish.sh <date>
# Example: bash src/publish.sh 2026-03-23

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DATE="${1:-$(date +%Y-%m-%d)}"

cd "$BASE_DIR"

# git 초기화 (최초 실행 시)
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
fi

# 리모트가 설정되어 있는지 확인
if ! git remote get-url origin &>/dev/null; then
    echo "Warning: No remote 'origin' configured."
    echo "Set it with: git remote add origin https://github.com/<user>/<repo>.git"
    echo "Committing locally only."
    HAS_REMOTE=false
else
    HAS_REMOTE=true
fi

# .gitignore 생성 (최초 실행 시)
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.env
venv/
.venv/
EOF
fi

# 변경사항 스테이징
git add reports/ data/ .gitignore
git add -A

# 변경사항이 있는지 확인
if git diff --cached --quiet; then
    echo "No changes to commit."
    exit 0
fi

# 커밋
git commit -m "report: AI Agent Trend Report $DATE"

# 푸시
if [ "$HAS_REMOTE" = true ]; then
    echo "Pushing to origin..."
    git push origin main
    echo "Pushed successfully."
else
    echo "Committed locally. Push manually after setting remote."
fi

#!/bin/bash
set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Web Branch Commit Helper"
echo "========================================"
echo ""

# Detect current branch from .git/HEAD
if [ -f .git/HEAD ]; then
    HEAD_REF=$(cat .git/HEAD)
    if [[ $HEAD_REF == ref:* ]]; then
        CURRENT_BRANCH="${HEAD_REF#ref: refs/heads/}"
        echo -e "${GREEN}Current branch: ${CURRENT_BRANCH}${NC}"
    else
        echo -e "${YELLOW}Detached HEAD detected${NC}"
        CURRENT_BRANCH="${CLAUDE_BRANCH:-claude-web-fix}"
        echo -e "${YELLOW}Creating/switching to: ${CURRENT_BRANCH}${NC}"
        git checkout -b "$CURRENT_BRANCH" 2>/dev/null || git checkout "$CURRENT_BRANCH"
    fi
else
    echo -e "${RED}Error: Not a git repository (.git/HEAD not found)${NC}"
    exit 1
fi

echo ""
echo "========================================"
echo "Safety Checks"
echo "========================================"

# Safety: refuse if docker-compose.yml still has absolute paths
if grep -qE '/host_mnt|/Users' infra/docker-compose.yml 2>/dev/null; then
    echo -e "${RED}✗ ERROR: Absolute host paths still found in infra/docker-compose.yml${NC}"
    echo -e "${YELLOW}  Found problematic paths:${NC}"
    grep -nE '/host_mnt|/Users' infra/docker-compose.yml | head -5
    echo ""
    echo -e "${YELLOW}  Please fix these paths before committing.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ No absolute paths found in docker-compose.yml${NC}"

echo ""
echo "========================================"
echo "Staging Changes"
echo "========================================"

# Add all changes
git add -A

# Check if anything staged
if git diff --cached --quiet; then
    echo -e "${GREEN}✓ No changes to commit${NC}"
    exit 0
fi

echo -e "${YELLOW}Staged changes:${NC}"
git diff --cached --stat

echo ""
echo "========================================"
echo "Creating Commit"
echo "========================================"

# Commit with descriptive message
git commit -m "chore: web-branch sync — compose relative mounts & secrets; install.sh env; DB URL-encoding; settings hardening

- All Docker Compose secrets use relative paths with \${SECRETS_DIR}
- No bind mounts for secret files (proper secrets management)
- install.sh creates directories and generates URL-safe secrets
- URL-encoded DATABASE_URL with expanded values in .env
- Robust Python settings with port validation and URL encoding
- Strengthened validation guards in install.sh
- Zero absolute paths (/host_mnt, /Users) in configuration
- Cross-platform compatibility (macOS, Linux, Windows WSL2)
- Idempotent and safe to re-run

Branch: ${CURRENT_BRANCH}"

echo ""
echo -e "${GREEN}✓ Commit created on branch: ${CURRENT_BRANCH}${NC}"
echo ""
echo "Next step: Run 'bash scripts/web-branch-push.sh' to push to remote"
echo ""

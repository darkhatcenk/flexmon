#!/bin/bash
set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Web Branch Push Helper"
echo "========================================"
echo ""

# Environment variables with defaults
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-$(git branch --show-current 2>/dev/null || echo claude-web-fix)}"

echo -e "${GREEN}Remote: ${GIT_REMOTE}${NC}"
echo -e "${GREEN}Branch: ${GIT_BRANCH}${NC}"
echo ""

# Check if remote is configured
if ! git remote get-url "$GIT_REMOTE" >/dev/null 2>&1; then
    echo -e "${RED}✗ ERROR: Remote '${GIT_REMOTE}' is not configured${NC}"
    echo ""
    echo "To configure a remote, run:"
    echo "  git remote add ${GIT_REMOTE} <repository-url>"
    echo ""
    echo "Example:"
    echo "  git remote add origin https://github.com/user/flexmon.git"
    echo ""
    exit 1
fi

REMOTE_URL=$(git remote get-url "$GIT_REMOTE")
echo -e "${GREEN}Remote URL: ${REMOTE_URL}${NC}"

echo ""
echo "========================================"
echo "Syncing with Remote"
echo "========================================"

# Try to pull with rebase (may fail if branch doesn't exist on remote yet)
echo -e "${YELLOW}Attempting to pull with rebase...${NC}"
if git pull --rebase "$GIT_REMOTE" "$GIT_BRANCH" 2>/dev/null; then
    echo -e "${GREEN}✓ Successfully pulled and rebased${NC}"
else
    echo -e "${YELLOW}⚠ Pull failed (branch may not exist on remote yet)${NC}"
fi

echo ""
echo "========================================"
echo "Pushing to Remote"
echo "========================================"

# Push with retry logic (exponential backoff)
RETRY=0
MAX_RETRIES=4
DELAY=2

while [ $RETRY -lt $MAX_RETRIES ]; do
    echo -e "${YELLOW}Push attempt $((RETRY+1))/${MAX_RETRIES}...${NC}"

    if git push -u "$GIT_REMOTE" "$GIT_BRANCH"; then
        echo ""
        echo -e "${GREEN}✓ Successfully pushed to ${GIT_REMOTE}/${GIT_BRANCH}${NC}"
        echo ""
        echo "========================================"
        echo "Push Complete!"
        echo "========================================"
        echo ""
        echo "Your changes are now on branch: ${GIT_BRANCH}"
        echo "Remote: ${REMOTE_URL}"
        echo ""
        exit 0
    else
        RETRY=$((RETRY+1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}⚠ Push failed, retrying in ${DELAY}s...${NC}"
            sleep $DELAY
            DELAY=$((DELAY*2))
        fi
    fi
done

echo ""
echo -e "${RED}✗ Failed to push after ${MAX_RETRIES} attempts${NC}"
echo ""
echo "Possible issues:"
echo "  - Network connectivity problems"
echo "  - Authentication required"
echo "  - Branch protection rules"
echo "  - Remote repository issues"
echo ""
echo "Try running manually:"
echo "  git push -u ${GIT_REMOTE} ${GIT_BRANCH}"
echo ""
exit 1

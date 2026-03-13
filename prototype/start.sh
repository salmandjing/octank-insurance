#!/bin/bash
# ClaimFlow AI — Start Script

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ClaimFlow AI — FNOL Automation for Agencies   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check for .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}No .env file found. Copying from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}Edit .env and add your ANTHROPIC_API_KEY${NC}"
    fi
fi

# Check Anthropic API key
if [ -f .env ]; then
    source .env
fi
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-..." ]; then
    echo -e "${YELLOW}Warning: ANTHROPIC_API_KEY not set${NC}"
    echo "Add your key to .env: ANTHROPIC_API_KEY=sk-ant-api03-..."
    exit 1
fi
echo -e "${GREEN}Anthropic API key configured${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q -r requirements.txt

echo ""
echo -e "${GREEN}Starting ClaimFlow AI on http://localhost:${PORT:-8000}${NC}"
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo ""

# Start server
uvicorn backend.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --reload

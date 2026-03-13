import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Model — Claude Sonnet 4 for everything
MODEL = os.getenv("MODEL", "claude-sonnet-4-20250514")
SUPERVISOR_MODEL = MODEL
SPECIALIST_MODEL = MODEL
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))

# Agent
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "5"))

# RAG
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))

# Session
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))

# Agency info
AGENCY_NAME = "Prairie Shield Insurance Group"
AGENCY_CITY = "Omaha"
AGENCY_STATE = "NE"

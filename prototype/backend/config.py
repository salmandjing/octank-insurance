import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"

# AWS / Bedrock
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Models — two-tier for cost efficiency
# Haiku for fast/cheap classification, Sonnet for specialist reasoning
SUPERVISOR_MODEL_ID = os.getenv(
    "SUPERVISOR_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0"
)
SPECIALIST_MODEL_ID = os.getenv(
    "SPECIALIST_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
)
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))

# Agent
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "5"))

# RAG
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))

# Session
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

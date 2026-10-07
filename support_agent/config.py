"""
SupportAgent AI - Configuration and Environment Settings
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base directories
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

# Database configuration
DEFAULT_DB_PATH = PACKAGE_ROOT / "data" / "support_agent.db"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # 'mock', 'ollama', 'openai', 'gemini'
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))

# OpenAI / Gemini optional keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Agent Orchestrator settings
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "6"))
AGENT_PROMPT_VERSION = os.getenv("AGENT_PROMPT_VERSION", "v1.2")
RECENT_MESSAGES_LIMIT = int(os.getenv("RECENT_MESSAGES_LIMIT", "12"))
CONTEXT_TOKEN_LIMIT = int(os.getenv("CONTEXT_TOKEN_LIMIT", "4000"))
GROUNDING_CONFIDENCE_THRESHOLD = float(os.getenv("GROUNDING_THRESHOLD", "0.60"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

# Demo mode flag
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")


class AppConfig(BaseModel):
    app_name: str = "SupportAgent AI"
    version: str = "2.0.0"
    db_path: Path = DB_PATH
    llm_provider: str = LLM_PROVIDER
    ollama_url: str = OLLAMA_URL
    ollama_model: str = OLLAMA_MODEL
    max_steps: int = MAX_AGENT_STEPS
    prompt_version: str = AGENT_PROMPT_VERSION
    demo_mode: bool = DEMO_MODE


config = AppConfig()

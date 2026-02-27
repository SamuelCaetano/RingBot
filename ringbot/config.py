"""Configuration management with .env loading."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

load_dotenv(PROJECT_ROOT / ".env")


def get_api_key(provider: str) -> str:
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = key_map.get(provider)
    if not env_var:
        raise ValueError(f"Unknown provider: {provider}")
    key = os.getenv(env_var, "")
    if not key:
        raise RuntimeError(
            f"{env_var} not set. Copy .env.example to .env and fill in your key."
        )
    return key


def get_default_provider() -> str:
    return os.getenv("AI_PROVIDER", "openai")


def get_default_ring_size() -> float:
    return float(os.getenv("DEFAULT_RING_SIZE", "7"))

"""Load settings from the .env file.

python-dotenv reads GEMINI_API_KEY so the key stays out of the source code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is one folder above backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Open the .env file, paste your key, "
            "and save. Get a key at https://aistudio.google.com/apikey"
        )
    return key


def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

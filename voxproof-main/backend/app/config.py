import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

LOBSTER_BINARY = os.environ.get("LOBSTER_BINARY", "lobstertrap")
LOBSTER_POLICIES_DIR = os.environ.get("LOBSTER_POLICIES_DIR", str(PROJECT_ROOT / "policies"))
SCENARIOS_DIR = os.environ.get("SCENARIOS_DIR", str(PROJECT_ROOT / "scenarios"))
FIXTURES_DIR = os.environ.get("FIXTURES_DIR", str(PROJECT_ROOT / "fixtures"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL = os.environ.get("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
GEMINI_PRO_MODEL = os.environ.get("GEMINI_PRO_MODEL", "gemini-2.5-pro")
GEMINI_LIVE_MODEL = os.environ.get("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-latest")

DB_PATH = os.environ.get("VOXPROOF_DB", str(PROJECT_ROOT / "voxproof.db"))

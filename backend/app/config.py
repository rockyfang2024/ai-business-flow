"""
Shared configuration for Business Flow Skill Web backend.
Avoids circular imports between routers and main.
"""

from pathlib import Path

# Project root data directory
BASE_DATA_DIR = Path(__file__).parent.parent.parent / "data"
BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
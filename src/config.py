
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"


def load_config() -> dict:
    """Load project settings from the JSON configuration file."""
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_path(relative_path: str) -> Path:
    """Resolve a configured path relative to the project root."""
    return PROJECT_ROOT / relative_path

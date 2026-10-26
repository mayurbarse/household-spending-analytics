
import sqlite3
from pathlib import Path

from src.config import PROJECT_ROOT, load_config, resolve_path


SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create a SQLite connection with foreign-key enforcement enabled."""
    if db_path is None:
        config = load_config()
        db_path = resolve_path(config["database_path"])
    else:
        db_path = Path(db_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: str | Path | None = None) -> None:
    """Create the database tables and indexes from schema.sql."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Database schema not found: {SCHEMA_PATH}")

    with get_connection(db_path) as connection:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema_sql)

    print("Database schema initialized successfully.")


if __name__ == "__main__":
    initialize_database()

import sqlite3
from pathlib import Path

db_path = Path("database/app.db")

if not db_path.exists():
    print(f"Database not found: {db_path}")
    raise SystemExit(1)

conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON")

tables = [
    row[0]
    for row in conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
]

print("DATABASE TABLES AND ROW COUNTS")
for table in tables:
    # Table names come from SQLite's own metadata.
    quoted_table = '"' + table.replace('"', '""') + '"'
    count = conn.execute(
        f"SELECT COUNT(*) FROM {quoted_table}"
    ).fetchone()[0]
    print(f"{table}: {count:,} rows")

print("\nFOREIGN KEY CHECK")
violations = conn.execute("PRAGMA foreign_key_check").fetchall()
print("No foreign-key violations." if not violations else violations)

conn.close()

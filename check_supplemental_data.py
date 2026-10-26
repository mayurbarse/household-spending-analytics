
from src.db import get_connection

connection = get_connection()

for table in ["budgets", "recurring_series"]:
    count = connection.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]
    print(f"{table}: {count:,} rows")

connection.close()

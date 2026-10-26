
from src.db import get_connection

connection = get_connection()

tables = connection.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
    """
).fetchall()

print("Database tables:")
for table in tables:
    print("-", table["name"])

connection.close()

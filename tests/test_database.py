
import sqlite3

import pytest

from src.db import initialize_database, get_connection


@pytest.fixture
def test_db(tmp_path):
    """Create an isolated database for each test."""
    db_path = tmp_path / "test_app.db"
    initialize_database(db_path)
    return db_path


def test_all_required_tables_exist(test_db):
    with get_connection(test_db) as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    tables = {row["name"] for row in rows}

    expected = {
        "user_profiles",
        "accounts",
        "merchants",
        "merchant_aliases",
        "transactions",
        "categories",
        "category_rules",
        "budgets",
        "recurring_series",
        "recurring_transaction_links",
        "insights",
        "state_events",
        "exceptions",
    }

    assert expected.issubset(tables)


def test_foreign_keys_are_enabled(test_db):
    with get_connection(test_db) as connection:
        enabled = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

    assert enabled == 1


def test_duplicate_user_id_is_rejected(test_db):
    with get_connection(test_db) as connection:
        connection.execute(
            """
            INSERT INTO user_profiles
            (user_id, household_size, region, income_band,
             currency, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("USR-000001", 2, "West", "middle",
             "INR", "2026-01-01T00:00:00Z", "active"),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO user_profiles
                (user_id, household_size, region, income_band,
                 currency, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("USR-000001", 3, "North", "middle",
                 "INR", "2026-01-01T00:00:00Z", "active"),
            )


def test_orphan_account_is_rejected(test_db):
    with get_connection(test_db) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO accounts
                (account_id, user_id, account_type, opening_date, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("ACC-USR-999999-01", "USR-999999",
                 "savings", "2026-01-01", "active"),
            )

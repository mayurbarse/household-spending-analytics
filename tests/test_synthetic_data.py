
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from src.config import resolve_path
from src.db import get_connection, initialize_database
from src.generate_data import create_profiles


def test_profile_generation_is_reproducible():
    """The same seed should produce identical profiles."""
    first = create_profiles(10, np.random.default_rng(20261022))
    second = create_profiles(10, np.random.default_rng(20261022))

    assert first == second


def test_transfer_pairs_balance():
    """Both sides of each internal transfer must net to zero."""
    path = resolve_path("data/output/transactions.csv")
    assert path.exists(), "Run the synthetic data generator first."

    transactions = pd.read_csv(path)
    transfers = transactions[
        transactions["transaction_type"] == "transfer"
    ]

    assert not transfers.empty

    for group_id, group in transfers.groupby("transfer_group_id"):
        assert pd.notna(group_id)
        assert len(group) == 2
        assert group["amount_minor"].sum() == 0
        assert group["account_id"].nunique() == 2


def test_refunds_are_positive_credits_not_positive_expenses():
    """Refund rows should be positive credits with refund transaction type."""
    path = resolve_path("data/output/transactions.csv")
    transactions = pd.read_csv(path)

    refunds = transactions[
        transactions["transaction_type"] == "refund"
    ]

    assert not refunds.empty
    assert (refunds["amount_minor"] > 0).all()
    assert (refunds["category_id"] == "CAT-014").all()


def test_timezone_boundary_converts_to_next_local_day():
    """UTC timestamps must be converted before assigning local dates."""
    utc_timestamp = datetime.fromisoformat(
        "2026-01-01T20:00:00+00:00"
    )

    local_timestamp = utc_timestamp.astimezone(
        ZoneInfo("Asia/Kolkata")
    )

    assert local_timestamp.date().isoformat() == "2026-01-02"
    assert local_timestamp.hour == 1
    assert local_timestamp.minute == 30


def test_ground_truth_contains_all_five_scenarios():
    """All required edge cases should be documented in ground truth."""
    path = resolve_path("data/ground_truth/edge_case_scenarios.csv")
    assert path.exists(), "Run the supplemental data generator first."

    scenarios = pd.read_csv(path)
    scenario_types = set(scenarios["scenario_type"])

    expected = {
        "internal_transfer_double_count",
        "refund_misclassified_as_expense",
        "missing_recurring_occurrence",
        "timezone_date_boundary",
        "budget_category_not_in_taxonomy",
    }

    assert expected.issubset(scenario_types)


def test_invalid_budget_category_is_rejected(tmp_path):
    """SQLite must reject a budget referencing a nonexistent category."""
    db_path = tmp_path / "invalid_budget_test.db"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO user_profiles
            (user_id, household_size, region, income_band,
             currency, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "USR-TEST01", 2, "West", "middle",
                "INR", "2026-01-01T00:00:00Z", "active",
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO budgets
                (budget_id, user_id, category_id, budget_month,
                 budget_amount_minor, currency, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "BUD-INVALID-001",
                    "USR-TEST01",
                    "CAT-999",
                    "2026-01-01",
                    100000,
                    "INR",
                    "active",
                ),
            )


def test_missing_recurring_occurrence_is_labelled():
    """The expected missing occurrence must appear in ground truth."""
    path = resolve_path("data/ground_truth/edge_case_scenarios.csv")
    scenarios = pd.read_csv(path)

    missing = scenarios[
        scenarios["scenario_type"] == "missing_recurring_occurrence"
    ]

    assert len(missing) == 1
    assert missing.iloc[0]["status"] == "labelled"
    assert pd.notna(missing.iloc[0]["entity_ids"])

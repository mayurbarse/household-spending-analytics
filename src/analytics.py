
"""Core spending analytics for household-spending-analytics."""

import json
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXPENSE_TYPES = {"purchase", "bill_payment", "fee"}
REFUND_TYPES = {"refund"}


def _load_transactions_uncached(db_path=None) -> pd.DataFrame:
    """Load posted transactions and associate each with its account owner."""
    if db_path is None:
        settings_path = PROJECT_ROOT / "config" / "settings.json"
        with settings_path.open("r", encoding="utf-8") as file:
            settings = json.load(file)

        if isinstance(settings.get("database"), dict):
            database_setting = settings["database"]["path"]
        else:
            database_setting = settings.get("database_path")

        if not database_setting:
            raise ValueError("Database path not found in settings.json.")

        db_path = Path(database_setting)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path

    query = """
        SELECT
            t.transaction_id,
            a.user_id,
            t.account_id,
            t.merchant_id,
            t.transaction_type,
            ABS(t.amount_minor) / 100.0 AS amount,
            t.currency,
            t.local_transaction_date AS transaction_date,
            t.descriptor AS description,
            t.category_id
        FROM transactions AS t
        JOIN accounts AS a
            ON t.account_id = a.account_id
        WHERE t.status = 'posted'
    """

    with sqlite3.connect(str(db_path)) as connection:
        transactions = pd.read_sql_query(query, connection)

    if transactions.empty:
        return transactions

    transactions["amount"] = pd.to_numeric(
        transactions["amount"], errors="raise"
    )
    transactions["transaction_type"] = (
        transactions["transaction_type"].str.lower().str.strip()
    )

    return transactions


@lru_cache(maxsize=1)
def _load_default_transactions_cached() -> pd.DataFrame:
    """Cache transactions loaded from the default database."""
    return _load_transactions_uncached()


def load_transactions(db_path=None) -> pd.DataFrame:
    """Load transactions, caching the default database result."""
    if db_path is not None:
        return _load_transactions_uncached(db_path).copy()

    return _load_default_transactions_cached().copy()


def clear_transaction_cache() -> None:
    """Clear cached transactions after the database is updated."""
    _load_default_transactions_cached.cache_clear()

def calculate_spending(transactions: pd.DataFrame) -> pd.DataFrame:
    """Calculate expenses, refunds, and net spending per transaction."""
    required = {"transaction_type", "amount"}
    missing = required - set(transactions.columns)

    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    result = transactions.copy()
    result["transaction_type"] = (
        result["transaction_type"].astype(str).str.lower().str.strip()
    )
    result["amount"] = pd.to_numeric(result["amount"], errors="raise")

    if result["amount"].isna().any():
        raise ValueError("Transaction amounts cannot be missing.")

    if (result["amount"] < 0).any():
        raise ValueError(
            "Amounts must be non-negative; use positive magnitudes "
            "for expenses and refunds."
        )

    result["gross_expense"] = 0.0
    result["refund_credit"] = 0.0

    expense_mask = result["transaction_type"].isin(EXPENSE_TYPES)
    refund_mask = result["transaction_type"].isin(REFUND_TYPES)

    result.loc[expense_mask, "gross_expense"] = result.loc[
        expense_mask, "amount"
    ]
    result.loc[refund_mask, "refund_credit"] = result.loc[
        refund_mask, "amount"
    ]

    result["net_spending"] = (
        result["gross_expense"] - result["refund_credit"]
    )

    return result


def spending_summary(
    transactions: pd.DataFrame,
) -> dict[str, float | int]:
    """Return overall spending metrics."""
    calculated = calculate_spending(transactions)

    gross_expenses = float(calculated["gross_expense"].sum())
    refunds = float(calculated["refund_credit"].sum())

    return {
        "transaction_count": int(len(calculated)),
        "expense_transaction_count": int(
            calculated["transaction_type"].isin(EXPENSE_TYPES).sum()
        ),
        "refund_transaction_count": int(
            calculated["transaction_type"].isin(REFUND_TYPES).sum()
        ),
        "gross_expenses": round(gross_expenses, 2),
        "refunds": round(refunds, 2),
        "net_spending": round(gross_expenses - refunds, 2),
    }


import pandas as pd
import pytest

from src.budget_analytics import (
    calculate_monthly_spending,
    compare_budgets,
)


def test_monthly_spending_excludes_transfers_and_subtracts_refunds():
    transactions = pd.DataFrame(
        [
            {
                "user_id": "U1",
                "transaction_type": "purchase",
                "amount": 100.0,
                "transaction_date": "2026-01-10",
                "category_id": "CAT-1",
            },
            {
                "user_id": "U1",
                "transaction_type": "refund",
                "amount": 20.0,
                "transaction_date": "2026-01-15",
                "category_id": "CAT-1",
            },
            {
                "user_id": "U1",
                "transaction_type": "transfer",
                "amount": 500.0,
                "transaction_date": "2026-01-20",
                "category_id": "CAT-1",
            },
        ]
    )

    result = calculate_monthly_spending(transactions)

    assert len(result) == 1
    assert result.iloc[0]["gross_expenses"] == 100.0
    assert result.iloc[0]["refunds"] == 20.0
    assert result.iloc[0]["net_spending"] == 80.0
    assert result.iloc[0]["transaction_count"] == 3


def test_budget_remaining_and_overspending():
    budgets = pd.DataFrame(
        [
            {
                "user_id": "U1",
                "category_id": "CAT-1",
                "month": "2026-01",
                "budget_amount": 100.0,
            },
            {
                "user_id": "U1",
                "category_id": "CAT-2",
                "month": "2026-01",
                "budget_amount": 200.0,
            },
        ]
    )

    monthly = pd.DataFrame(
        [
            {
                "user_id": "U1",
                "category_id": "CAT-1",
                "month": "2026-01",
                "net_spending": 130.0,
            }
        ]
    )

    result = compare_budgets(budgets, monthly).sort_values(
        "category_id"
    ).reset_index(drop=True)

    assert result.loc[0, "remaining_budget"] == -30.0
    assert result.loc[0, "budget_utilization_pct"] == 130.0
    assert bool(result.loc[0, "is_overspent"]) is True
    assert result.loc[0, "overspend_amount"] == 30.0

    assert result.loc[1, "net_spending"] == 0.0
    assert result.loc[1, "remaining_budget"] == 200.0
    assert bool(result.loc[1, "is_overspent"]) is False


def test_duplicate_budget_keys_are_rejected():
    budgets = pd.DataFrame(
        [
            {
                "user_id": "U1",
                "category_id": "CAT-1",
                "month": "2026-01",
                "budget_amount": 100.0,
            },
            {
                "user_id": "U1",
                "category_id": "CAT-1",
                "month": "2026-01",
                "budget_amount": 120.0,
            },
        ]
    )

    monthly = pd.DataFrame(
        columns=["user_id", "category_id", "month", "net_spending"]
    )

    with pytest.raises(ValueError, match="Duplicate budgets"):
        compare_budgets(budgets, monthly)


def test_missing_required_transaction_column_is_rejected():
    transactions = pd.DataFrame(
        [
            {
                "user_id": "U1",
                "transaction_type": "purchase",
                "amount": 10.0,
                "transaction_date": "2026-01-10",
            }
        ]
    )

    with pytest.raises(ValueError, match="Missing required transaction"):
        calculate_monthly_spending(transactions)

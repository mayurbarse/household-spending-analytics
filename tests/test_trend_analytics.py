
import pandas as pd
import pytest

from src.trend_analytics import calculate_monthly_trends


def test_monthly_trends_aggregate_expenses_and_refunds():
    transactions = pd.DataFrame(
        [
            {
                "user_id": "U1",
                "transaction_type": "purchase",
                "amount": 1000,
                "transaction_date": "2026-01-05",
            },
            {
                "user_id": "U1",
                "transaction_type": "refund",
                "amount": 200,
                "transaction_date": "2026-01-12",
            },
            {
                "user_id": "U1",
                "transaction_type": "transfer",
                "amount": 500,
                "transaction_date": "2026-01-15",
            },
            {
                "user_id": "U1",
                "transaction_type": "fee",
                "amount": 50,
                "transaction_date": "2026-02-02",
            },
        ]
    )

    result = calculate_monthly_trends(transactions)

    january = result[result["month"] == "2026-01"].iloc[0]
    february = result[result["month"] == "2026-02"].iloc[0]

    assert january["gross_expenses"] == 1000
    assert january["refunds"] == 200
    assert january["net_spending"] == 800
    assert february["net_spending"] == 50


def test_monthly_trends_separate_users():
    transactions = pd.DataFrame(
        [
            {
                "user_id": "U1",
                "transaction_type": "purchase",
                "amount": 100,
                "transaction_date": "2026-01-05",
            },
            {
                "user_id": "U2",
                "transaction_type": "purchase",
                "amount": 250,
                "transaction_date": "2026-01-06",
            },
        ]
    )

    result = calculate_monthly_trends(transactions)

    assert len(result) == 2
    assert set(result["user_id"]) == {"U1", "U2"}


def test_monthly_trends_reject_invalid_dates():
    transactions = pd.DataFrame(
        [
            {
                "transaction_type": "purchase",
                "amount": 100,
                "transaction_date": "not-a-date",
            }
        ]
    )

    with pytest.raises(ValueError, match="dates"):
        calculate_monthly_trends(transactions)


def test_monthly_trends_reject_missing_columns():
    transactions = pd.DataFrame(
        [{"transaction_type": "purchase", "amount": 100}]
    )

    with pytest.raises(ValueError, match="transaction_date"):
        calculate_monthly_trends(transactions)

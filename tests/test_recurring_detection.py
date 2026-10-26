
"""Tests for recurring-payment detection."""

import pandas as pd
import pytest

from src.recurring_detection import detect_recurring_payments


def make_transactions(dates, amounts=None, merchant="MER-001"):
    if amounts is None:
        amounts = [500.0] * len(dates)

    return pd.DataFrame(
        {
            "user_id": ["USR-001"] * len(dates),
            "account_id": ["ACC-001"] * len(dates),
            "merchant_id": [merchant] * len(dates),
            "transaction_type": ["bill_payment"] * len(dates),
            "amount": amounts,
            "transaction_date": dates,
        }
    )


def test_detects_monthly_recurring_payment():
    transactions = make_transactions(
        ["2026-01-05", "2026-02-05", "2026-03-05", "2026-04-05"]
    )

    result = detect_recurring_payments(transactions)

    assert len(result) == 1
    assert result.iloc[0]["cadence"] == "monthly"
    assert result.iloc[0]["occurrences"] == 4
    assert result.iloc[0]["average_amount"] == 500.0


def test_ignores_groups_with_too_few_occurrences():
    transactions = make_transactions(["2026-01-05", "2026-02-05"])

    result = detect_recurring_payments(transactions)

    assert result.empty


def test_ignores_irregular_amounts():
    transactions = make_transactions(
        [
            "2026-01-05",
            "2026-02-05",
            "2026-03-05",
            "2026-04-05",
        ],
        amounts=[100, 300, 700, 1200],
    )

    result = detect_recurring_payments(transactions)

    assert result.empty


def test_ignores_refunds_and_transfers():
    transactions = make_transactions(
        ["2026-01-05", "2026-02-05", "2026-03-05", "2026-04-05"]
    )
    transactions["transaction_type"] = [
        "refund",
        "transfer",
        "refund",
        "transfer",
    ]

    result = detect_recurring_payments(transactions)

    assert result.empty


def test_detects_weekly_payment():
    transactions = make_transactions(
        ["2026-01-01", "2026-01-08", "2026-01-15", "2026-01-22"]
    )

    result = detect_recurring_payments(transactions)

    assert len(result) == 1
    assert result.iloc[0]["cadence"] == "weekly"


def test_rejects_missing_required_columns():
    with pytest.raises(ValueError, match="Missing required"):
        detect_recurring_payments(pd.DataFrame({"amount": [100]}))


def test_rejects_invalid_amount_tolerance():
    transactions = make_transactions(
        ["2026-01-05", "2026-02-05", "2026-03-05"]
    )

    with pytest.raises(ValueError, match="amount_tolerance"):
        detect_recurring_payments(
            transactions, amount_tolerance=1.0
        )


def test_empty_input_returns_empty_results():
    transactions = make_transactions([])
    
    result = detect_recurring_payments(transactions)

    assert result.empty
    assert "cadence" in result.columns

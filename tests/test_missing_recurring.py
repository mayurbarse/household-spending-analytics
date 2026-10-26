
import pandas as pd

from src.recurring_detection import detect_missing_recurring_occurrences


def test_missing_expected_payment_is_flagged():
    recurring_series = pd.DataFrame([
        {
            "user_id": "USR-000001",
            "account_id": "ACC-000001",
            "merchant_id": "MER-0001",
            "expected_amount": 499.0,
            "expected_occurrence_date": "2026-11-15",
        }
    ])

    transactions = pd.DataFrame([
        {
            "user_id": "USR-000001",
            "account_id": "ACC-000001",
            "merchant_id": "MER-0001",
            "amount": 499.0,
            "transaction_date": "2026-10-15",
        }
    ])

    result = detect_missing_recurring_occurrences(
        recurring_series,
        transactions,
        as_of_date="2026-11-20",
    )

    assert len(result) == 1
    assert result.iloc[0]["status"] == "missing_occurrence"
    assert result.iloc[0]["review_required"] == True


def test_matching_payment_is_not_flagged():
    recurring_series = pd.DataFrame([
        {
            "user_id": "USR-000001",
            "account_id": "ACC-000001",
            "merchant_id": "MER-0001",
            "expected_amount": 499.0,
            "expected_occurrence_date": "2026-11-15",
        }
    ])

    transactions = pd.DataFrame([
        {
            "user_id": "USR-000001",
            "account_id": "ACC-000001",
            "merchant_id": "MER-0001",
            "amount": 499.0,
            "transaction_date": "2026-11-16",
        }
    ])

    result = detect_missing_recurring_occurrences(
        recurring_series,
        transactions,
        as_of_date="2026-11-20",
    )

    assert result.empty


def test_future_payment_is_not_flagged():
    recurring_series = pd.DataFrame([
        {
            "user_id": "USR-000001",
            "account_id": "ACC-000001",
            "merchant_id": "MER-0001",
            "expected_amount": 499.0,
            "expected_occurrence_date": "2026-12-15",
        }
    ])

    transactions = pd.DataFrame(columns=[
        "user_id",
        "account_id",
        "merchant_id",
        "amount",
        "transaction_date",
    ])

    result = detect_missing_recurring_occurrences(
        recurring_series,
        transactions,
        as_of_date="2026-11-20",
    )

    assert result.empty

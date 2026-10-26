
import pandas as pd
import pytest

from src.anomaly_detection import detect_unusual_transactions


def sample_transactions():
    return pd.DataFrame({
        "user_id": ["U1"] * 7,
        "transaction_type": [
            "purchase", "purchase", "purchase", "purchase",
            "purchase", "purchase", "refund",
        ],
        "amount": [100, 100, 100, 100, 100, 10000, 5000],
        "category_id": ["CAT-1"] * 7,
    })


def test_flags_unusually_large_expense():
    result = detect_unusual_transactions(
        sample_transactions(),
        min_history=5,
        robust_z_threshold=3.5,
    )

    unusual = result[result["amount"] == 10000].iloc[0]
    assert bool(unusual["is_anomaly"]) is True
    assert "unusually high" in unusual["anomaly_reason"]


def test_refunds_are_not_flagged_as_expense_anomalies():
    result = detect_unusual_transactions(sample_transactions())
    refund = result[result["transaction_type"] == "refund"].iloc[0]

    assert bool(refund["is_anomaly"]) is False
    assert refund["anomaly_reason"] == ""


def test_insufficient_history_does_not_flag_anomaly():
    transactions = pd.DataFrame({
        "user_id": ["U1", "U1", "U1"],
        "transaction_type": ["purchase"] * 3,
        "amount": [100, 100, 10000],
    })

    result = detect_unusual_transactions(transactions, min_history=5)
    assert not result["is_anomaly"].any()


def test_categories_are_scored_separately():
    transactions = pd.DataFrame({
        "user_id": ["U1"] * 6,
        "transaction_type": ["purchase"] * 6,
        "amount": [100, 100, 100, 100, 100, 10000],
        "category_id": ["FOOD"] * 5 + ["TRAVEL"],
    })

    result = detect_unusual_transactions(transactions, min_history=5)
    travel = result[result["category_id"] == "TRAVEL"].iloc[0]

    # Only one transaction exists in this category, so there is
    # insufficient category-specific history.
    assert bool(travel["is_anomaly"]) is False


def test_empty_input_returns_empty_result():
    transactions = pd.DataFrame(
        columns=["user_id", "transaction_type", "amount"]
    )

    result = detect_unusual_transactions(transactions)
    assert result.empty
    assert "is_anomaly" in result.columns


def test_missing_required_column_raises_error():
    transactions = pd.DataFrame({
        "user_id": ["U1"],
        "amount": [100],
    })

    with pytest.raises(ValueError, match="Missing required transaction columns"):
        detect_unusual_transactions(transactions)


def test_negative_amount_raises_error():
    transactions = pd.DataFrame({
        "user_id": ["U1", "U1"],
        "transaction_type": ["purchase", "purchase"],
        "amount": [100, -50],
    })

    with pytest.raises(ValueError, match="non-negative"):
        detect_unusual_transactions(transactions)


def test_invalid_parameters_raise_errors():
    transactions = sample_transactions()

    with pytest.raises(ValueError, match="min_history"):
        detect_unusual_transactions(transactions, min_history=1)

    with pytest.raises(ValueError, match="robust_z_threshold"):
        detect_unusual_transactions(transactions, robust_z_threshold=0)

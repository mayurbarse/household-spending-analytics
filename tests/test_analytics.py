
import pandas as pd
import pytest

from src.analytics import calculate_spending, spending_summary


@pytest.fixture
def sample_transactions():
    return pd.DataFrame(
        [
            {"transaction_type": "purchase", "amount": 100.0},
            {"transaction_type": "bill_payment", "amount": 50.0},
            {"transaction_type": "fee", "amount": 5.0},
            {"transaction_type": "refund", "amount": 20.0},
            {"transaction_type": "transfer", "amount": 200.0},
            {"transaction_type": "salary", "amount": 1000.0},
            {"transaction_type": "other", "amount": 10.0},
        ]
    )


def test_transfers_and_income_do_not_count_as_spending(
    sample_transactions,
):
    result = calculate_spending(sample_transactions)

    transfer = result[result["transaction_type"] == "transfer"].iloc[0]
    salary = result[result["transaction_type"] == "salary"].iloc[0]

    assert transfer["net_spending"] == 0
    assert salary["net_spending"] == 0


def test_refund_reduces_net_spending(sample_transactions):
    result = calculate_spending(sample_transactions)

    assert result["gross_expense"].sum() == 155.0
    assert result["refund_credit"].sum() == 20.0
    assert result["net_spending"].sum() == 135.0


def test_summary_returns_expected_totals(sample_transactions):
    summary = spending_summary(sample_transactions)

    assert summary["transaction_count"] == 7
    assert summary["expense_transaction_count"] == 3
    assert summary["refund_transaction_count"] == 1
    assert summary["gross_expenses"] == 155.0
    assert summary["refunds"] == 20.0
    assert summary["net_spending"] == 135.0


def test_missing_required_column_raises_error():
    with pytest.raises(ValueError, match="Missing required"):
        calculate_spending(pd.DataFrame({"amount": [10.0]}))


def test_negative_amount_raises_error():
    with pytest.raises(ValueError, match="non-negative"):
        calculate_spending(
            pd.DataFrame(
                [{"transaction_type": "purchase", "amount": -10.0}]
            )
        )

def test_ground_truth_internal_transfer_legs_are_excluded():
    import pandas as pd

    from src.analytics import calculate_spending

    transactions = pd.DataFrame([
        {"transaction_type": "purchase", "amount": 500.0},
        {"transaction_type": "transfer", "amount": 1000.0},
        {"transaction_type": "transfer", "amount": 1000.0},
    ])

    result = calculate_spending(transactions)

    assert result["gross_expense"].sum() == 500.0
    assert result["refund_credit"].sum() == 0.0
    assert result["net_spending"].sum() == 500.0


def test_ground_truth_refund_is_not_counted_as_an_expense():
    import pandas as pd

    from src.analytics import calculate_spending

    transactions = pd.DataFrame([
        {"transaction_type": "purchase", "amount": 1000.0},
        {"transaction_type": "refund", "amount": 471.0},
    ])

    result = calculate_spending(transactions)

    assert result["gross_expense"].sum() == 1000.0
    assert result["refund_credit"].sum() == 471.0
    assert result["net_spending"].sum() == 529.0

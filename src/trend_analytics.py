
"""Monthly spending trend analytics."""

from pathlib import Path

import pandas as pd

from src.analytics import calculate_spending


def calculate_monthly_trends(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate expenses, refunds, and net spending by month.

    Required columns:
        transaction_type, amount, transaction_date

    If user_id exists, trends are calculated separately for each user.
    """
    required = {"transaction_type", "amount", "transaction_date"}
    missing = required - set(transactions.columns)

    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    if transactions.empty:
        columns = ["month", "gross_expenses", "refunds", "net_spending"]
        if "user_id" in transactions.columns:
            columns.insert(0, "user_id")
        return pd.DataFrame(columns=columns)

    result = transactions.copy()
    result["transaction_date"] = pd.to_datetime(
        result["transaction_date"], errors="coerce"
    )

    if result["transaction_date"].isna().any():
        raise ValueError("Transaction dates cannot be missing or invalid.")

    result = calculate_spending(result)
    result["month"] = result["transaction_date"].dt.strftime("%Y-%m")

    group_columns = ["month"]
    if "user_id" in result.columns:
        group_columns.insert(0, "user_id")

    trends = (
        result.groupby(group_columns, as_index=False)
        .agg(
            gross_expenses=("gross_expense", "sum"),
            refunds=("refund_credit", "sum"),
            net_spending=("net_spending", "sum"),
            transaction_count=("transaction_type", "size"),
        )
        .sort_values(group_columns)
        .reset_index(drop=True)
    )

    money_columns = ["gross_expenses", "refunds", "net_spending"]
    trends[money_columns] = trends[money_columns].round(2)

    return trends


def save_monthly_trends(
    trends: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Save monthly trends as a CSV report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    trends.to_csv(path, index=False)
    return path

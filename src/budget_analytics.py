
"""Monthly household budget analytics."""

import sqlite3
from pathlib import Path

import pandas as pd

from src.analytics import calculate_spending


PROJECT_ROOT = Path(__file__).resolve().parent.parent



def load_budgets(db_path=None) -> pd.DataFrame:
    """Load active budgets and convert minor units into major units."""
    if db_path is None:
        db_path = PROJECT_ROOT / "database" / "app.db"

    with sqlite3.connect(str(db_path)) as connection:
        budgets = pd.read_sql_query(
            """
            SELECT
                budget_id,
                user_id,
                category_id,
                strftime('%Y-%m', budget_month) AS month,
                budget_amount_minor / 100.0 AS budget_amount,
                currency
            FROM budgets
            WHERE status = 'active'
            """,
            connection,
        )

    return budgets

def validate_budget_categories(
    budgets: pd.DataFrame,
    categories: pd.DataFrame,
) -> pd.DataFrame:
    """Reject budgets that reference categories absent from the taxonomy."""
    if "category_id" not in budgets.columns:
        raise ValueError("Budgets must contain a category_id column.")

    if "category_id" not in categories.columns:
        raise ValueError("Categories must contain a category_id column.")

    valid_category_ids = set(categories["category_id"].dropna())
    budget_category_ids = set(budgets["category_id"].dropna())

    invalid_category_ids = budget_category_ids - valid_category_ids

    if budgets["category_id"].isna().any():
        raise ValueError("Budgets cannot have a missing category_id.")

    if invalid_category_ids:
        invalid_list = sorted(invalid_category_ids, key=str)
        raise ValueError(
            f"Unknown budget category IDs: {invalid_list}"
        )

    return budgets.copy()



def calculate_monthly_spending(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate net spending by user, month, and category."""
    required = {
        "user_id",
        "transaction_type",
        "amount",
        "transaction_date",
        "category_id",
    }
    missing = required - set(transactions.columns)

    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    calculated = calculate_spending(transactions)

    # Transaction dates are converted to calendar months.
    # The source timestamps should already reflect the intended reporting
    # timezone before this function is called.
    dates = pd.to_datetime(calculated["transaction_date"], errors="raise")
    calculated["month"] = dates.dt.strftime("%Y-%m")

    # Unknown categories remain separate instead of being silently assigned.
    calculated["category_id"] = calculated["category_id"].fillna(
        "uncategorized"
    )

    return (
        calculated.groupby(
            ["user_id", "month", "category_id"],
            dropna=False,
            as_index=False,
        )
        .agg(
            gross_expenses=("gross_expense", "sum"),
            refunds=("refund_credit", "sum"),
            net_spending=("net_spending", "sum"),
            transaction_count=("transaction_type", "size"),
        )
    )


def compare_budgets(
    budgets: pd.DataFrame,
    monthly_spending: pd.DataFrame,
) -> pd.DataFrame:
    """Compare each budget with actual spending for the same user/category/month."""
    required_budgets = {
        "user_id",
        "category_id",
        "month",
        "budget_amount",
    }
    missing_budgets = required_budgets - set(budgets.columns)

    if missing_budgets:
        raise ValueError(
            f"Missing required budget columns: {sorted(missing_budgets)}"
        )

    required_spending = {
        "user_id",
        "category_id",
        "month",
        "net_spending",
    }
    missing_spending = required_spending - set(monthly_spending.columns)

    if missing_spending:
        raise ValueError(
            "Missing required spending columns: "
            f"{sorted(missing_spending)}"
        )

    if budgets.duplicated(
        subset=["user_id", "category_id", "month"]
    ).any():
        raise ValueError(
            "Duplicate budgets found for the same user, category, and month."
        )

    actual = monthly_spending[
        ["user_id", "category_id", "month", "net_spending"]
    ].copy()

    comparison = budgets.merge(
        actual,
        on=["user_id", "category_id", "month"],
        how="left",
        validate="one_to_one",
    )

    comparison["net_spending"] = comparison["net_spending"].fillna(0.0)
    comparison["remaining_budget"] = (
        comparison["budget_amount"] - comparison["net_spending"]
    )

    comparison["budget_utilization_pct"] = (
        comparison["net_spending"]
        .div(comparison["budget_amount"].where(comparison["budget_amount"] > 0))
        .mul(100)
    )

    comparison["is_overspent"] = (
        comparison["net_spending"] > comparison["budget_amount"]
    )

    comparison["overspend_amount"] = (
        comparison["net_spending"] - comparison["budget_amount"]
    ).clip(lower=0)

    return comparison


def generate_budget_report(db_path=None) -> pd.DataFrame:
    """Load database data and return the monthly budget comparison."""
    if db_path is None:
        db_path = PROJECT_ROOT / "database" / "app.db"

    from src.analytics import load_transactions

    transactions = load_transactions(db_path)
    budgets = load_budgets(db_path)
    monthly = calculate_monthly_spending(transactions)

    return compare_budgets(budgets, monthly)


def save_budget_report(
    report: pd.DataFrame,
    output_path=None,
) -> Path:
    """Save the budget report as CSV."""
    if output_path is None:
        output_path = PROJECT_ROOT / "data" / "output" / "budget_report.csv"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False)

    return output_path

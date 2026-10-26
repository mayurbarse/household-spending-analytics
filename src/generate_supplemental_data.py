
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.config import load_config, resolve_path
from src.db import get_connection, initialize_database


EXPENSE_CATEGORY_IDS = [
    "CAT-001",  # Groceries
    "CAT-002",  # Housing
    "CAT-003",  # Transport
    "CAT-004",  # Utilities
    "CAT-005",  # Shopping
    "CAT-006",  # Healthcare
    "CAT-007",  # Entertainment
    "CAT-008",  # Education
]


def month_starts(start_date: date, end_date: date) -> list[date]:
    """Return the first day of each month in the configured date range."""
    current = start_date.replace(day=1)
    result = []

    while current <= end_date:
        result.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return result


def load_generated_csv(filename: str) -> pd.DataFrame:
    path = resolve_path(f"data/output/{filename}")

    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run python -m src.generate_data first."
        )

    return pd.read_csv(path)


def create_budgets(
    profiles: pd.DataFrame,
    months: list[date],
) -> list[dict]:
    """Create a monthly budget for each household and expense category."""
    budgets = []

    # Illustrative monthly limits in rupees, converted to paise.
    monthly_limits_rupees = {
        "CAT-001": 8000,
        "CAT-002": 15000,
        "CAT-003": 3500,
        "CAT-004": 3000,
        "CAT-005": 4000,
        "CAT-006": 2500,
        "CAT-007": 2000,
        "CAT-008": 5000,
    }

    for profile in profiles.to_dict("records"):
        user_id = profile["user_id"]

        for month in months:
            for category_id in EXPENSE_CATEGORY_IDS:
                budget_id = (
                    f"BUD-{user_id}-{month.strftime('%Y%m')}-{category_id}"
                )

                budgets.append({
                    "budget_id": budget_id,
                    "user_id": user_id,
                    "category_id": category_id,
                    "budget_month": month.isoformat(),
                    "budget_amount_minor": (
                        monthly_limits_rupees[category_id] * 100
                    ),
                    "currency": "INR",
                    "status": "active",
                })

    return budgets


def create_recurring_series(
    profiles: pd.DataFrame,
    accounts: pd.DataFrame,
    merchants: pd.DataFrame,
    end_date: date,
) -> list[dict]:
    """Create illustrative recurring salary and household bill series."""
    account_by_user = {}

    for account in accounts.to_dict("records"):
        if account["account_type"] == "checking":
            account_by_user[account["user_id"]] = account["account_id"]

    merchant_by_name = {
        row["canonical_name"]: row["merchant_id"]
        for row in merchants.to_dict("records")
    }

    templates = [
        {
            "series_type": "salary",
            "merchant_name": "Employer Payroll",
            "expected_amount_minor": 6000000,
            "cadence": "monthly",
            "expected_day": 1,
        },
        {
            "series_type": "rent",
            "merchant_name": "Home Rentals",
            "expected_amount_minor": 1500000,
            "cadence": "monthly",
            "expected_day": 5,
        },
        {
            "series_type": "subscription",
            "merchant_name": "StreamFlix",
            "expected_amount_minor": 69900,
            "cadence": "monthly",
            "expected_day": 15,
        },
        {
            "series_type": "utility",
            "merchant_name": "City Electricity Board",
            "expected_amount_minor": 180000,
            "cadence": "monthly",
            "expected_day": 20,
        },
    ]

    series = []

    for profile in profiles.to_dict("records"):
        user_id = profile["user_id"]
        account_id = account_by_user[user_id]

        for template in templates:
            recurring_id = (
                f"REC-{user_id}-{template['series_type'].upper()}"
            )

            next_date = date(2026, 11, template["expected_day"])
            if next_date > end_date:
                next_date = end_date

            series.append({
                "recurring_id": recurring_id,
                "account_id": account_id,
                "merchant_id": merchant_by_name[
                    template["merchant_name"]
                ],
                "series_type": template["series_type"],
                "expected_amount_minor": template[
                    "expected_amount_minor"
                ],
                "currency": "INR",
                "cadence": template["cadence"],
                "expected_day": template["expected_day"],
                "start_date": "2026-01-01",
                "end_date": end_date.isoformat(),
                "next_expected_date": next_date.isoformat(),
                "status": "active",
            })

    return series


def write_ground_truth(
    transactions: pd.DataFrame,
    recurring_series: list[dict],
) -> None:
    """Record known edge cases and their expected analytical treatment."""
    scenarios = []

    # Case 1: Both sides of an internal transfer must not be treated
    # as household spending.
    transfer_rows = transactions[
        transactions["transaction_type"] == "transfer"
    ]

    if not transfer_rows.empty:
        group_id = transfer_rows.iloc[0]["transfer_group_id"]
        pair = transfer_rows[
            transfer_rows["transfer_group_id"] == group_id
        ]

        scenarios.append({
            "scenario_id": "GT-001",
            "scenario_type": "internal_transfer_double_count",
            "entity_ids": ",".join(pair["transaction_id"].astype(str)),
            "expected_treatment": "Exclude both transfer legs from spending.",
            "actual_observation": (
                f"Two linked transfer records share group {group_id}."
            ),
            "status": "labelled",
        })
    else:
        raise ValueError(
            "No transfer pairs found. Check transaction generation."
        )

    # Case 2: A refund must offset spending rather than become a
    # positive expense.
    refunds = transactions[
        transactions["transaction_type"] == "refund"
    ]

    if not refunds.empty:
        refund = refunds.iloc[0]
        scenarios.append({
            "scenario_id": "GT-002",
            "scenario_type": "refund_misclassified_as_expense",
            "entity_ids": str(refund["transaction_id"]),
            "expected_treatment": (
                "Treat as a refund/credit and offset eligible spending; "
                "do not add it as a positive expense."
            ),
            "actual_observation": (
                f"Refund amount is {refund['amount_minor']} paise "
                "and should be handled according to transaction type."
            ),
            "status": "labelled",
        })
    else:
        raise ValueError("No refund transactions found.")

    # Case 3: An expected recurring occurrence deliberately has no
    # linked transaction in the recurring-transaction link table.
    subscriptions = [
        item for item in recurring_series
        if item["series_type"] == "subscription"
    ]

    if subscriptions:
        missing = subscriptions[0]
        scenarios.append({
            "scenario_id": "GT-003",
            "scenario_type": "missing_recurring_occurrence",
            "entity_ids": missing["recurring_id"],
            "expected_treatment": (
                "Flag the expected occurrence for review when no "
                "qualifying transaction matches it."
            ),
            "actual_observation": (
                "No recurring transaction link is created for this "
                "series in the synthetic baseline."
            ),
            "expected_occurrence_date": missing["next_expected_date"],
            "status": "labelled",
        })

    # Case 4: UTC timestamp converts to the next calendar day in India.
    scenarios.append({
        "scenario_id": "GT-004",
        "scenario_type": "timezone_date_boundary",
        "entity_ids": "TZ-CASE-001",
        "expected_treatment": (
            "Convert UTC to Asia/Kolkata before assigning the local "
            "transaction date."
        ),
        "actual_observation": (
            "2026-01-01T20:00:00Z corresponds to "
            "2026-01-02 01:30:00 in Asia/Kolkata."
        ),
        "example_utc_timestamp": "2026-01-01T20:00:00Z",
        "expected_local_date": "2026-01-02",
        "status": "labelled",
    })

    # Case 5: A budget referencing a nonexistent category should be
    # rejected, not inserted into the database.
    scenarios.append({
        "scenario_id": "GT-005",
        "scenario_type": "budget_category_not_in_taxonomy",
        "entity_ids": "BUD-INVALID-001",
        "expected_treatment": (
            "Reject the budget because CAT-999 is not a valid category."
        ),
        "actual_observation": (
            "This is a labelled invalid-input test case; it is not "
            "inserted into the database."
        ),
        "invalid_category_id": "CAT-999",
        "status": "labelled",
    })

    output_dir = resolve_path("data/ground_truth")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "edge_case_scenarios.csv"
    pd.DataFrame(scenarios).to_csv(
        output_path,
        index=False,
        encoding="utf-8",
    )

    print(f"Saved: data/ground_truth/edge_case_scenarios.csv "
          f"({len(scenarios)} scenarios)")


def main() -> None:
    config = load_config()
    rng = np.random.default_rng(int(config["seed"]))

    start_date = date.fromisoformat(
        config["date_range"]["start_date"]
    )
    end_date = date.fromisoformat(
        config["date_range"]["end_date"]
    )

    profiles = load_generated_csv("user_profiles.csv")
    accounts = load_generated_csv("accounts.csv")
    merchants = load_generated_csv("merchants.csv")
    transactions = load_generated_csv("transactions.csv")

    months = month_starts(start_date, end_date)

    budgets = create_budgets(profiles, months)
    recurring_series = create_recurring_series(
        profiles, accounts, merchants, end_date
    )

    # Deterministic check: expected amounts are positive and the
    # random generator is seeded for future extensibility.
    assert all(
        item["budget_amount_minor"] >= 0 for item in budgets
    )
    assert all(
        item["expected_amount_minor"] > 0
        for item in recurring_series
    )

    initialize_database()
    connection = get_connection()

    try:
        connection.execute("BEGIN")

        # Remove prior generated dependent records before replacing them.
        connection.execute("DELETE FROM recurring_transaction_links")
        connection.execute("DELETE FROM recurring_series")
        connection.execute("DELETE FROM budgets")

        connection.executemany(
            """
            INSERT INTO budgets
            (budget_id, user_id, category_id, budget_month,
             budget_amount_minor, currency, status)
            VALUES
            (:budget_id, :user_id, :category_id, :budget_month,
             :budget_amount_minor, :currency, :status)
            """,
            budgets,
        )

        connection.executemany(
            """
            INSERT INTO recurring_series
            (recurring_id, account_id, merchant_id, series_type,
             expected_amount_minor, currency, cadence, expected_day,
             start_date, end_date, next_expected_date, status)
            VALUES
            (:recurring_id, :account_id, :merchant_id, :series_type,
             :expected_amount_minor, :currency, :cadence, :expected_day,
             :start_date, :end_date, :next_expected_date, :status)
            """,
            recurring_series,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    write_ground_truth(transactions, recurring_series)

    output_dir = resolve_path("data/output")
    pd.DataFrame(budgets).to_csv(
        output_dir / "budgets.csv", index=False, encoding="utf-8"
    )
    pd.DataFrame(recurring_series).to_csv(
        output_dir / "recurring_series.csv",
        index=False,
        encoding="utf-8",
    )

    print("\nSupplemental data generated successfully.")
    print(f"Monthly budgets: {len(budgets):,}")
    print(f"Recurring series: {len(recurring_series):,}")
    print("Ground-truth scenarios: 5")


if __name__ == "__main__":
    main()

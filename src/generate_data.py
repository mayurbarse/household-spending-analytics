
import random
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from faker import Faker

from src.config import load_config, resolve_path
from src.db import get_connection, initialize_database


fake = Faker("en_IN")

REGIONS = ["North", "South", "East", "West", "Central"]
INCOME_BANDS = ["low", "lower_middle", "middle", "upper_middle", "high"]

MERCHANT_NAMES = [
    ("FreshMart Grocery", "grocery"),
    ("City Supermarket", "grocery"),
    ("Metro Fuel", "fuel"),
    ("City Electricity Board", "utility"),
    ("Water Services", "utility"),
    ("QuickRide", "transport"),
    ("Urban Clothing", "shopping"),
    ("HealthPlus Pharmacy", "healthcare"),
    ("StreamFlix", "subscription"),
    ("Home Rentals", "housing"),
    ("School Services", "education"),
    ("Cafe Corner", "restaurant"),
    ("Food Delivery Hub", "restaurant"),
    ("Electro World", "electronics"),
    ("Movie House", "entertainment"),
    ("Employer Payroll", "employer"),
    ("Bank Services", "bank"),
]

CATEGORY_DEFINITIONS = [
    ("CAT-001", "GROCERIES", "Food & Groceries", "expense"),
    ("CAT-002", "HOUSING", "Housing & Rent", "expense"),
    ("CAT-003", "TRANSPORT", "Transport", "expense"),
    ("CAT-004", "UTILITIES", "Utilities", "expense"),
    ("CAT-005", "SHOPPING", "Shopping", "expense"),
    ("CAT-006", "HEALTHCARE", "Healthcare", "expense"),
    ("CAT-007", "ENTERTAINMENT", "Entertainment", "expense"),
    ("CAT-008", "EDUCATION", "Education", "expense"),
    ("CAT-009", "FEES", "Bank Fees", "expense"),
    ("CAT-010", "OTHER_EXPENSE", "Other Expenses", "expense"),
    ("CAT-011", "SALARY", "Salary", "income"),
    ("CAT-012", "OTHER_INCOME", "Other Income", "income"),
    ("CAT-013", "TRANSFER", "Internal Transfer", "transfer"),
    ("CAT-014", "REFUND", "Refund", "refund"),
    ("CAT-015", "OTHER", "Other Transactions", "other"),
]

EXPENSE_CATEGORIES = [
    "CAT-001", "CAT-002", "CAT-003", "CAT-004", "CAT-005",
    "CAT-006", "CAT-007", "CAT-008", "CAT-010",
]

CATEGORY_BY_MERCHANT_TYPE = {
    "grocery": "CAT-001",
    "fuel": "CAT-003",
    "utility": "CAT-004",
    "transport": "CAT-003",
    "shopping": "CAT-005",
    "healthcare": "CAT-006",
    "subscription": "CAT-007",
    "housing": "CAT-002",
    "education": "CAT-008",
    "restaurant": "CAT-001",
    "electronics": "CAT-005",
    "entertainment": "CAT-007",
    "bank": "CAT-009",
}

CATEGORY_NAMES = {
    row[0]: row[2] for row in CATEGORY_DEFINITIONS
}

MERCHANT_TYPES = {
    row[0]: row[1] for row in MERCHANT_NAMES
}


def utc_iso(value: datetime) -> str:
    """Convert an aware datetime to a consistent UTC ISO string."""
    return value.astimezone(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def create_profiles(profile_count: int, rng) -> list[dict]:
    profiles = []

    for i in range(1, profile_count + 1):
        profiles.append({
            "user_id": f"USR-{i:06d}",
            "household_size": int(rng.integers(1, 7)),
            "region": str(rng.choice(REGIONS)),
            "income_band": str(rng.choice(INCOME_BANDS)),
            "currency": "INR",
            "created_at": "2026-01-01T00:00:00Z",
            "status": "active",
        })

    return profiles


def create_accounts(profiles: list[dict]) -> list[dict]:
    accounts = []

    for profile in profiles:
        user_id = profile["user_id"]

        accounts.append({
            "account_id": f"ACC-{user_id}-01",
            "user_id": user_id,
            "account_type": "checking",
            "opening_date": "2025-01-01",
            "status": "active",
        })

        accounts.append({
            "account_id": f"ACC-{user_id}-02",
            "user_id": user_id,
            "account_type": "savings",
            "opening_date": "2025-01-01",
            "status": "active",
        })

    return accounts


def create_merchants() -> list[dict]:
    merchants = []

    for i, (name, merchant_type) in enumerate(
        MERCHANT_NAMES, start=1
    ):
        merchants.append({
            "merchant_id": f"MER-{i:04d}",
            "canonical_name": name,
            "merchant_type": merchant_type,
            "created_at": "2026-01-01T00:00:00Z",
        })

    return merchants


def create_categories() -> list[dict]:
    categories = []

    for category_id, code, name, category_type in CATEGORY_DEFINITIONS:
        categories.append({
            "category_id": category_id,
            "category_code": code,
            "category_name": name,
            "parent_category_id": None,
            "category_type": category_type,
            "status": "active",
        })

    return categories


def random_local_datetime(start_date: date, end_date: date, rng) -> datetime:
    """Generate a random timestamp in the reporting timezone."""
    total_days = (end_date - start_date).days

    day_offset = int(rng.integers(0, total_days + 1))
    seconds_of_day = int(rng.integers(0, 86400))

    selected_day = start_date + timedelta(days=day_offset)
    selected_datetime = datetime.combine(
        selected_day,
        time(0, 0),
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    return selected_datetime + timedelta(seconds=seconds_of_day)


def build_transaction(
    transaction_number: int,
    account: dict,
    merchant: dict | None,
    transaction_type: str,
    amount_minor: int,
    category_id: str,
    local_datetime: datetime,
    rng,
    transfer_group_id: str | None = None,
) -> dict:
    utc_datetime = local_datetime.astimezone(timezone.utc)

    if transaction_type == "salary":
        descriptor = "Monthly salary payment"
    elif transaction_type == "refund":
        descriptor = (
            f"Refund from {merchant['canonical_name']}"
            if merchant else "Customer refund"
        )
    elif transaction_type == "transfer":
        descriptor = "Internal account transfer"
    elif transaction_type == "fee":
        descriptor = "Bank service fee"
    elif transaction_type == "bill_payment":
        descriptor = (
            f"Bill payment to {merchant['canonical_name']}"
            if merchant else "Bill payment"
        )
    else:
        descriptor = (
            f"Payment at {merchant['canonical_name']}"
            if merchant else "Miscellaneous transaction"
        )

    return {
        "transaction_id": f"TXN-2026-{transaction_number:08d}",
        "account_id": account["account_id"],
        "merchant_id": merchant["merchant_id"] if merchant else None,
        "transaction_ts_utc": utc_iso(utc_datetime),
        "recorded_at_utc": utc_iso(
            utc_datetime + timedelta(minutes=int(rng.integers(0, 15)))
        ),
        "local_transaction_date": local_datetime.date().isoformat(),
        "reporting_timezone": "Asia/Kolkata",
        "descriptor": descriptor,
        "transaction_type": transaction_type,
        "amount_minor": int(amount_minor),
        "currency": "INR",
        "category_id": category_id,
        "applied_rule_id": None,
        "linked_transaction_id": None,
        "transfer_group_id": transfer_group_id,
        "status": "posted",
    }


def create_transactions(
    profiles: list[dict],
    accounts: list[dict],
    merchants: list[dict],
    transaction_count: int,
    months: int,
    start_date: date,
    end_date: date,
    rng,
) -> list[dict]:
    if transaction_count < 1:
        raise ValueError("Transaction count must be at least 1.")

    if months < 1:
        raise ValueError("Months must be at least 1.")

    if start_date > end_date:
        raise ValueError("Start date must not be after end date.")

    accounts_by_user = {}
    for account in accounts:
        accounts_by_user.setdefault(account["user_id"], []).append(account)

    merchants_by_type = {}
    for merchant in merchants:
        merchants_by_type.setdefault(
            merchant["merchant_type"], []
        ).append(merchant)

    # Keep a stable monthly salary pattern to support later
    # recurring-payment analysis.
    salary_events = []

    for profile in profiles:
        user_accounts = accounts_by_user[profile["user_id"]]
        checking_account = user_accounts[0]

        for month_offset in range(months):
            month_start = (
                start_date.replace(day=1)
                + timedelta(days=32 * month_offset)
            ).replace(day=1)

            if month_start > end_date:
                break

            # Keep dates within the configured date range.
            month_end = (
                (month_start.replace(day=28) + timedelta(days=4))
                .replace(day=1) - timedelta(days=1)
            )
            month_end = min(month_end, end_date)
            actual_start = max(month_start, start_date)

            if actual_start > month_end:
                continue

            pay_day = min(1, month_end.day)
            pay_date = max(actual_start, month_start.replace(day=pay_day))

            salary_events.append((checking_account, pay_date))

    # Reserve a small portion of the dataset for paired transfers.
    transfer_pair_count = transaction_count // 100
    transfer_pair_count = min(
        transfer_pair_count,
        max(0, (transaction_count - 1) // 2),
    )

    # If the dataset is too small to contain every salary event,
    # keep a deterministic subset.
    salary_events = salary_events[:max(
        0, transaction_count - (transfer_pair_count * 2)
    )]

    reserved_count = len(salary_events) + transfer_pair_count * 2
    regular_count = transaction_count - reserved_count

    transactions = []
    next_number = 1

    # Salary payments are generated once per household per month.
    payroll_merchants = merchants_by_type["employer"]

    for account, pay_date in salary_events:
        local_datetime = datetime.combine(
            pay_date,
            time(9, 0),
            tzinfo=ZoneInfo("Asia/Kolkata"),
        )

        salary_amount = int(
            rng.integers(30000, 150001)
        ) * 100

        transactions.append(build_transaction(
            next_number,
            account,
            payroll_merchants[0],
            "salary",
            salary_amount,
            "CAT-011",
            local_datetime,
            rng,
        ))
        next_number += 1

    # Generate matched transfer pairs between two accounts belonging
    # to the same household. The two sides have equal, opposite amounts.
    eligible_users = [
        profile for profile in profiles
        if len(accounts_by_user[profile["user_id"]]) >= 2
    ]

    if transfer_pair_count and not eligible_users:
        raise ValueError(
            "Paired transfers require at least one household "
            "with two accounts."
        )

    for pair_number in range(1, transfer_pair_count + 1):
        profile = eligible_users[
            int(rng.integers(0, len(eligible_users)))
        ]
        user_accounts = accounts_by_user[profile["user_id"]]
        source, destination = user_accounts[:2]

        local_datetime = random_local_datetime(
            start_date, end_date, rng
        )
        amount = int(rng.integers(500, 20001)) * 100
        group_id = f"TRF-{pair_number:08d}"

        transactions.append(build_transaction(
            next_number, source, None, "transfer", -amount,
            "CAT-013", local_datetime, rng, group_id,
        ))
        next_number += 1

        transactions.append(build_transaction(
            next_number, destination, None, "transfer", amount,
            "CAT-013", local_datetime + timedelta(seconds=2),
            rng, group_id,
        ))
        next_number += 1

    
    # Keep employers and banks out of ordinary merchant transactions.
    expense_merchants = [
        merchant for merchant in merchants
        if merchant["merchant_type"] not in {"employer", "bank"}
    ]

    # Typical transaction ranges in rupees, selected by merchant type.
    # These are synthetic-data assumptions, not financial advice.
    purchase_ranges = {
        "grocery": (150, 2500),
        "fuel": (300, 4000),
        "utility": (300, 6000),
        "transport": (50, 1200),
        "shopping": (200, 5000),
        "healthcare": (100, 3000),
        "subscription": (100, 1500),
        "housing": (5000, 25000),
        "education": (500, 10000),
        "restaurant": (100, 1800),
        "electronics": (500, 15000),
        "entertainment": (100, 2000),
    }

    bill_ranges = {
        "grocery": (200, 2000),
        "fuel": (300, 2500),
        "utility": (500, 6000),
        "transport": (100, 1500),
        "shopping": (200, 2500),
        "healthcare": (100, 2000),
        "subscription": (100, 1500),
        "housing": (5000, 25000),
        "education": (500, 8000),
        "restaurant": (100, 1200),
        "electronics": (500, 5000),
        "entertainment": (100, 1500),
    }

    for transaction_index in range(regular_count):
        if transaction_index % 10000 == 0:
            print(
                f"Generating regular transactions: "
                f"{transaction_index:,}/{regular_count:,}",
                flush=True,
            )

        account = accounts[int(rng.integers(0, len(accounts)))]
        local_datetime = random_local_datetime(
            start_date, end_date, rng
        )

        roll = float(rng.random())

        if roll < 0.72:
            merchant = expense_merchants[
                int(rng.integers(0, len(expense_merchants)))
            ]
            merchant_type = merchant["merchant_type"]
            category_id = CATEGORY_BY_MERCHANT_TYPE.get(
                merchant_type, "CAT-010"
            )
            transaction_type = "purchase"

            low, high = purchase_ranges.get(
                merchant_type, (100, 2500)
            )
            amount = -int(rng.integers(low, high + 1)) * 100

        elif roll < 0.82:
            merchant = expense_merchants[
                int(rng.integers(0, len(expense_merchants)))
            ]
            category_id = "CAT-014"
            transaction_type = "refund"
            amount = int(rng.integers(100, 3001)) * 100

        elif roll < 0.90:
            merchant = merchants_by_type["bank"][0]
            category_id = "CAT-009"
            transaction_type = "fee"
            amount = -int(rng.integers(10, 301)) * 100

        elif roll < 0.98:
            merchant = expense_merchants[
                int(rng.integers(0, len(expense_merchants)))
            ]
            merchant_type = merchant["merchant_type"]
            category_id = CATEGORY_BY_MERCHANT_TYPE.get(
                merchant_type, "CAT-010"
            )
            transaction_type = "bill_payment"

            low, high = bill_ranges.get(
                merchant_type, (200, 2500)
            )
            amount = -int(rng.integers(low, high + 1)) * 100

        else:
            merchant = None
            category_id = "CAT-015"
            transaction_type = "other"
            amount = -int(rng.integers(100, 2001)) * 100

        transactions.append(build_transaction(
            next_number,
            account,
            merchant,
            transaction_type,
            amount,
            category_id,
            local_datetime,
            rng,
        ))
        next_number += 1


    # Stable ordering makes output easier to inspect.
    transactions.sort(
        key=lambda row: (
            row["transaction_ts_utc"],
            row["transaction_id"],
        )
    )

    return transactions


def validate_data(
    profiles: list[dict],
    accounts: list[dict],
    merchants: list[dict],
    categories: list[dict],
    transactions: list[dict],
    expected_transaction_count: int,
) -> None:
    assert len(profiles) == len({
        row["user_id"] for row in profiles
    }), "Duplicate user IDs found."

    assert len(accounts) == len({
        row["account_id"] for row in accounts
    }), "Duplicate account IDs found."

    assert len(merchants) == len({
        row["merchant_id"] for row in merchants
    }), "Duplicate merchant IDs found."

    assert len(transactions) == expected_transaction_count, (
        f"Expected {expected_transaction_count} transactions; "
        f"generated {len(transactions)}."
    )

    valid_users = {row["user_id"] for row in profiles}
    valid_accounts = {row["account_id"] for row in accounts}
    valid_merchants = {row["merchant_id"] for row in merchants}
    valid_categories = {row["category_id"] for row in categories}

    for account in accounts:
        assert account["user_id"] in valid_users

    for transaction in transactions:
        assert transaction["account_id"] in valid_accounts
        assert transaction["category_id"] in valid_categories
        assert transaction["amount_minor"] != 0

        if transaction["merchant_id"] is not None:
            assert transaction["merchant_id"] in valid_merchants

        if transaction["transaction_type"] in {
            "salary", "refund", "reversal"
        }:
            assert transaction["amount_minor"] > 0

        if transaction["transaction_type"] in {
            "purchase", "fee", "bill_payment"
        }:
            assert transaction["amount_minor"] < 0

    transfer_rows = [
        row for row in transactions
        if row["transaction_type"] == "transfer"
    ]

    groups = {}
    for row in transfer_rows:
        groups.setdefault(row["transfer_group_id"], []).append(row)

    for group_id, rows in groups.items():
        assert group_id is not None
        assert len(rows) == 2, (
            f"Transfer group {group_id} must have exactly two sides."
        )
        assert sum(row["amount_minor"] for row in rows) == 0, (
            f"Transfer group {group_id} does not balance."
        )


def save_csv_outputs(
    profiles: list[dict],
    accounts: list[dict],
    merchants: list[dict],
    categories: list[dict],
    transactions: list[dict],
) -> None:
    output_dir = resolve_path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "user_profiles.csv": profiles,
        "accounts.csv": accounts,
        "merchants.csv": merchants,
        "categories.csv": categories,
        "transactions.csv": transactions,
    }

    for filename, rows in datasets.items():
        pd.DataFrame(rows).to_csv(
            output_dir / filename,
            index=False,
            encoding="utf-8",
        )
        print(f"Saved: data/output/{filename} ({len(rows):,} rows)")


def replace_database_data(
    profiles: list[dict],
    accounts: list[dict],
    merchants: list[dict],
    categories: list[dict],
    transactions: list[dict],
) -> None:
    """Replace generated records in dependency-safe order."""
    connection = get_connection()

    try:
        connection.execute("BEGIN")

        # Delete dependent records first so rerunning the generator
        # does not leave stale records or violate foreign keys.
        for table in [
            "exceptions",
            "state_events",
            "recurring_transaction_links",
            "insights",
            "recurring_series",
            "budgets",
            "transactions",
            "category_rules",
            "merchant_aliases",
            "merchants",
            "categories",
            "accounts",
            "user_profiles",
        ]:
            connection.execute(f"DELETE FROM {table}")

        connection.executemany(
            """
            INSERT INTO user_profiles
            (user_id, household_size, region, income_band,
             currency, created_at, status)
            VALUES
            (:user_id, :household_size, :region, :income_band,
             :currency, :created_at, :status)
            """,
            profiles,
        )

        connection.executemany(
            """
            INSERT INTO accounts
            (account_id, user_id, account_type, opening_date, status)
            VALUES
            (:account_id, :user_id, :account_type, :opening_date, :status)
            """,
            accounts,
        )

        connection.executemany(
            """
            INSERT INTO merchants
            (merchant_id, canonical_name, merchant_type, created_at)
            VALUES
            (:merchant_id, :canonical_name, :merchant_type, :created_at)
            """,
            merchants,
        )

        connection.executemany(
            """
            INSERT INTO categories
            (category_id, category_code, category_name,
             parent_category_id, category_type, status)
            VALUES
            (:category_id, :category_code, :category_name,
             :parent_category_id, :category_type, :status)
            """,
            categories,
        )

        connection.executemany(
            """
            INSERT INTO transactions
            (transaction_id, account_id, merchant_id,
             transaction_ts_utc, recorded_at_utc,
             local_transaction_date, reporting_timezone,
             descriptor, transaction_type, amount_minor, currency,
             category_id, applied_rule_id, linked_transaction_id,
             transfer_group_id, status)
            VALUES
            (:transaction_id, :account_id, :merchant_id,
             :transaction_ts_utc, :recorded_at_utc,
             :local_transaction_date, :reporting_timezone,
             :descriptor, :transaction_type, :amount_minor, :currency,
             :category_id, :applied_rule_id, :linked_transaction_id,
             :transfer_group_id, :status)
            """,
            transactions,
        )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    config = load_config()
    seed = int(config["seed"])

    random.seed(seed)
    Faker.seed(seed)
    fake.seed_instance(seed)
    rng = np.random.default_rng(seed)

    profile_count = int(config["scale"]["profiles"])
    transaction_count = int(config["scale"]["transactions"])
    months = int(config["scale"]["months"])

    start_date = date.fromisoformat(
        config["date_range"]["start_date"]
    )
    end_date = date.fromisoformat(
        config["date_range"]["end_date"]
    )

    print("Generating synthetic financial data...")
    print(f"Seed: {seed}")
    print(f"Profiles: {profile_count:,}")
    print(f"Target transactions: {transaction_count:,}")

    profiles = create_profiles(profile_count, rng)
    accounts = create_accounts(profiles)
    merchants = create_merchants()
    categories = create_categories()

    transactions = create_transactions(
        profiles=profiles,
        accounts=accounts,
        merchants=merchants,
        transaction_count=transaction_count,
        months=months,
        start_date=start_date,
        end_date=end_date,
        rng=rng,
    )

    validate_data(
        profiles,
        accounts,
        merchants,
        categories,
        transactions,
        transaction_count,
    )

    initialize_database()
    replace_database_data(
        profiles,
        accounts,
        merchants,
        categories,
        transactions,
    )
    save_csv_outputs(
        profiles,
        accounts,
        merchants,
        categories,
        transactions,
    )

    transaction_df = pd.DataFrame(transactions)
    print("\nTransaction type counts:")
    print(transaction_df["transaction_type"].value_counts().to_string())

    print("\nValidation passed.")
    print(f"Profiles generated: {len(profiles):,}")
    print(f"Accounts generated: {len(accounts):,}")
    print(f"Merchants generated: {len(merchants):,}")
    print(f"Categories generated: {len(categories):,}")
    print(f"Transactions generated: {len(transactions):,}")
    print("Database updated and CSV exports created.")


if __name__ == "__main__":
    main()

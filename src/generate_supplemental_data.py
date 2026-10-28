
import json
import re
from datetime import date, timedelta

import pandas as pd

from src.config import load_config, resolve_path
from src.db import get_connection, initialize_database


EXPENSE_CATEGORY_IDS = [
    "CAT-001", "CAT-002", "CAT-003", "CAT-004",
    "CAT-005", "CAT-006", "CAT-007", "CAT-008",
]

MERCHANT_CATEGORY = {
    "FreshMart Grocery": "CAT-001",
    "City Supermarket": "CAT-001",
    "Metro Fuel": "CAT-003",
    "City Electricity Board": "CAT-004",
    "Water Services": "CAT-004",
    "QuickRide": "CAT-003",
    "Urban Clothing": "CAT-005",
    "HealthPlus Pharmacy": "CAT-006",
    "StreamFlix": "CAT-007",
    "Home Rentals": "CAT-002",
    "School Services": "CAT-008",
    "Cafe Corner": "CAT-001",
    "Food Delivery Hub": "CAT-001",
    "Electro World": "CAT-005",
    "Movie House": "CAT-007",
    "Employer Payroll": "CAT-011",
    "Bank Services": "CAT-009",
}

TYPE_CATEGORY = {
    "salary": "CAT-011",
    "refund": "CAT-014",
    "transfer": "CAT-013",
    "fee": "CAT-009",
    "other": "CAT-015",
}


def month_starts(start_date: date, end_date: date) -> list[date]:
    current = start_date.replace(day=1)
    result = []
    while current <= end_date:
        result.append(current)
        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )
    return result


def load_csv(filename: str) -> pd.DataFrame:
    path = resolve_path(f"data/output/{filename}")
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run python -m src.generate_data first."
        )
    return pd.read_csv(path)


def create_budgets(profiles, months):
    limits = {
        "CAT-001": 8000, "CAT-002": 15000,
        "CAT-003": 3500, "CAT-004": 3000,
        "CAT-005": 4000, "CAT-006": 2500,
        "CAT-007": 2000, "CAT-008": 5000,
    }
    rows = []
    for profile in profiles.to_dict("records"):
        user_id = profile["user_id"]
        for month in months:
            for category_id in EXPENSE_CATEGORY_IDS:
                rows.append({
                    "budget_id": (
                        f"BUD-{user_id}-{month:%Y-%m}-"
                        f"{category_id.removeprefix('CAT-')}"
                    ),
                    "user_id": user_id,
                    "category_id": category_id,
                    "budget_month": month.isoformat(),
                    "budget_amount_minor": limits[category_id] * 100,
                    "currency": profile.get("currency", "INR"),
                    "status": "active",
                })
    return rows


def create_recurring_series(profiles, accounts, merchants, start_date, end_date):
    checking = {
        row["user_id"]: row["account_id"]
        for row in accounts.to_dict("records")
        if row["account_type"] == "checking"
    }
    merchant_ids = {
        row["canonical_name"]: row["merchant_id"]
        for row in merchants.to_dict("records")
    }

    templates = [
        ("salary", "Employer Payroll", 6000000, 1),
        ("rent", "Home Rentals", 1500000, 5),
        ("subscription", "StreamFlix", 69900, 15),
        ("utility", "City Electricity Board", 180000, 20),
    ]
    rows = []
    for profile in profiles.to_dict("records"):
        user_id = profile["user_id"]
        for kind, merchant_name, amount, day in templates:
            expected_day = min(day, end_date.day)
            next_date = date(end_date.year, end_date.month, expected_day)
            if next_date < start_date:
                next_date = start_date
            rows.append({
                "recurring_id": f"REC-{user_id}-{kind.upper()}",
                "account_id": checking[user_id],
                "merchant_id": merchant_ids[merchant_name],
                "series_type": kind,
                "expected_amount_minor": amount,
                "currency": profile.get("currency", "INR"),
                "cadence": "monthly",
                "expected_day": day,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "next_expected_date": next_date.isoformat(),
                "status": "active",
            })
    return rows


def create_aliases(merchants):
    rows = []
    number = 1
    for merchant in merchants.to_dict("records"):
        canonical = str(merchant["canonical_name"])
        variants = {
            canonical.lower(),
            re.sub(r"[^a-z0-9 ]", "", canonical.lower()).replace(" ", ""),
        }
        for alias in sorted(variants):
            normalized = re.sub(r"[^a-z0-9]", "", alias.lower())
            rows.append({
                "alias_id": f"ALS-{number:06d}",
                "merchant_id": merchant["merchant_id"],
                "alias": alias,
                "normalized_alias": normalized,
                "effective_from": "2026-01-01",
                "effective_to": None,
            })
            number += 1
    # Avoid duplicate normalized aliases if a name normalizes identically.
    unique = {}
    for row in rows:
        unique[(row["normalized_alias"], row["effective_from"])] = row
    result = list(unique.values())
    for number, row in enumerate(result, 1):
        row["alias_id"] = f"ALS-{number:06d}"
    return result


def create_rules(merchants):
    rows = []
    priority = 10

    for transaction_type, category_id in TYPE_CATEGORY.items():
        rows.append({
            "rule_id": f"RULE-TYPE-{transaction_type.upper()}",
            "rule_name": f"Classify {transaction_type} transactions",
            "match_field": "transaction_type",
            "match_pattern": transaction_type,
            "match_mode": "exact",
            "category_id": category_id,
            "priority": priority,
            "effective_from": "2026-01-01",
            "effective_to": None,
            "status": "active",
        })
        priority += 1

    for merchant in merchants.to_dict("records"):
        name = str(merchant["canonical_name"])
        category_id = MERCHANT_CATEGORY.get(name, "CAT-015")
        rows.append({
            "rule_id": f"RULE-MER-{merchant['merchant_id']}",
            "rule_name": f"Classify merchant: {name}",
            "match_field": "merchant_name",
            "match_pattern": name,
            "match_mode": "exact",
            "category_id": category_id,
            "priority": 100,
            "effective_from": "2026-01-01",
            "effective_to": None,
            "status": "active",
        })
    return rows


def create_insights(transactions, profiles, budgets):
    tx = transactions.copy()
    tx["amount_minor"] = pd.to_numeric(tx["amount_minor"])
    tx["local_transaction_date"] = pd.to_datetime(
        tx["local_transaction_date"], errors="raise"
    )
    tx["month"] = tx["local_transaction_date"].dt.strftime("%Y-%m")

    # Transfers are excluded. Refunds are credits, not new expenses.
    eligible = tx[~tx["transaction_type"].isin(["transfer", "reversal"])]
    eligible = eligible[eligible["status"] == "posted"]

    monthly = eligible.groupby(
        [eligible["account_id"].str.extract(r"ACC-(USR-\d+)-")[0],
         "month"]
    )["amount_minor"].sum().reset_index()
    monthly.columns = ["user_id", "month", "net_amount_minor"]

    budget_df = pd.DataFrame(budgets)
    budget_totals = budget_df.groupby(
        ["user_id", budget_df["budget_month"].str.slice(0, 7)]
    )["budget_amount_minor"].sum().to_dict()

    rows = []
    for index, item in enumerate(monthly.to_dict("records"), 1):
        user_id = item["user_id"]
        month = item["month"]
        month_start = f"{month}-01"
        month_end = (
            pd.Period(month, freq="M").end_time.date().isoformat()
        )
        budget_total = budget_totals.get((user_id, month), 0)
        rows.append({
            "insight_id": f"INS-{index:08d}",
            "user_id": user_id,
            "period_start": month_start,
            "period_end": month_end,
            "insight_type": "monthly_net_cash_flow",
            "metric_value": round(item["net_amount_minor"] / 100, 2),
            "currency": "INR",
            "details_json": json.dumps({
                "net_amount_minor": int(item["net_amount_minor"]),
                "budget_total_minor": int(budget_total),
                "method": (
                    "Posted ledger amounts excluding transfers and reversals; "
                    "refunds remain credits."
                ),
            }, sort_keys=True),
            "created_at": f"{month_end}T23:59:59Z",
        })
    return rows


def write_ground_truth(transactions, recurring_series, output_dir):
    scenarios = []
    transfers = transactions[transactions["transaction_type"] == "transfer"]
    if not transfers.empty:
        group_id = transfers.iloc[0]["transfer_group_id"]
        pair = transfers[transfers["transfer_group_id"] == group_id]
        scenarios.append({
            "scenario_id": "GT-001",
            "scenario_type": "internal_transfer_double_count",
            "entity_ids": ",".join(pair["transaction_id"].astype(str)),
            "expected_treatment": "Exclude both transfer legs from spending.",
            "status": "labelled",
        })

    refunds = transactions[transactions["transaction_type"] == "refund"]
    if not refunds.empty:
        refund = refunds.iloc[0]
        scenarios.append({
            "scenario_id": "GT-002",
            "scenario_type": "refund_misclassified_as_expense",
            "entity_ids": str(refund["transaction_id"]),
            "expected_treatment": "Treat refund as a credit, not a positive expense.",
            "status": "labelled",
        })

    if recurring_series:
        item = next(
            (row for row in recurring_series
             if row["series_type"] == "subscription"),
            recurring_series[0],
        )
        scenarios.append({
            "scenario_id": "GT-003",
            "scenario_type": "missing_recurring_occurrence",
            "entity_ids": item["recurring_id"],
            "expected_treatment": "Review if no qualifying transaction matches the expected date.",
            "expected_occurrence_date": item["next_expected_date"],
            "status": "labelled",
        })

    scenarios.extend([
        {
            "scenario_id": "GT-004",
            "scenario_type": "timezone_date_boundary",
            "entity_ids": "TZ-CASE-001",
            "example_utc_timestamp": "2026-01-01T20:00:00Z",
            "expected_local_date": "2026-01-02",
            "expected_treatment": "Convert UTC to Asia/Kolkata before assigning the local date.",
            "status": "labelled",
        },
        {
            "scenario_id": "GT-005",
            "scenario_type": "budget_category_not_in_taxonomy",
            "entity_ids": "BUD-INVALID-001",
            "invalid_category_id": "CAT-999",
            "expected_treatment": "Reject the budget because CAT-999 is not a valid category.",
            "status": "labelled",
        },
    ])
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(scenarios).to_csv(
        output_dir / "edge_case_scenarios.csv", index=False
    )


def populate_database(budgets, series, aliases, rules, insights, transactions):
    connection = get_connection()
    try:
        connection.execute("BEGIN")

        # Rebuild only supplemental/generated records.
        for table in [
            "exceptions", "state_events", "recurring_transaction_links",
            "insights", "recurring_series", "budgets",
            "category_rules", "merchant_aliases",
        ]:
            connection.execute(f"DELETE FROM {table}")

        connection.executemany("""
            INSERT INTO merchant_aliases
            (alias_id, merchant_id, alias, normalized_alias,
             effective_from, effective_to)
            VALUES (:alias_id, :merchant_id, :alias, :normalized_alias,
                    :effective_from, :effective_to)
        """, aliases)

        connection.executemany("""
            INSERT INTO category_rules
            (rule_id, rule_name, match_field, match_pattern, match_mode,
             category_id, priority, effective_from, effective_to, status)
            VALUES (:rule_id, :rule_name, :match_field, :match_pattern,
                    :match_mode, :category_id, :priority, :effective_from,
                    :effective_to, :status)
        """, rules)

        connection.executemany("""
            INSERT INTO budgets
            (budget_id, user_id, category_id, budget_month,
             budget_amount_minor, currency, status)
            VALUES (:budget_id, :user_id, :category_id, :budget_month,
                    :budget_amount_minor, :currency, :status)
        """, budgets)

        connection.executemany("""
            INSERT INTO recurring_series
            (recurring_id, account_id, merchant_id, series_type,
             expected_amount_minor, currency, cadence, expected_day,
             start_date, end_date, next_expected_date, status)
            VALUES (:recurring_id, :account_id, :merchant_id, :series_type,
                    :expected_amount_minor, :currency, :cadence, :expected_day,
                    :start_date, :end_date, :next_expected_date, :status)
        """, series)

        connection.executemany("""
            INSERT INTO insights
            (insight_id, user_id, period_start, period_end, insight_type,
             metric_value, currency, details_json, created_at)
            VALUES (:insight_id, :user_id, :period_start, :period_end,
                    :insight_type, :metric_value, :currency, :details_json,
                    :created_at)
        """, insights)

        # Link observed transactions to a recurring series when the
        # account, merchant, transaction type and expected day agree.
        tx_rows = connection.execute("""
            SELECT transaction_id, account_id, merchant_id,
                   transaction_type, local_transaction_date, amount_minor
            FROM transactions
            WHERE status = 'posted'
              AND transaction_type IN ('salary', 'purchase', 'bill_payment')
        """).fetchall()

        by_key = {}
        for tx in tx_rows:
            key = (tx["account_id"], tx["merchant_id"])
            by_key.setdefault(key, []).append(tx)

        links = []
        exceptions = []
        events = []
        event_number = 1
        exception_number = 1

        for item in series:
            expected_type = {
                "salary": "salary",
                "rent": None,
                "subscription": None,
                "utility": None,
            }.get(item["series_type"])

            candidates = by_key.get(
                (item["account_id"], item["merchant_id"]), []
            )
            for tx in candidates:
                tx_date = date.fromisoformat(tx["local_transaction_date"])
                if tx_date < date.fromisoformat(item["start_date"]):
                    continue
                if tx_date > date.fromisoformat(item["end_date"]):
                    continue
                if expected_type and tx["transaction_type"] != expected_type:
                    continue
                if not expected_type and tx["transaction_type"] not in (
                    "purchase", "bill_payment"
                ):
                    continue

                # Require the same calendar day-of-month (with a three-day
                # tolerance) and an amount within a broad 50% tolerance.
                day_distance = abs(tx_date.day - int(item["expected_day"]))
                day_distance = min(day_distance, 31 - day_distance)
                if day_distance > 3:
                    continue
                expected_amount = int(item["expected_amount_minor"])
                if abs(abs(int(tx["amount_minor"])) - expected_amount) > expected_amount * 0.5:
                    continue

                links.append({
                    "recurring_id": item["recurring_id"],
                    "transaction_id": tx["transaction_id"],
                    "occurrence_date": tx_date.isoformat(),
                    "match_status": "matched",
                })

            events.append({
                "event_id": f"EVT-{event_number:08d}",
                "entity_type": "recurring_series",
                "entity_id": item["recurring_id"],
                "event_type": "series_created",
                "old_value_json": None,
                "new_value_json": json.dumps(item, sort_keys=True),
                "reason": "Synthetic baseline recurring series generation",
                "actor_type": "system",
                "occurred_at_utc": "2026-01-01T00:00:00Z",
            })
            event_number += 1

        connection.executemany("""
            INSERT OR IGNORE INTO recurring_transaction_links
            (recurring_id, transaction_id, occurrence_date, match_status)
            VALUES (:recurring_id, :transaction_id, :occurrence_date, :match_status)
        """, links)

        connection.executemany("""
            INSERT INTO state_events
            (event_id, entity_type, entity_id, event_type, old_value_json,
             new_value_json, reason, actor_type, occurred_at_utc)
            VALUES (:event_id, :entity_type, :entity_id, :event_type,
                    :old_value_json, :new_value_json, :reason, :actor_type,
                    :occurred_at_utc)
        """, events)

        linked_series = {row["recurring_id"] for row in links}
        for item in series:
            if item["recurring_id"] in linked_series:
                continue
            exceptions.append({
                "exception_id": f"EXC-{exception_number:08d}",
                "entity_type": "recurring_series",
                "entity_id": item["recurring_id"],
                "issue_type": "recurring_occurrence_not_matched",
                "severity": "medium",
                "status": "open",
                "description": (
                    "No qualifying ledger transaction matched this series "
                    "using account, merchant, expected day and amount tolerance."
                ),
                "created_at_utc": "2026-12-31T23:59:59Z",
                "resolved_at_utc": None,
            })
            exception_number += 1

        if exceptions:
            connection.executemany("""
                INSERT INTO exceptions
                (exception_id, entity_type, entity_id, issue_type, severity,
                 status, description, created_at_utc, resolved_at_utc)
                VALUES (:exception_id, :entity_type, :entity_id, :issue_type,
                        :severity, :status, :description, :created_at_utc,
                        :resolved_at_utc)
            """, exceptions)

        connection.commit()
        print(f"Merchant aliases: {len(aliases):,}")
        print(f"Category rules: {len(rules):,}")
        print(f"Recurring transaction links: {len(links):,}")
        print(f"Insights: {len(insights):,}")
        print(f"State events: {len(events):,}")
        print(f"Exceptions: {len(exceptions):,}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    config = load_config()
    start_date = date.fromisoformat(config["date_range"]["start_date"])
    end_date = date.fromisoformat(config["date_range"]["end_date"])

    profiles = load_csv("user_profiles.csv")
    accounts = load_csv("accounts.csv")
    merchants = load_csv("merchants.csv")
    transactions = load_csv("transactions.csv")

    months = month_starts(start_date, end_date)
    budgets = create_budgets(profiles, months)
    series = create_recurring_series(
        profiles, accounts, merchants, start_date, end_date
    )
    aliases = create_aliases(merchants)
    rules = create_rules(merchants)
    insights = create_insights(transactions, profiles, budgets)

    initialize_database()
    populate_database(budgets, series, aliases, rules, insights, transactions)

    output_dir = resolve_path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, rows in [
        ("budgets.csv", budgets),
        ("recurring_series.csv", series),
        ("merchant_aliases.csv", aliases),
        ("category_rules.csv", rules),
        ("insights.csv", insights),
    ]:
        pd.DataFrame(rows).to_csv(
            output_dir / filename, index=False, encoding="utf-8"
        )

    write_ground_truth(
        transactions,
        series,
        resolve_path("data/ground_truth"),
    )
    print("Supplemental data generation completed.")


if __name__ == "__main__":
    main()

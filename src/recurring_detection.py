
"""Detect potential recurring payments from posted transaction history."""

import pandas as pd


RECURRING_TYPES = {"purchase", "bill_payment"}
MIN_OCCURRENCES = 3
AMOUNT_TOLERANCE = 0.15


def detect_recurring_payments(
    transactions: pd.DataFrame,
    min_occurrences: int = MIN_OCCURRENCES,
    amount_tolerance: float = AMOUNT_TOLERANCE,
) -> pd.DataFrame:
    """Identify likely monthly or weekly payments using transaction history.

    Transactions are grouped by user, account, merchant, and transaction
    type. A group is considered recurring when it has enough occurrences
    and its dates and amounts show a consistent pattern.
    """
    required = {
        "user_id",
        "account_id",
        "merchant_id",
        "transaction_type",
        "amount",
        "transaction_date",
    }
    missing = required - set(transactions.columns)
    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    if min_occurrences < 2:
        raise ValueError("min_occurrences must be at least 2.")

    if not 0 <= amount_tolerance < 1:
        raise ValueError("amount_tolerance must be between 0 and 1.")

    columns = [
        "user_id",
        "account_id",
        "merchant_id",
        "transaction_type",
        "occurrences",
        "average_amount",
        "amount_variation_pct",
        "average_interval_days",
        "cadence",
        "first_date",
        "last_date",
        "confidence",
    ]

    if transactions.empty:
        return pd.DataFrame(columns=columns)

    data = transactions.copy()
    data["transaction_type"] = (
        data["transaction_type"].astype(str).str.lower().str.strip()
    )
    data["amount"] = pd.to_numeric(data["amount"], errors="raise")
    data["transaction_date"] = pd.to_datetime(
        data["transaction_date"], errors="coerce"
    )

    if data["transaction_date"].isna().any():
        raise ValueError("Transaction dates must be valid.")

    if data["amount"].isna().any() or (data["amount"] < 0).any():
        raise ValueError("Amounts must be non-negative and not missing.")

    data = data[
        data["transaction_type"].isin(RECURRING_TYPES)
        & data["merchant_id"].notna()
        & data["account_id"].notna()
        & data["user_id"].notna()
    ].copy()

    if data.empty:
        return pd.DataFrame(columns=columns)

    group_columns = [
        "user_id",
        "account_id",
        "merchant_id",
        "transaction_type",
    ]
    detections = []

    for key, group in data.groupby(group_columns, dropna=True):
        group = group.sort_values("transaction_date")
        group = group.drop_duplicates(
            subset=["transaction_date", "amount"]
        )

        if len(group) < min_occurrences:
            continue

        amounts = group["amount"]
        average_amount = float(amounts.mean())

        if average_amount <= 0:
            continue

        variation = float(amounts.std(ddof=0) / average_amount)
        if variation > amount_tolerance:
            continue

        dates = group["transaction_date"].drop_duplicates().sort_values()
        intervals = dates.diff().dropna().dt.total_seconds() / 86400

        if intervals.empty:
            continue

        average_interval = float(intervals.median())

        if 6 <= average_interval <= 8:
            cadence = "weekly"
        elif 12 <= average_interval <= 16:
            cadence = "fortnightly"
        elif 26 <= average_interval <= 35:
            cadence = "monthly"
        elif 80 <= average_interval <= 100:
            cadence = "quarterly"
        elif 350 <= average_interval <= 380:
            cadence = "yearly"
        else:
            continue

        # Higher confidence requires more occurrences and more stable amounts.
        occurrence_score = min(len(group) / 6, 1.0)
        stability_score = max(
            0.0, 1.0 - variation / max(amount_tolerance, 0.01)
        )
        confidence = round(
            100 * (0.6 * occurrence_score + 0.4 * stability_score), 1
        )

        detections.append(
            {
                "user_id": key[0],
                "account_id": key[1],
                "merchant_id": key[2],
                "transaction_type": key[3],
                "occurrences": int(len(group)),
                "average_amount": round(average_amount, 2),
                "amount_variation_pct": round(variation * 100, 2),
                "average_interval_days": round(average_interval, 1),
                "cadence": cadence,
                "first_date": dates.iloc[0].date().isoformat(),
                "last_date": dates.iloc[-1].date().isoformat(),
                "confidence": confidence,
            }
        )

    if not detections:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(detections, columns=columns)
        .sort_values(
            ["confidence", "occurrences"],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )

def detect_missing_recurring_occurrences(
    recurring_series: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of_date: str,
    date_tolerance_days: int = 3,
) -> pd.DataFrame:
    """Flag expected recurring payments with no matching transaction.

    Expected recurring series columns:
        user_id, account_id, merchant_id, expected_amount,
        expected_occurrence_date

    Transaction columns:
        user_id, account_id, merchant_id, amount, transaction_date
    """
    series_required = {
        "user_id",
        "account_id",
        "merchant_id",
        "expected_amount",
        "expected_occurrence_date",
    }
    transaction_required = {
        "user_id",
        "account_id",
        "merchant_id",
        "amount",
        "transaction_date",
    }

    missing_series = series_required - set(recurring_series.columns)
    missing_transactions = transaction_required - set(transactions.columns)

    if missing_series:
        raise ValueError(
            f"Missing recurring series columns: {sorted(missing_series)}"
        )
    if missing_transactions:
        raise ValueError(
            f"Missing transaction columns: {sorted(missing_transactions)}"
        )
    if date_tolerance_days < 0:
        raise ValueError("date_tolerance_days cannot be negative.")

    series = recurring_series.copy()
    tx = transactions.copy()

    series["expected_occurrence_date"] = pd.to_datetime(
        series["expected_occurrence_date"], errors="coerce"
    ).dt.normalize()
    tx["transaction_date"] = pd.to_datetime(
        tx["transaction_date"], errors="coerce"
    ).dt.normalize()

    series["expected_amount"] = pd.to_numeric(
        series["expected_amount"], errors="raise"
    )
    tx["amount"] = pd.to_numeric(tx["amount"], errors="raise")

    if series["expected_occurrence_date"].isna().any():
        raise ValueError("Expected occurrence dates must be valid.")
    if tx["transaction_date"].isna().any():
        raise ValueError("Transaction dates must be valid.")
    if series["expected_amount"].isna().any() or (
        series["expected_amount"] < 0
    ).any():
        raise ValueError("Expected amounts must be non-negative.")
    if tx["amount"].isna().any() or (tx["amount"] < 0).any():
        raise ValueError("Transaction amounts must be non-negative.")

    as_of = pd.Timestamp(as_of_date).normalize()
    matches = []

    for _, expected in series.iterrows():
        due_date = expected["expected_occurrence_date"]

        # Do not flag future payments or dates beyond the review date.
        if due_date > as_of:
            continue

        same_payment = (
            (tx["user_id"] == expected["user_id"])
            & (tx["account_id"] == expected["account_id"])
            & (tx["merchant_id"] == expected["merchant_id"])
        )

        date_difference = (
            tx["transaction_date"] - due_date
        ).abs().dt.days

        amount = float(expected["expected_amount"])
        if amount > 0:
            amount_matches = (
                (tx["amount"] - amount).abs() <= amount * 0.15
            )
        else:
            amount_matches = tx["amount"] == 0

        found = (
            same_payment
            & (date_difference <= date_tolerance_days)
            & amount_matches
        ).any()

        if not found:
            matches.append({
                "user_id": expected["user_id"],
                "account_id": expected["account_id"],
                "merchant_id": expected["merchant_id"],
                "expected_amount": amount,
                "expected_occurrence_date": due_date.date().isoformat(),
                "status": "missing_occurrence",
                "review_required": True,
            })

    return pd.DataFrame(
        matches,
        columns=[
            "user_id",
            "account_id",
            "merchant_id",
            "expected_amount",
            "expected_occurrence_date",
            "status",
            "review_required",
        ],
    )

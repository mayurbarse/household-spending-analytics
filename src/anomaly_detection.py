
"""Detect unusually large transactions using robust spending statistics."""

import pandas as pd

from src.analytics import EXPENSE_TYPES


REQUIRED_COLUMNS = {"user_id", "transaction_type", "amount"}


def detect_unusual_transactions(
    transactions: pd.DataFrame,
    min_history: int = 5,
    robust_z_threshold: float = 3.5,
) -> pd.DataFrame:
    """Flag unusual expenses relative to a user's spending history.

    Transactions are compared within user/category groups when category_id
    exists. The median absolute deviation (MAD) reduces sensitivity to
    unusually large values in the baseline itself.

    This identifies candidates for review, not confirmed fraud.
    """
    missing = REQUIRED_COLUMNS - set(transactions.columns)
    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    if min_history < 2:
        raise ValueError("min_history must be at least 2.")

    if robust_z_threshold <= 0:
        raise ValueError("robust_z_threshold must be positive.")

    if transactions.empty:
        return pd.DataFrame(
            columns=[
                *transactions.columns,
                "baseline_median",
                "robust_z_score",
                "is_anomaly",
                "anomaly_reason",
            ]
        )

    result = transactions.copy()
    result["transaction_type"] = (
        result["transaction_type"].astype(str).str.lower().str.strip()
    )
    result["amount"] = pd.to_numeric(result["amount"], errors="raise")

    if result["amount"].isna().any():
        raise ValueError("Transaction amounts cannot be missing.")

    if (result["amount"] < 0).any():
        raise ValueError("Transaction amounts must be non-negative.")

    result["baseline_median"] = float("nan")
    result["robust_z_score"] = float("nan")
    result["is_anomaly"] = False
    result["anomaly_reason"] = ""

    expense_mask = result["transaction_type"].isin(EXPENSE_TYPES)
    eligible = result.loc[expense_mask].copy()

    if eligible.empty:
        return result

    # Prefer category-specific baselines where the category is available.
    group_columns = ["user_id"]
    if "category_id" in eligible.columns:
        group_columns.append("category_id")

    grouped = eligible.groupby(group_columns, dropna=False)["amount"]

    eligible["_history_count"] = grouped.transform("count")
    eligible["_median"] = grouped.transform("median")
    deviation_frame = eligible[group_columns].copy()
    deviation_frame["_deviation"] = (
        eligible["amount"] - eligible["_median"]
    ).abs()
    eligible["_mad"] = deviation_frame.groupby(
        group_columns, dropna=False
    )["_deviation"].transform("median")

    # Use the robust modified z-score when MAD is non-zero.
    has_mad = eligible["_mad"] > 0
    eligible["_robust_z"] = float("nan")
    eligible.loc[has_mad, "_robust_z"] = (
        0.6745
        * (
            eligible.loc[has_mad, "amount"]
            - eligible.loc[has_mad, "_median"]
        )
        / eligible.loc[has_mad, "_mad"]
    )

    # If MAD is zero, use the interquartile range as a fallback.
    eligible["_row_order"] = range(len(eligible))

    quantiles = (
        eligible.groupby(group_columns, dropna=False)["amount"]
        .quantile([0.25, 0.75])
        .unstack()
    )
    quantiles.columns = ["_q1", "_q3"]
    quantiles = quantiles.reset_index()

    quantile_rows = eligible[group_columns + ["_row_order"]].merge(
        quantiles,
        on=group_columns,
        how="left",
        sort=False,
        validate="many_to_one",
    ).sort_values("_row_order", kind="stable")

    eligible["_q1"] = quantile_rows["_q1"].to_numpy()
    eligible["_q3"] = quantile_rows["_q3"].to_numpy()
    eligible.drop(columns="_row_order", inplace=True)
    eligible["_iqr"] = eligible["_q3"] - eligible["_q1"]

    zero_mad = ~has_mad
    has_iqr = zero_mad & (eligible["_iqr"] > 0)

    eligible.loc[has_iqr, "_robust_z"] = (
        eligible.loc[has_iqr, "amount"]
        - eligible.loc[has_iqr, "_median"]
    ) / eligible.loc[has_iqr, "_iqr"]

    # If both MAD and IQR are zero, avoid division by zero. Only values
    # strictly above the common historical amount are candidates.
    no_spread = zero_mad & (eligible["_iqr"] == 0)
    eligible.loc[no_spread, "_robust_z"] = 0.0
    eligible.loc[
        no_spread & (eligible["amount"] > eligible["_median"]),
        "_robust_z",
    ] = robust_z_threshold + 1.0

    eligible["is_anomaly"] = (
        (eligible["_history_count"] >= min_history)
        & (eligible["_robust_z"] >= robust_z_threshold)
    )

    eligible["anomaly_reason"] = ""
    eligible.loc[eligible["is_anomaly"], "anomaly_reason"] = (
        "Expense amount is unusually high compared with the user's "
        "historical spending in this group."
    )

    result.loc[eligible.index, "baseline_median"] = eligible["_median"]
    result.loc[eligible.index, "robust_z_score"] = eligible["_robust_z"]
    result.loc[eligible.index, "is_anomaly"] = eligible["is_anomaly"]
    result.loc[eligible.index, "anomaly_reason"] = eligible["anomaly_reason"]

    return result


"""Generate analytics reports from the existing SQLite database."""

import json
from pathlib import Path

from src.analytics import load_transactions, spending_summary
from src.trend_analytics import calculate_monthly_trends, save_monthly_trends


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading transactions from SQLite...", flush=True)
    transactions = load_transactions()

    if transactions.empty:
        raise RuntimeError(
            "No posted transactions found. Check the database and transaction statuses."
        )

    print(f"Loaded {len(transactions):,} transactions.", flush=True)

    print("Calculating spending summary...", flush=True)
    summary = spending_summary(transactions)

    summary_path = OUTPUT_DIR / "spending_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("Calculating monthly trends...", flush=True)
    trends = calculate_monthly_trends(transactions)

    trends_path = OUTPUT_DIR / "monthly_trends.csv"
    save_monthly_trends(trends, trends_path)

    print("\nAnalytics reports generated successfully.")
    print(f"Summary: {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Monthly trends: {trends_path.relative_to(PROJECT_ROOT)}")
    print(f"Monthly trend rows: {len(trends):,}")
    print("\nSpending summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()


import sqlite3
import pandas as pd

DB_PATH = "database/app.db"
REPORT_PATH = "data/output/budget_report.csv"

with sqlite3.connect(DB_PATH) as connection:
    # 1. Compare total active budgets with posted expenses.
    budget_total = connection.execute("""
        SELECT SUM(budget_amount_minor) / 100.0
        FROM budgets
        WHERE status = 'active'
    """).fetchone()[0] or 0

    expense_total = connection.execute("""
        SELECT SUM(ABS(amount_minor)) / 100.0
        FROM transactions
        WHERE status = 'posted'
          AND transaction_type IN ('purchase', 'bill_payment', 'fee')
    """).fetchone()[0] or 0

    print("\n=== OVERALL TOTALS ===")
    print(f"Active budgets: ₹{budget_total:,.2f}")
    print(f"Gross expenses: ₹{expense_total:,.2f}")
    print(f"Expenses / budgets: {expense_total / budget_total:.1%}"
          if budget_total else "No active budgets found")

    # 2. Check average monthly expense per user.
    monthly = connection.execute("""
        SELECT
            COUNT(DISTINCT a.user_id) AS users,
            COUNT(DISTINCT substr(t.local_transaction_date, 1, 7)) AS months,
            SUM(ABS(t.amount_minor)) / 100.0 AS total_expenses
        FROM transactions t
        JOIN accounts a ON a.account_id = t.account_id
        WHERE t.status = 'posted'
          AND t.transaction_type IN ('purchase', 'bill_payment', 'fee')
    """).fetchone()

    users, months, total = monthly
    print("\n=== AVERAGE SPENDING ===")
    print(f"Users with expenses: {users}")
    print(f"Months represented: {months}")
    if users and months:
        print(f"Average expenses per user per month: "
              f"₹{total / users / months:,.2f}")

# 3. Inspect the generated budget report.
report = pd.read_csv(REPORT_PATH)

print("\n=== BUDGET REPORT CHECK ===")
print(f"Budget rows: {len(report):,}")
print(f"Rows marked overspent: {int(report['is_overspent'].sum()):,}")
print(f"Overspending rate: {report['is_overspent'].mean():.1%}")

print("\n=== CATEGORY BREAKDOWN ===")
summary = report.groupby("category_id").agg(
    budget_rows=("budget_id", "count"),
    average_budget=("budget_amount", "mean"),
    average_spending=("net_spending", "mean"),
    overspent_rows=("is_overspent", "sum"),
).round(2)

summary["overspent_pct"] = (
    summary["overspent_rows"] / summary["budget_rows"] * 100
).round(1)

print(summary.to_string())

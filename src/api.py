
"""FastAPI endpoints for household spending analytics."""

import json
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from src.analytics import load_transactions, spending_summary
from src.config import PROJECT_ROOT
from src.anomaly_detection import detect_unusual_transactions
from src.trend_analytics import calculate_monthly_trends
from src.recurring_detection import detect_recurring_payments

app = FastAPI(
    title="Household Spending Analytics API",
    description="API for household spending, trends, and budgets.",
    version="1.0.0",
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
DATABASE_PATH = PROJECT_ROOT / "database" / "app.db"


@app.get("/")
def root() -> dict:
    """API health and documentation links."""
    return {
        "name": "Household Spending Analytics API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    """Check whether the application and database are accessible."""
    try:
        with sqlite3.connect(
            f"{DATABASE_PATH.as_uri()}?mode=ro",
            uri=True,
            timeout=5,
        ) as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "healthy", "database": "accessible"}
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        ) from exc


@app.get("/api/summary")
def get_summary() -> dict:
    """Return overall spending metrics."""
    try:
        transactions = load_transactions()
        return spending_summary(transactions)
    except (ValueError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not calculate spending summary.",
        ) from exc


@app.get("/api/trends")
def get_trends(
    user_id: str | None = Query(default=None, min_length=1),
) -> dict:
    """Return monthly spending trends, optionally filtered by user."""
    try:
        transactions = load_transactions()

        if user_id is not None:
            transactions = transactions[
                transactions["user_id"] == user_id
            ]

        trends = calculate_monthly_trends(transactions)
        records = trends.where(pd.notna(trends), None).to_dict(
            orient="records"
        )

        return {
            "count": len(records),
            "data": records,
        }
    except (ValueError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not calculate monthly trends.",
        ) from exc


@app.get("/api/budgets")
def get_budgets(
    user_id: str | None = Query(default=None, min_length=1),
    month: str | None = Query(
        default=None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
) -> dict:
    """Return saved budget comparisons, optionally filtered."""
    budget_path = OUTPUT_DIR / "budget_report.csv"

    if not budget_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Budget report not found. Generate the budget report first.",
        )

    try:
        budgets = pd.read_csv(budget_path)

        if user_id is not None:
            if "user_id" not in budgets.columns:
                raise HTTPException(
                    status_code=500,
                    detail="Budget report has no user_id column.",
                )
            budgets = budgets[budgets["user_id"].astype(str) == user_id]

        if month is not None:
            month_column = next(
                (
                    column
                    for column in ("budget_month", "month")
                    if column in budgets.columns
                ),
                None,
            )
            if month_column is None:
                raise HTTPException(
                    status_code=500,
                    detail="Budget report has no month column.",
                )
            budgets = budgets[
                budgets[month_column].astype(str).str[:7] == month
            ]

        budgets = budgets.astype(object).where(
            pd.notna(budgets), None
        )

        return {
            "count": len(budgets),
            "data": budgets.to_dict(orient="records"),
        }
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the budget report.",
        ) from exc

    
@app.get("/api/recurring")
def get_recurring_payments(
    user_id: str | None = Query(default=None, min_length=1),
) -> dict:
    """Detect likely recurring payments from posted transactions."""
    try:
        transactions = load_transactions()

        if user_id is not None:
            transactions = transactions[
                transactions["user_id"] == user_id
            ]

        recurring = detect_recurring_payments(transactions)
        records = recurring.astype(object).where(
            pd.notna(recurring), None
        ).to_dict(orient="records")

        return {
            "count": len(records),
            "data": records,
        }
    except (ValueError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not detect recurring payments.",
        ) from exc
@app.get("/api/anomalies")
def get_anomalies(
    user_id: str | None = Query(default=None, min_length=1),
    min_history: int = Query(default=5, ge=2),
    threshold: float = Query(default=3.5, gt=0),
) -> dict:
    """Return unusually large expenses for review."""
    try:
        transactions = load_transactions()

        if user_id is not None:
            transactions = transactions[
                transactions["user_id"] == user_id
            ]

        results = detect_unusual_transactions(
            transactions,
            min_history=min_history,
            robust_z_threshold=threshold,
        )

        anomalies = results[results["is_anomaly"]].copy()
        anomalies = anomalies.astype(object).where(
            pd.notna(anomalies), None
        )

        records = anomalies.to_dict(orient="records")

        return {
            "count": len(records),
            "filters": {
                "user_id": user_id,
                "min_history": min_history,
                "threshold": threshold,
            },
            "data": records,
            "notice": (
                "These are unusual spending patterns for review, "
                "not confirmed fraud."
            ),
        }
    except (ValueError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not detect spending anomalies.",
        ) from exc    


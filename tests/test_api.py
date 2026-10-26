
"""Tests for the Household Spending Analytics API."""

from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_summary_endpoint():
    response = client.get("/api/summary")

    assert response.status_code == 200

    data = response.json()
    assert data["transaction_count"] == 500000
    assert data["gross_expenses"] >= 0
    assert data["refunds"] >= 0
    assert data["net_spending"] == round(
        data["gross_expenses"] - data["refunds"], 2
    )


def test_trends_endpoint():
    response = client.get("/api/trends")

    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 12000
    assert len(data["data"]) > 0

    first_record = data["data"][0]
    assert "month" in first_record
    assert "gross_expenses" in first_record
    assert "refunds" in first_record
    assert "net_spending" in first_record


def test_trends_can_filter_by_user():
    response = client.get(
        "/api/trends",
        params={"user_id": "USR-000001"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 12
    assert all(
        record["user_id"] == "USR-000001"
        for record in data["data"]
    )


def test_budgets_endpoint():
    response = client.get("/api/budgets")

    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 96000
    assert len(data["data"]) > 0

    first_record = data["data"][0]
    assert "budget_amount" in first_record
    assert "net_spending" in first_record
    assert "is_overspent" in first_record


def test_budgets_can_filter_by_user_and_month():
    response = client.get(
        "/api/budgets",
        params={
            "user_id": "USR-000001",
            "month": "2026-01",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 8
    assert all(
        record["user_id"] == "USR-000001"
        and record["month"] == "2026-01"
        for record in data["data"]
    )


def test_budgets_reject_invalid_month():
    response = client.get(
        "/api/budgets",
        params={"month": "2026-13"},
    )

    assert response.status_code == 422


def test_recurring_endpoint():
    response = client.get("/api/recurring")

    assert response.status_code == 200

    data = response.json()
    assert "count" in data
    assert "data" in data
    assert data["count"] == len(data["data"])

    if data["data"]:
        first_record = data["data"][0]
        assert "merchant_id" in first_record
        assert "cadence" in first_record
        assert "average_amount" in first_record
        assert "confidence" in first_record


def test_recurring_endpoint_can_filter_by_user():
    response = client.get(
        "/api/recurring",
        params={"user_id": "USR-000624"},
    )

    assert response.status_code == 200

    data = response.json()
    assert all(
        record["user_id"] == "USR-000624"
        for record in data["data"]
    )


def test_anomalies_endpoint_returns_expected_structure():
    response = client.get("/api/anomalies")

    assert response.status_code == 200

    data = response.json()
    assert "count" in data
    assert "filters" in data
    assert "data" in data
    assert "notice" in data
    assert isinstance(data["data"], list)
    assert data["count"] == len(data["data"])


def test_anomalies_endpoint_can_filter_by_user():
    response = client.get(
        "/api/anomalies",
        params={"user_id": "USR-000001"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["filters"]["user_id"] == "USR-000001"

    for anomaly in data["data"]:
        assert anomaly["user_id"] == "USR-000001"
        assert anomaly["is_anomaly"] is True


def test_anomalies_endpoint_accepts_detection_parameters():
    response = client.get(
        "/api/anomalies",
        params={
            "user_id": "USR-000001",
            "min_history": 3,
            "threshold": 4.0,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["filters"]["min_history"] == 3
    assert data["filters"]["threshold"] == 4.0


def test_anomalies_endpoint_rejects_invalid_parameters():
    response = client.get(
        "/api/anomalies",
        params={"min_history": 1},
    )

    assert response.status_code == 422

    response = client.get(
        "/api/anomalies",
        params={"threshold": 0},
    )

    assert response.status_code == 422

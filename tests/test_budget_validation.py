
import pandas as pd
import pytest

from src.budget_analytics import validate_budget_categories


def test_valid_budget_category_is_accepted():
    budgets = pd.DataFrame([
        {"budget_id": "BUD-001", "category_id": "CAT-001"}
    ])
    categories = pd.DataFrame([
        {"category_id": "CAT-001", "category_name": "Food"}
    ])

    result = validate_budget_categories(budgets, categories)

    assert len(result) == 1
    assert result.iloc[0]["category_id"] == "CAT-001"


def test_unknown_budget_category_is_rejected():
    budgets = pd.DataFrame([
        {"budget_id": "BUD-INVALID-001", "category_id": "CAT-999"}
    ])
    categories = pd.DataFrame([
        {"category_id": "CAT-001", "category_name": "Food"}
    ])

    with pytest.raises(ValueError, match="CAT-999"):
        validate_budget_categories(budgets, categories)


def test_missing_budget_category_is_rejected():
    budgets = pd.DataFrame([
        {"budget_id": "BUD-002", "category_id": None}
    ])
    categories = pd.DataFrame([
        {"category_id": "CAT-001", "category_name": "Food"}
    ])

    with pytest.raises(ValueError, match="missing category_id"):
        validate_budget_categories(budgets, categories)


def test_missing_category_column_is_rejected():
    budgets = pd.DataFrame([
        {"budget_id": "BUD-001", "category_id": "CAT-001"}
    ])
    categories = pd.DataFrame([
        {"category_name": "Food"}
    ])

    with pytest.raises(ValueError, match="category_id column"):
        validate_budget_categories(budgets, categories)

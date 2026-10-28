# Household Spending Analytics

A Python-based financial analytics project built around synthetic household transaction data. It explores spending patterns, monthly budgets, recurring payments, unusual transactions, and data-quality edge cases through a SQLite database and REST API.

> **Project status:** Full-stack dashboard implemented with a FastAPI backend and React/Vite frontend.

## Features

- **Spending analytics:** Calculate gross expenses, refund credits, and net spending while excluding internal transfers from expenses.
- **Monthly trends:** Aggregate spending by month and user.
- **Budget analysis:** Compare actual spending with category budgets and identify overspending.
- **Recurring payment detection:** Identify potentially recurring payments using transaction frequency and amount consistency.
- **Missing payment checks:** Flag expected recurring occurrences that have no matching transaction for review.
- **Anomaly detection:** Identify unusually large expenses using robust statistical methods.
- **Data validation:** Check required fields, budget categories, amounts, and transaction edge cases.
- **Synthetic data generation:** Generate configurable profiles, accounts, merchants, categories, and transactions.
- **REST API:** Expose analytics through FastAPI endpoints.
- **Automated tests:** Validate analytics, database integrity, API behaviour, and edge cases using pytest.

## Technology Stack

- Python
- SQLite
- Pandas and NumPy
- FastAPI and Uvicorn
- pytest
- React and Vite (planned frontend)

## Project Structure

```text
household-spending-analytics/
├── config/
│   └── settings.json
├── data/
│   ├── ground_truth/
│   ├── input/
│   └── output/
├── database/
│   └── schema.sql
├── frontend/
├── reports/
├── schemas/
│   └── data_dictionary.md
├── src/
│   ├── analytics.py
│   ├── anomaly_detection.py
│   ├── api.py
│   ├── budget_analytics.py
│   ├── config.py
│   ├── db.py
│   ├── generate_data.py
│   ├── generate_supplemental_data.py
│   ├── recurring_detection.py
│   ├── run_analytics.py
│   └── trend_analytics.py
├── tests/
├── .gitignore
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.13 or a compatible Python version
- pip
- Git

## Setup

Clone the repository and enter the project directory:

```powershell
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
cd household-spending-analytics
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Generate the Dataset

The default configuration specifies:

- 1,000 synthetic profiles
- 500,000 target transactions
- 12 months of configured data
- INR as the reporting currency
- Asia/Kolkata as the reporting timezone

Review `config/settings.json` before generating data.

**Warning:** The main generator replaces generated database records and writes CSV exports. It can take significant time and disk space. Do not run it against a database containing data you need to preserve.

Generate the core dataset:

```powershell
python -m src.generate_data
```

Generate supplemental budgets, recurring series, and labelled edge-case scenarios:

```powershell
python -m src.generate_supplemental_data
```

The supplemental generator uses CSV files produced by the main generator.

## Run Analytics

After generating the dataset, calculate the spending summary and monthly trends:

```powershell
python -m src.run_analytics
```

Reports are written under `data/output/`, including:

- `spending_summary.json`
- `monthly_trends.csv`

Generated datasets, reports, and local database files are excluded from Git. They are not included in this repository by default.

## Run the API

Start the development server:

```powershell
python -m uvicorn src.api:app --reload
```

Open the interactive API documentation at:

http://127.0.0.1:8000/docs

### API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API status and documentation link |
| GET | `/health` | Database connectivity check |
| GET | `/api/summary` | Overall spending summary |
| GET | `/api/trends` | Monthly spending trends |
| GET | `/api/budgets` | Budget comparison results |
| GET | `/api/recurring` | Detected recurring payments |
| GET | `/api/anomalies` | Unusual expense candidates |

Some endpoints support query parameters for filtering by user or month. The trends and anomaly endpoints also support relevant analysis parameters. See `/docs` for the available parameters and response schemas.

## Run Tests

Run the full test suite:

```powershell
python -m pytest tests/ -v
```

The latest local verification completed with **63 passing tests**. Results may change as the project evolves.

The tests cover spending calculations, refunds, internal transfers, budget validation, recurring payments, anomaly detection, timezone conversion, database constraints, and API responses.

## Data and Evaluation

This project is designed to use synthetic financial data rather than real customer financial records.

The ground-truth scenario file covers five targeted cases:

1. Internal transfers should not inflate spending.
2. Refunds should reduce net spending rather than increase expenses.
3. Missing recurring payments should be flagged for review.
4. UTC timestamps should be converted correctly to the reporting timezone.
5. Budgets with categories outside the taxonomy should be rejected.

These scenarios support targeted validation; they do not by themselves establish that every detection algorithm is production-ready.

## Limitations and Future Work

- Add more representative dashboard screenshots and sample outputs.
- Improve the realism and calibration of synthetic spending and budget distributions.
- Evaluate recurring-payment and anomaly-detection precision and recall against labelled data.
- Improve detection of missed recurring payments and validate results across more edge cases.
- Add further API integration and end-to-end tests.
- Add representative, privacy-safe sample outputs and visualizations.

## Disclaimer

This project is for learning, analytics, and software engineering demonstration. All generated financial data is synthetic. Anomaly and recurring-payment results are candidates for review, not financial advice or definitive fraud findings.

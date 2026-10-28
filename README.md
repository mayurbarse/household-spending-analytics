# Household Spending Analytics

A Python-based financial analytics project built around synthetic household transaction data. It explores spending patterns, monthly budgets, recurring payments, unusual transactions, and data-quality edge cases through a SQLite database, a FastAPI REST API, and a React/Vite dashboard.

> **Project status:** Python analytics pipeline and FastAPI backend, with a React/Vite dashboard that consumes the API. Follow the setup instructions below to generate the data and run each component.

## Features

- **Spending analytics:** Calculate gross expenses, refund credits, and net spending while excluding internal transfers from expenses.
- **Monthly trends:** Aggregate spending by month and user.
- **Budget analysis:** Compare actual spending with category budgets and identify overspending.
- **Recurring payment detection:** Identify potentially recurring payments using transaction frequency and amount consistency.
- **Missing payment checks:** Flag expected recurring occurrences without a matching transaction for review.
- **Anomaly detection:** Identify unusually large expenses using robust statistical methods.
- **Data validation:** Check required fields, budget categories, amounts, and transaction edge cases.
- **Synthetic data generation:** Generate configurable profiles, accounts, merchants, categories, and transactions.
- **REST API:** Expose analytics through FastAPI endpoints.
- **Dashboard:** Present spending summaries, monthly trends, budgets, recurring payments, and anomaly candidates through a React/Vite frontend.
- **Automated tests:** Validate analytics, database integrity, API behaviour, and edge cases using pytest.

## Technology Stack

- Python
- SQLite
- Pandas and NumPy
- FastAPI and Uvicorn
- pytest
- React
- Vite
- JavaScript and CSS

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
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
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
├── screenshots/
├── Household_Spending_Analytics_Test_Cases.docx
├── Household_Spending_Analytics_LLM_Prompt_History.docx
├── .gitignore
├── README.md
└── requirements.txt
```

*Note: This is a high-level structure. Some generated datasets, reports, and local database files are excluded from Git and must be created locally.*

## Requirements

- Python 3.13 or a compatible Python version supported by the dependencies
- pip
- Git
- Node.js and npm (for the frontend)

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/mayurbarse/household-spending-analytics.git
cd household-spending-analytics
```

### 2. Create a Python virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, review your local execution policy rather than changing system-wide settings unnecessarily.

### 3. Install Python dependencies

```powershell
python -m pip install -r requirements.txt
```

## Generate the Dataset

The default configuration is intended to generate:

- 1,000 synthetic profiles
- 500,000 target transactions
- 12 months of configured data
- INR as the reporting currency
- Asia/Kolkata as the reporting timezone

Review `config/settings.json` before generating the dataset.

> **Warning:** The main generator replaces generated database records and writes CSV exports. Generation can take significant time and disk space. Do not run it against a database containing data you need to preserve.

### 1. Generate the core dataset

From the project root:

```powershell
python -m src.generate_data
```

### 2. Generate supplemental data

```powershell
python -m src.generate_supplemental_data
```

The supplemental generator uses CSV files produced by the main generator. Run the core generator first.

## Run Analytics

After generating the dataset, calculate the spending summary and monthly trends:

```powershell
python -m src.run_analytics
```

Reports are written under `data/output/`, including:

- `spending_summary.json`
- `monthly_trends.csv`

Other generated datasets and reports may also be written to this directory.

Generated datasets, reports, and local database files are excluded from Git by default. A fresh clone therefore needs the generation and analytics steps above before those local outputs are available.

## Run the API

Start the FastAPI development server from the project root:

```powershell
python -m uvicorn src.api:app --reload
```

Open the interactive API documentation at:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

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

Some endpoints support query parameters for filtering by user or month. The trends and anomaly endpoints may also support analysis parameters. Refer to `/docs` for the actual parameters and response schemas exposed by the running API.

## Run the Frontend

The frontend uses React and Vite and requests analytics from the FastAPI backend at `http://localhost:8000`.

Open a **second terminal** and run:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite, usually:

[http://localhost:5173](http://localhost:5173)

Keep the backend running in the first terminal. The frontend depends on the API and the generated data being available.

To create a production build:

```powershell
npm run build
```

To run the frontend linter:

```powershell
npm run lint
```

## Run Tests

From the project root, run:

```powershell
python -m pytest tests/ -v
```

The latest reported local verification completed with **63 passing tests**. Run the test suite again after code changes to confirm the current result.

The tests cover spending calculations, refunds, internal transfers, budget validation, recurring payments, anomaly detection, timezone conversion, database constraints, and API responses.

## Data and Evaluation

This project uses synthetic financial data rather than real customer financial records.

The ground-truth scenario file, `data/ground_truth/edge_case_scenarios.csv`, covers five targeted cases:

1. **Internal transfers:** Transfers between accounts should not inflate household spending.
2. **Refunds:** Refunds should reduce net spending rather than be counted as additional expenses.
3. **Missing recurring payments:** Expected recurring occurrences without a suitable matching transaction should be flagged for review.
4. **Timezone conversion:** UTC timestamps should be converted correctly to the reporting timezone.
5. **Invalid categories:** Budgets referencing categories outside the defined taxonomy should be rejected or flagged.

These scenarios support targeted validation. They do not, by themselves, establish that every detection algorithm is production-ready.

## Screenshots

Representative dashboard screenshots are available in the `screenshots/` directory:

- `main-dashboard.png`
- `monthly-trends.png`
- `budget-analysis.png`
- `recurring-payments.png`
- `anomaly-detection.png`

These images illustrate the dashboard's presentation and analytics views. They should not be interpreted as independent proof of model accuracy.

## Limitations and Future Work

- Improve the realism and calibration of synthetic spending and budget distributions.
- Evaluate recurring-payment and anomaly-detection precision and recall against labelled data.
- Improve detection of missed recurring payments and validate results across additional edge cases.
- Add further API integration and end-to-end tests.
- Expand representative sample outputs and dashboard visualizations.
- Improve configuration and deployment options for running the application outside a local development environment.

## Supporting Documentation

- [Test Cases and Validation](Household_Spending_Analytics_Test_Cases.docx)
- [LLM Prompt History and AI Usage](Household_Spending_Analytics_LLM_Prompt_History.docx)

The test-case document describes the intended validation scenarios. The prompt-history document records the prompts and AI-assisted development process used for the project.

## Disclaimer

This project is intended for learning, analytics, and software engineering demonstration. All generated financial data is synthetic. Anomaly and recurring-payment results are candidates for review, not financial advice or definitive fraud findings.

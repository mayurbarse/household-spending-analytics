# Household Spending Analytics

A full-stack financial analytics dashboard built with Python, FastAPI, SQLite, React, and Vite. The project analyzes **500,000 synthetic household transactions** to summarize spending, track budgets, identify recurring payments, and flag unusual transactions.

The dashboard provides an interactive view of financial activity, while the backend exposes analytics through REST API endpoints.

## Features

- **Spending analytics:** Calculate gross expenses, refunds, and net spending while excluding internal transfers from expenses.
- **Monthly trends:** Explore spending patterns over time.
- **Budget analysis:** Compare planned budgets against actual spending and identify overspending.
- **Recurring payment detection:** Identify potential recurring payments based on transaction frequency and amount consistency.
- **Anomaly detection:** Flag unusually large expenses using robust statistical methods.
- **Data validation:** Check required fields, budget categories, amounts, and transaction edge cases.
- **Synthetic data generation:** Generate configurable profiles, accounts, merchants, categories, and transactions.
- **REST API:** Serve analytics through FastAPI.
- **Interactive dashboard:** Explore summary metrics, monthly trends, budgets, recurring payments, and unusual transactions.
- **Automated tests:** Validate calculations, database integrity, API behaviour, and edge cases.

## Technology Stack

| Area | Technologies |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Data processing | Pandas, NumPy |
| Database | SQLite |
| Frontend | React, Vite, JavaScript |
| Testing | pytest |

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
│   ├── src/
│   │   └── App.jsx
│   └── package.json
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

- Python 3.13 or another version compatible with the project dependencies
- Node.js and npm
- Git

## Getting Started

### 1. Clone the repository

```powershell
git clone https://github.com/mayurbarse/household-spending-analytics.git
cd household-spending-analytics
```

### 2. Set up the Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Prepare the data

The project uses synthetic financial transactions. The default configuration is designed around 1,000 profiles, 500,000 target transactions, 12 months of data, and INR reporting.

If the generated database and output files are not already present, review `config/settings.json` and generate the dataset:

```powershell
python -m src.generate_data
python -m src.generate_supplemental_data
python -m src.run_analytics
```

**Note:** Data generation can take time and may replace generated database records or output files. Back up any data you need to preserve before running the generators.

### 4. Start the backend

From the project root, activate the virtual environment if needed, then run:

```powershell
python -m uvicorn src.api:app --reload
```

The backend runs at:

- API: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### 5. Start the frontend

Open a **second terminal** in the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local dashboard URL printed by Vite, usually:

http://localhost:5173

Keep both development servers running while using the dashboard.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API status |
| GET | `/health` | Health check |
| GET | `/api/summary` | Spending summary |
| GET | `/api/trends` | Monthly spending trends |
| GET | `/api/budgets` | Budget comparisons |
| GET | `/api/recurring` | Potential recurring payments |
| GET | `/api/anomalies` | Unusual expense candidates |

Some endpoints support filtering and analysis parameters. Visit `/docs` for the current request parameters and response schemas.

## Performance Improvements

The analytics pipeline includes measured optimizations to reduce computation time while preserving verified output:

| Component | Before | After | Speed improvement |
|---|---:|---:|---:|
| Recurring-payment detection | 30.52 s | 6.31 s | 4.84× faster |
| Anomaly detection | 17.73 s | 1.22 s | 14.48× faster |

The optimized outputs were compared with saved baseline results. Exact equality was verified for the recurring-detection output and the anomaly-detection DataFrame in the tested environment.

These timings are local benchmark results and may vary with hardware, data, and runtime conditions.

## Running Tests

From the project root:

```powershell
python -m pytest tests/ -v
```

The latest recorded verification completed with **63 passing tests**. Run the tests again after code changes to confirm the current result.

## Data and Limitations

- All generated financial records are synthetic.
- Recurring-payment detections are potential patterns, not confirmed subscriptions.
- Anomalies are unusual transactions for review, not confirmed fraud.
- Detection quality should be evaluated against labelled data before production use.
- Generated datasets, reports, and local database files may be excluded from Git; follow the setup steps if they are not included in your clone.

## Future Improvements

- Add more representative dashboard screenshots and sample outputs.
- Evaluate recurring-payment and anomaly-detection precision and recall against labelled data.
- Expand API integration and end-to-end testing.
- Improve the realism of synthetic spending and budget distributions.

## Disclaimer

This project is intended for learning, analytics, and software engineering demonstration. It does not provide financial advice, and its anomaly detections should not be treated as definitive fraud findings.

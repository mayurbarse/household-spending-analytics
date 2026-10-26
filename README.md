
# Household Spending Analytics

A synthetic financial-data project for transaction categorization,
recurring payment detection, household budgeting and anomaly evaluation.

## Technology

- Python
- SQLite
- Pandas and NumPy
- FastAPI
- React and Vite
- Pytest

## Setup

Create and activate a Python virtual environment, then install
dependencies:

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt

## Initialize the database

    python -m src.db

## Run tests

    python -m pytest -v

## Configuration

Edit config/settings.json to configure the random seed, dataset size,
date range, reporting timezone and database path.

## Data provenance

The project is designed to use synthetic data only. No real customer
financial data is required.

## Project status

Step 1: Project foundation and database schema.

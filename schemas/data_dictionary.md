
# Household Spending Analytics — Data Dictionary

## Conventions

- User ID: USR-000001
- Account ID: ACC-<user-id>-01
- Transaction ID: TXN-2026-00000001
- Budget ID: BUD-<user-id>-2026-01-<category-code>
- Recurring ID: REC-000001
- Money: integer minor units; INR uses paise.
- Timestamps: UTC ISO 8601 timestamps.
- Reporting dates: local calendar dates using the configured timezone.
- Synthetic records only; no real customer financial records.

## Entity overview

| Entity | Primary key | Relationship |
|---|---|---|
| UserProfile | user_id | One user has many accounts and budgets |
| Account | account_id | Many transactions belong to one account |
| Merchant | merchant_id | One merchant has many aliases and transactions |
| Category | category_id | One category can have many rules and budgets |
| CategoryRule | rule_id | Each rule targets one category |
| Transaction | transaction_id | Each transaction belongs to one account |
| Budget | budget_id | One user and category per month |
| RecurringSeries | recurring_id | One series can link to many transactions |
| Insight | insight_id | One user can have many insights |
| StateEvent | event_id | Append-only record of a state change |
| Exception | exception_id | Record of an issue requiring review |

## Lifecycle conventions

- User/account: active, inactive, closed.
- Transaction: pending, posted, reversed, cancelled.
- Recurring series: active, paused, ended, under_review.
- Exception: open, under_review, resolved, dismissed.

## Transaction rules

- Positive amount_minor means an inflow.
- Negative amount_minor means an outflow.
- Salary is an inflow.
- Purchase and bill-payment transactions are outflows.
- Refunds and reversals are represented as inflows.
- Transfers are excluded from household spending when matched as
  internal transfers.
- Refunds reduce eligible spending rather than becoming new expenses.
- Category assignment must be traceable to a rule or a documented
  manual-review decision.
- Invalid records are rejected or quarantined, not silently corrected.

## Reproducibility

- Seed: 20261022
- Starter scale: 10 users and 1,000 transactions.
- Target scale: 1,000 users and 500,000 transactions.
- Full generator settings are stored in config/settings.json.

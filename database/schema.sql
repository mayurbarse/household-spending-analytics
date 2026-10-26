
PRAGMA foreign_keys = ON;

-- 1. Master data: synthetic user profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    household_size INTEGER NOT NULL CHECK (household_size >= 1),
    region TEXT NOT NULL,
    income_band TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'closed'))
);

-- 2. Accounts: one user can have multiple accounts
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    account_type TEXT NOT NULL
        CHECK (account_type IN (
            'checking', 'savings', 'credit', 'cash', 'investment'
        )),
    opening_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'closed')),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);

-- 3. Merchants: canonical merchant records
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    merchant_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Merchant descriptors and aliases
CREATE TABLE IF NOT EXISTS merchant_aliases (
    alias_id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    UNIQUE (normalized_alias, effective_from)
);

-- 4. Category taxonomy
CREATE TABLE IF NOT EXISTS categories (
    category_id TEXT PRIMARY KEY,
    category_code TEXT NOT NULL UNIQUE,
    category_name TEXT NOT NULL,
    parent_category_id TEXT,
    category_type TEXT NOT NULL
        CHECK (category_type IN (
            'income', 'expense', 'transfer', 'refund', 'other'
        )),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    FOREIGN KEY (parent_category_id)
        REFERENCES categories(category_id)
);

-- 5. Categorization rules with effective dates and priorities
CREATE TABLE IF NOT EXISTS category_rules (
    rule_id TEXT PRIMARY KEY,
    rule_name TEXT NOT NULL,
    match_field TEXT NOT NULL
        CHECK (match_field IN (
            'merchant_name', 'merchant_alias', 'descriptor', 'transaction_type'
        )),
    match_pattern TEXT NOT NULL,
    match_mode TEXT NOT NULL
        CHECK (match_mode IN ('exact', 'contains', 'prefix', 'regex')),
    category_id TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

-- 6. Transaction ledger
-- Amounts use integer minor units (paise for INR), not floating point.
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    merchant_id TEXT,
    transaction_ts_utc TEXT NOT NULL,
    recorded_at_utc TEXT NOT NULL,
    local_transaction_date TEXT NOT NULL,
    reporting_timezone TEXT NOT NULL,
    descriptor TEXT NOT NULL,
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN (
            'purchase', 'salary', 'refund', 'transfer',
            'fee', 'reversal', 'bill_payment', 'other'
        )),
    amount_minor INTEGER NOT NULL CHECK (amount_minor <> 0),
    currency TEXT NOT NULL,
    category_id TEXT,
    applied_rule_id TEXT,
    linked_transaction_id TEXT,
    transfer_group_id TEXT,
    status TEXT NOT NULL DEFAULT 'posted'
        CHECK (status IN (
            'pending', 'posted', 'reversed', 'cancelled'
        )),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    FOREIGN KEY (applied_rule_id) REFERENCES category_rules(rule_id),
    FOREIGN KEY (linked_transaction_id)
        REFERENCES transactions(transaction_id),
    CHECK (
        (transaction_type IN ('salary', 'refund', 'reversal')
            AND amount_minor > 0)
        OR
        (transaction_type IN (
            'purchase', 'fee', 'bill_payment'
        ) AND amount_minor < 0)
        OR transaction_type IN ('transfer', 'other')
    )
);

-- 7. Monthly budgets
CREATE TABLE IF NOT EXISTS budgets (
    budget_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    budget_month TEXT NOT NULL,
    budget_amount_minor INTEGER NOT NULL
        CHECK (budget_amount_minor >= 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'rejected')),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    UNIQUE (user_id, category_id, budget_month)
);

-- 8. Expected recurring payment series
CREATE TABLE IF NOT EXISTS recurring_series (
    recurring_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    merchant_id TEXT,
    series_type TEXT NOT NULL
        CHECK (series_type IN (
            'salary', 'rent', 'subscription', 'utility', 'other'
        )),
    expected_amount_minor INTEGER NOT NULL
        CHECK (expected_amount_minor > 0),
    currency TEXT NOT NULL,
    cadence TEXT NOT NULL
        CHECK (cadence IN ('weekly', 'monthly', 'quarterly', 'annual')),
    expected_day INTEGER,
    start_date TEXT NOT NULL,
    end_date TEXT,
    next_expected_date TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN (
            'active', 'paused', 'ended', 'under_review'
        )),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
    CHECK (expected_day IS NULL OR expected_day BETWEEN 1 AND 31),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Many-to-many link between recurring series and observed transactions
CREATE TABLE IF NOT EXISTS recurring_transaction_links (
    recurring_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    occurrence_date TEXT NOT NULL,
    match_status TEXT NOT NULL
        CHECK (match_status IN (
            'matched', 'candidate', 'rejected'
        )),
    PRIMARY KEY (recurring_id, transaction_id),
    FOREIGN KEY (recurring_id)
        REFERENCES recurring_series(recurring_id),
    FOREIGN KEY (transaction_id)
        REFERENCES transactions(transaction_id)
);

-- 9. Calculated insights
CREATE TABLE IF NOT EXISTS insights (
    insight_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    insight_type TEXT NOT NULL,
    metric_value REAL,
    currency TEXT,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
    CHECK (period_end >= period_start)
);

-- Explicit audit events; do not overwrite previous decisions.
CREATE TABLE IF NOT EXISTS state_events (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    old_value_json TEXT,
    new_value_json TEXT,
    reason TEXT,
    actor_type TEXT NOT NULL
        CHECK (actor_type IN (
            'system', 'customer', 'analyst', 'reviewer', 'admin'
        )),
    occurred_at_utc TEXT NOT NULL
);

-- Operational exceptions, separate from evaluation ground truth.
CREATE TABLE IF NOT EXISTS exceptions (
    exception_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'under_review', 'resolved', 'dismissed')),
    description TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    resolved_at_utc TEXT
);

-- Indexes for commonly queried relationships and reporting periods
CREATE INDEX IF NOT EXISTS idx_accounts_user
    ON accounts(user_id);

CREATE INDEX IF NOT EXISTS idx_transactions_account_date
    ON transactions(account_id, local_transaction_date);

CREATE INDEX IF NOT EXISTS idx_transactions_merchant
    ON transactions(merchant_id);

CREATE INDEX IF NOT EXISTS idx_transactions_category_date
    ON transactions(category_id, local_transaction_date);

CREATE INDEX IF NOT EXISTS idx_category_rules_priority
    ON category_rules(priority, status);

CREATE INDEX IF NOT EXISTS idx_budgets_user_month
    ON budgets(user_id, budget_month);

CREATE INDEX IF NOT EXISTS idx_recurring_account
    ON recurring_series(account_id, status);

CREATE INDEX IF NOT EXISTS idx_exceptions_status
    ON exceptions(status, severity);

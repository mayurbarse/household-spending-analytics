
import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API = 'http://localhost:8000'

const formatINR = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value ?? 0)

const formatCompactINR = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value ?? 0)

function App() {
  const [summary, setSummary] = useState(null)
  const [monthlyData, setMonthlyData] = useState([])
  const [budgets, setBudgets] = useState([])
  const [recurring, setRecurring] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [selectedMonth, setSelectedMonth] = useState('all')
  const [recurringSearch, setRecurringSearch] = useState('')
  const [anomalySearch, setAnomalySearch] = useState('')
  const [error, setError] = useState('')

useEffect(() => {
  let cancelled = false

  async function loadSummary() {
    try {
      const response = await fetch(`${API}/api/summary`)
      if (!response.ok) throw new Error('Summary request failed')

      const data = await response.json()
      if (!cancelled) setSummary(data)
    } catch {
      if (!cancelled) {
        setError(
          'Unable to load dashboard summary. Check that FastAPI is running.',
        )
      }
    }
  }

  async function loadTrends() {
    try {
      const response = await fetch(`${API}/api/trends`)
      if (!response.ok) throw new Error('Trends request failed')

      const result = await response.json()
      const monthlyTotals = new Map()

      for (const record of result.data ?? []) {
        const current = monthlyTotals.get(record.month) ?? {
          month: record.month,
          gross_expenses: 0,
          refunds: 0,
          net_spending: 0,
          transaction_count: 0,
        }

        current.gross_expenses += Number(record.gross_expenses) || 0
        current.refunds += Number(record.refunds) || 0
        current.net_spending += Number(record.net_spending) || 0
        current.transaction_count += Number(record.transaction_count) || 0
        monthlyTotals.set(record.month, current)
      }

      if (!cancelled) {
        setMonthlyData(
          [...monthlyTotals.values()].sort((a, b) =>
            a.month.localeCompare(b.month),
          ),
        )
      }
    } catch (error) {
      console.error('Could not load spending trends:', error)
    }
  }

  async function loadCollection(path, setter, label) {
    try {
      const response = await fetch(`${API}${path}`)
      if (!response.ok) throw new Error(`${label} request failed`)

      const result = await response.json()
      if (!cancelled) {
        setter(Array.isArray(result) ? result : result.data ?? [])
      }
    } catch (error) {
      console.error(`Could not load ${label}:`, error)
    }
  }

  loadSummary()
  loadTrends()
  loadCollection('/api/budgets', setBudgets, 'budgets')
  loadCollection('/api/recurring', setRecurring, 'recurring payments')
  loadCollection('/api/anomalies', setAnomalies, 'anomalies')

  return () => {
    cancelled = true
  }
}, [])


  const availableMonths = useMemo(
    () =>
      [...new Set(budgets.map((item) => item.month))]
        .filter(Boolean)
        .sort(),
    [budgets],
  )

  const filteredBudgets = useMemo(
    () =>
      budgets
        .filter((item) => selectedMonth === 'all' || item.month === selectedMonth)
        .sort((a, b) => (b.overspend_amount ?? 0) - (a.overspend_amount ?? 0)),
    [budgets, selectedMonth],
  )

  const filteredRecurring = useMemo(() => {
    const search = recurringSearch.trim().toLowerCase()

    return recurring
      .filter((item) =>
        [
          item.user_id,
          item.account_id,
          item.merchant_id,
          item.transaction_type,
          item.cadence,
        ]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(search)),
      )
      .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
  }, [recurring, recurringSearch])

  const filteredAnomalies = useMemo(() => {
    const search = anomalySearch.trim().toLowerCase()

    return anomalies
      .filter((item) =>
        [
          item.transaction_id,
          item.user_id,
          item.account_id,
          item.merchant_id,
          item.transaction_type,
          item.transaction_date,
          item.description,
          item.category_id,
          item.anomaly_reason,
        ]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(search)),
      )
      .sort((a, b) => (Number(b.robust_z_score) || 0) - (Number(a.robust_z_score) || 0))
  }, [anomalies, anomalySearch])

  if (error) {
    return (
      <main className="dashboard">
        <p className="error">{error}</p>
      </main>
    )
  }

  if (!summary) {
    return <main className="dashboard"><p>Loading analytics...</p></main>
  }

  const metrics = [
    ['Total transactions', summary.transaction_count.toLocaleString('en-IN')],
    ['Expense transactions', summary.expense_transaction_count.toLocaleString('en-IN')],
    ['Refund transactions', summary.refund_transaction_count.toLocaleString('en-IN')],
    ['Gross expenses', formatINR(summary.gross_expenses)],
    ['Total refunds', formatINR(summary.refunds)],
    ['Net spending', formatINR(summary.net_spending)],
  ]

  const maxSpending = Math.max(
    ...monthlyData.map((item) => item.net_spending),
    1,
  )

  const budgetTotal = filteredBudgets.reduce(
    (total, item) => total + (Number(item.budget_amount) || 0),
    0,
  )

  const spendingTotal = filteredBudgets.reduce(
    (total, item) => total + (Number(item.net_spending) || 0),
    0,
  )

  const overspentBudgets = filteredBudgets.filter((item) => item.is_overspent)

  const overspendTotal = overspentBudgets.reduce(
    (total, item) => total + (Number(item.overspend_amount) || 0),
    0,
  )

  const highConfidenceCount = recurring.filter(
    (item) => Number(item.confidence) >= 70,
  ).length

  const averageRecurringAmount = recurring.length
    ? recurring.reduce(
        (total, item) => total + (Number(item.average_amount) || 0),
        0,
      ) / recurring.length
    : 0

  const anomalyAmountTotal = anomalies.reduce(
    (total, item) => total + (Number(item.amount) || 0),
    0,
  )

  return (
    <main className="dashboard">
      <header className="header">
        <div>
          <p className="eyebrow">PERSONAL FINANCE INTELLIGENCE</p>
          <h1>Household Spending Analytics</h1>
          <p className="subtitle">
            Understand transactions, spending trends, budgets, recurring bills and unusual activity.
          </p>
        </div>
        <span className="status"><span /> API connected</span>
      </header>

      <section className="metrics">
        {metrics.map(([label, value]) => (
          <article className="metric-card" key={label}>
            <p>{label}</p>
            <h2>{value}</h2>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">YEARLY OVERVIEW</p>
            <h2>Monthly Spending Trends</h2>
            <p className="subtitle">
              Combined net spending across all users for 2026, after refunds.
            </p>
          </div>
          <span className="data-count">{monthlyData.length} months</span>
        </div>

        {monthlyData.length === 0 ? (
          <p>No monthly trend data available.</p>
        ) : (
          <>
            <div className="chart">
              {monthlyData.map((item) => {
                const height = Math.max(
                  (item.net_spending / maxSpending) * 100,
                  1,
                )

                return (
                  <div className="chart-column" key={item.month}>
                    <span className="bar-value">
                      {formatCompactINR(item.net_spending)}
                    </span>
                    <div className="bar-track">
                      <div
                        className="bar"
                        style={{ height: `${height}%` }}
                        title={`${item.month}: ${formatINR(item.net_spending)}`}
                      />
                    </div>
                    <span className="month-label">
                      {new Date(`${item.month}-15T12:00:00`).toLocaleDateString(
                        'en-IN',
                        { month: 'short' },
                      )}
                    </span>
                  </div>
                )
              })}
            </div>

            <div className="chart-footer">
              <span>Net spending = gross expenses − refunds</span>
              <span>
                Annual total: {formatINR(
                  monthlyData.reduce(
                    (total, item) => total + item.net_spending,
                    0,
                  ),
                )}
              </span>
            </div>
          </>
        )}
      </section>

      <section className="panel budget-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">BUDGET PERFORMANCE</p>
            <h2>Budget vs. Actual Spending</h2>
            <p className="subtitle">
              Compare planned budgets with recorded net spending.
            </p>
          </div>

          <select
            className="month-select"
            value={selectedMonth}
            onChange={(event) => setSelectedMonth(event.target.value)}
            aria-label="Filter budgets by month"
          >
            <option value="all">All months</option>
            {availableMonths.map((month) => (
              <option key={month} value={month}>{month}</option>
            ))}
          </select>
        </div>

        <div className="budget-metrics">
          <article className="budget-stat">
            <p>Total budget</p>
            <h3>{formatINR(budgetTotal)}</h3>
          </article>
          <article className="budget-stat">
            <p>Actual spending</p>
            <h3>{formatINR(spendingTotal)}</h3>
          </article>
          <article className="budget-stat">
            <p>Overspent budgets</p>
            <h3>{overspentBudgets.length.toLocaleString('en-IN')}</h3>
          </article>
          <article className="budget-stat">
            <p>Total overspend</p>
            <h3 className="negative">{formatINR(overspendTotal)}</h3>
          </article>
        </div>

        <div className="table-wrap">
          <table className="budget-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>User</th>
                <th>Category</th>
                <th>Budget</th>
                <th>Actual spending</th>
                <th>Utilization</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredBudgets.slice(0, 100).map((item) => (
                <tr key={item.budget_id}>
                  <td>{item.month}</td>
                  <td>{item.user_id ?? '—'}</td>
                  <td>{item.category_id}</td>
                  <td>{formatINR(item.budget_amount)}</td>
                  <td>{formatINR(item.net_spending)}</td>
                  <td>
                    <div className="utilization">
                      <div className="utilization-track">
                        <div
                          className={`utilization-bar ${item.is_overspent ? 'over' : ''}`}
                          style={{
                            width: `${Math.min(
                              Math.max(Number(item.budget_utilization_pct) || 0, 0),
                              100,
                            )}%`,
                          }}
                        />
                      </div>
                      <span>
                        {(Number(item.budget_utilization_pct) || 0).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className={`budget-status ${item.is_overspent ? 'over' : 'within'}`}>
                      {item.is_overspent ? 'Overspent' : 'Within budget'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="table-note">
          Showing {Math.min(filteredBudgets.length, 100).toLocaleString('en-IN')} of{' '}
          {filteredBudgets.length.toLocaleString('en-IN')} budget records, sorted by highest overspend.
        </p>
      </section>

      <section className="panel recurring-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">REPEAT TRANSACTION DETECTION</p>
            <h2>Recurring Payments</h2>
            <p className="subtitle">
              Potential recurring bills identified from transaction patterns.
            </p>
          </div>
          <span className="data-count">
            {recurring.length.toLocaleString('en-IN')} patterns
          </span>
        </div>

        <div className="recurring-metrics">
          <article className="budget-stat">
            <p>Detected patterns</p>
            <h3>{recurring.length.toLocaleString('en-IN')}</h3>
          </article>
          <article className="budget-stat">
            <p>High-confidence patterns (70%+)</p>
            <h3>{highConfidenceCount.toLocaleString('en-IN')}</h3>
          </article>
          <article className="budget-stat">
            <p>Average payment amount</p>
            <h3>{formatINR(averageRecurringAmount)}</h3>
          </article>
        </div>

        <input
          className="recurring-search"
          type="search"
          placeholder="Search user, account, merchant, type or cadence..."
          value={recurringSearch}
          onChange={(event) => setRecurringSearch(event.target.value)}
          aria-label="Search recurring payments"
        />

        <div className="table-wrap">
          <table className="budget-table recurring-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Merchant</th>
                <th>Payment type</th>
                <th>Cadence</th>
                <th>Avg. amount</th>
                <th>Occurrences</th>
                <th>Avg. interval</th>
                <th>Confidence</th>
                <th>Last payment</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecurring.slice(0, 100).map((item, index) => (
                <tr
                  key={`${item.user_id}-${item.account_id}-${item.merchant_id}-${item.transaction_type}-${index}`}
                >
                  <td>{item.user_id}</td>
                  <td>{item.merchant_id}</td>
                  <td>{String(item.transaction_type ?? '').replaceAll('_', ' ')}</td>
                  <td>
                    <span className="cadence-badge">{item.cadence ?? 'Unknown'}</span>
                  </td>
                  <td>{formatINR(item.average_amount)}</td>
                  <td>{item.occurrences ?? 0}</td>
                  <td>
                    {item.average_interval_days != null
                      ? `${Number(item.average_interval_days).toFixed(0)} days`
                      : '—'}
                  </td>
                  <td>
                    <div className="confidence-cell">
                      <div className="utilization-track">
                        <div
                          className={`utilization-bar ${
                            Number(item.confidence) >= 70 ? '' : 'confidence-low'
                          }`}
                          style={{
                            width: `${Math.min(
                              Math.max(Number(item.confidence) || 0, 0),
                              100,
                            )}%`,
                          }}
                        />
                      </div>
                      <span>{Number(item.confidence ?? 0).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td>{item.last_date ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="table-note">
          Showing {Math.min(filteredRecurring.length, 100).toLocaleString('en-IN')} of{' '}
          {filteredRecurring.length.toLocaleString('en-IN')} matching patterns, sorted by confidence.
          These are detected patterns, not confirmed active subscriptions.
        </p>
      </section>

      <section className="panel anomaly-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">UNUSUAL SPENDING MONITOR</p>
            <h2>Anomaly Detection</h2>
            <p className="subtitle">
              Transactions flagged because their amounts differ from historical spending patterns.
              Flags are for review, not proof of fraud.
            </p>
          </div>
          <span className="data-count">
            {anomalies.length.toLocaleString('en-IN')} flagged
          </span>
        </div>

        <div className="recurring-metrics">
          <article className="budget-stat">
            <p>Flagged transactions</p>
            <h3>{anomalies.length.toLocaleString('en-IN')}</h3>
          </article>
          <article className="budget-stat">
            <p>Flagged amount total</p>
            <h3>{formatINR(anomalyAmountTotal)}</h3>
          </article>
          <article className="budget-stat">
            <p>Highest robust z-score</p>
            <h3>
              {Math.max(
                0,
                ...anomalies.map((item) => Number(item.robust_z_score) || 0),
              ).toFixed(1)}
            </h3>
          </article>
        </div>

        <input
          className="recurring-search"
          type="search"
          placeholder="Search transaction, user, merchant, category or reason..."
          value={anomalySearch}
          onChange={(event) => setAnomalySearch(event.target.value)}
          aria-label="Search anomalies"
        />

        <div className="table-wrap">
          <table className="budget-table anomaly-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Transaction</th>
                <th>User</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Historical median</th>
                <th>Robust z-score</th>
                <th>Category</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {filteredAnomalies.slice(0, 100).map((item) => (
                <tr key={item.transaction_id}>
                  <td>{item.transaction_date ?? '—'}</td>
                  <td>{item.transaction_id}</td>
                  <td>{item.user_id}</td>
                  <td>{item.description ?? '—'}</td>
                  <td className="anomaly-amount">{formatINR(item.amount)}</td>
                  <td>{formatINR(item.baseline_median)}</td>
                  <td>
                    <span className="z-score-badge">
                      {(Number(item.robust_z_score) || 0).toFixed(2)}
                    </span>
                  </td>
                  <td>{item.category_id ?? '—'}</td>
                  <td className="reason-cell">{item.anomaly_reason ?? 'Flagged for review'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="table-note">
          Showing {Math.min(filteredAnomalies.length, 100).toLocaleString('en-IN')} of{' '}
          {filteredAnomalies.length.toLocaleString('en-IN')} matching flagged transactions,
          sorted by highest robust z-score.
        </p>
      </section>

      <footer>
        Powered by Python, FastAPI, SQLite and React ·{' '}
        {summary.transaction_count.toLocaleString('en-IN')} transactions
      </footer>
    </main>
  )
}

export default App

import { Wallet, Users, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react'

const CATEGORY_LABELS = {
  accommodation: 'Accommodation',
  food: 'Food',
  activities: 'Activities',
  transport: 'Transport',
}

export default function BudgetSummary({ budget, travelers = 1 }) {
  if (!budget) return null

  const currency = budget.currency || 'USD'
  const format = (value) =>
    `${Number(value ?? 0).toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })} ${currency}`

  const categories = [
    { key: 'accommodation', value: budget.accommodation },
    { key: 'food', value: budget.food },
    { key: 'activities', value: budget.activities },
    { key: 'transport', value: budget.transport },
  ].filter((item) => Number(item.value) > 0)

  const total = Number(budget.total || 0)
  const maxValue = Math.max(...categories.map((item) => Number(item.value)), 1)

  const overBudget = Boolean(budget.over_budget)

  return (
    <section className={`budget${overBudget ? ' budget--over' : ''}`}>
      <header className="budget__header">
        <h3 className="budget__title">
          <Wallet aria-hidden="true" />
          Budget summary
        </h3>
        <span className="budget__estimate-badge">All figures are estimates</span>
      </header>

      <div className="budget__totals">
        <div className="budget__total">
          <span className="budget__total-label">Estimated trip cost</span>
          <span className="budget__total-value">{format(total)}</span>
        </div>
        <div className="budget__total">
          <span className="budget__total-label">
            <Users aria-hidden="true" /> Per person ({travelers})
          </span>
          <span className="budget__total-value">{format(budget.per_person)}</span>
        </div>
        <div className="budget__total">
          <span className="budget__total-label">Your budget</span>
          <span className="budget__total-value">{format(budget.budget)}</span>
        </div>
        <div className="budget__total">
          <span className="budget__total-label">
            {overBudget ? (
              <TrendingUp aria-hidden="true" />
            ) : (
              <TrendingDown aria-hidden="true" />
            )}
            {overBudget ? 'Over budget by' : 'Budget remaining'}
          </span>
          <span
            className={`budget__total-value ${
              overBudget ? 'budget__total-value--over' : 'budget__total-value--ok'
            }`}
          >
            {format(Math.abs(Number(budget.remaining ?? 0)))}
          </span>
        </div>
      </div>

      {categories.length > 0 && (
        <div className="budget__breakdown">
          {categories.map((item) => (
            <div className="budget__row" key={item.key}>
              <span className="budget__row-label">{CATEGORY_LABELS[item.key]}</span>
              <span className="budget__bar">
                <span
                  className={`budget__bar-fill budget__bar-fill--${item.key}`}
                  style={{ width: `${Math.max(4, (Number(item.value) / maxValue) * 100)}%` }}
                />
              </span>
              <span className="budget__row-value">{format(item.value)}</span>
            </div>
          ))}
        </div>
      )}

      {overBudget && (
        <div className="alert alert--warning budget__alert">
          <AlertTriangle className="alert__icon" aria-hidden="true" />
          <div className="alert__body">
            <h4 className="alert__title">This plan is over your budget</h4>
            <p className="alert__message">
              The estimated cost exceeds your budget by{' '}
              {format(budget.over_budget_amount)}. Consider a lower accommodation
              tier, fewer paid activities or a shorter trip.
            </p>
          </div>
        </div>
      )}

      {Array.isArray(budget.notes) && budget.notes.length > 0 && (
        <ul className="budget__notes">
          {budget.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </section>
  )
}

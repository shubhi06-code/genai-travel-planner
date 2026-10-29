import { useState } from 'react'
import { ChevronDown, ChevronUp, Utensils } from 'lucide-react'
import ActivityCard from './ActivityCard.jsx'

function formatDate(value) {
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export default function ItineraryDay({ day, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  const meals = day?.meals ?? {}
  const mealEntries = Object.entries(meals)

  return (
    <section className="day">
      <header className="day__header">
        <button
          type="button"
          className="day__toggle"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <span className="day__number">Day {day?.day_number}</span>
          <span className="day__heading">
            <span className="day__title">{day?.title || 'Day plan'}</span>
            <span className="day__date">
              {formatDate(day?.date)}
              {day?.theme ? ` · ${day.theme}` : ''}
            </span>
          </span>
          <span className="day__chevron" aria-hidden="true">
            {open ? <ChevronUp /> : <ChevronDown />}
          </span>
        </button>

        {Number(day?.daily_estimated_cost) > 0 && (
          <span className="day__cost">{day.daily_estimated_cost} est. / day</span>
        )}
      </header>

      {open && (
        <div className="day__body">
          {day?.summary && <p className="day__summary">{day.summary}</p>}

          <ul className="activity-list">
            {(day?.activities ?? []).map((activity, index) => (
              <ActivityCard key={`${activity.name}-${index}`} activity={activity} />
            ))}
          </ul>

          {mealEntries.length > 0 && (
            <div className="meals">
              <h4 className="meals__title">
                <Utensils aria-hidden="true" />
                Food suggestions
              </h4>
              <ul className="meals__list">
                {mealEntries.map(([meal, suggestion]) => (
                  <li key={meal}>
                    <span className="meals__label">{meal}</span>
                    <span className="meals__value">{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {day?.notes && <p className="day__notes">{day.notes}</p>}
        </div>
      )}
    </section>
  )
}

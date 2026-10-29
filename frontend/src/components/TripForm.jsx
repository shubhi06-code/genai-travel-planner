import { useMemo, useState } from 'react'
import {
  CalendarDays,
  Users,
  Wallet,
  Sparkles,
  Info,
} from 'lucide-react'
import { validatePreferences, buildRequestPayload } from '../services/api.js'

export const TRAVEL_STYLES = [
  { value: 'relaxed', label: 'Relaxed', hint: 'Slow days, plenty of rest and time to wander.' },
  { value: 'balanced', label: 'Balanced', hint: 'A mix of sightseeing, food and downtime.' },
  { value: 'packed', label: 'Packed', hint: 'See as much as possible in the time available.' },
  { value: 'adventure', label: 'Adventure', hint: 'Active days, outdoors and experiences.' },
  { value: 'cultural', label: 'Cultural', hint: 'Museums, history, art and local traditions.' },
  { value: 'romantic', label: 'Romantic', hint: 'Scenic spots, quiet tables and sunset views.' },
  { value: 'family-friendly', label: 'Family friendly', hint: 'Kid-friendly attractions with breaks built in.' },
]

export const ACCOMMODATION_OPTIONS = [
  { value: 'hostel', label: 'Hostel' },
  { value: 'guesthouse', label: 'Guesthouse' },
  { value: 'budget-hotel', label: 'Budget hotel' },
  { value: 'mid-range', label: 'Mid-range hotel' },
  { value: 'boutique', label: 'Boutique hotel' },
  { value: 'luxury', label: 'Luxury hotel' },
  { value: 'resort', label: 'Resort' },
]

export const TRANSPORTATION_OPTIONS = [
  { value: 'walking', label: 'Mostly walking' },
  { value: 'public-transit', label: 'Public transport' },
  { value: 'taxi-rideshare', label: 'Taxi / rideshare' },
  { value: 'rental-car', label: 'Rental car' },
  { value: 'mixed', label: 'A mix of everything' },
]

export const CURRENCIES = ['USD', 'EUR', 'GBP', 'TRY', 'INR', 'AUD', 'CAD', 'JPY']

export const INTERESTS = [
  'food', 'sightseeing', 'history', 'culture', 'art', 'architecture',
  'nature', 'hiking', 'adventure', 'beach', 'nightlife', 'shopping',
  'wellness', 'museums', 'photography', 'local-experience', 'family-friendly',
  'romantic', 'wildlife',
]

function todayISO() {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10)
}

export function emptyFormValues() {
  const start = todayISO()
  const end = new Date(Date.now() + 2 * 86400000)
  const offset = end.getTimezoneOffset()
  return {
    destination: '',
    start_date: start,
    end_date: new Date(end.getTime() - offset * 60000).toISOString().slice(0, 10),
    budget: '',
    currency: 'USD',
    travelers: 1,
    interests: [],
    travel_style: 'balanced',
    accommodation: 'mid-range',
    transportation: 'mixed',
    notes: '',
  }
}

/** Turn a saved trip's preferences back into editable form values. */
export function formValuesFromTrip(trip) {
  const prefs = trip?.preferences ?? {}
  return {
    destination: prefs.destination ?? trip?.destination ?? '',
    start_date: prefs.start_date ?? trip?.start_date ?? todayISO(),
    end_date: prefs.end_date ?? trip?.end_date ?? todayISO(),
    budget: prefs.budget ?? trip?.budget ?? '',
    currency: prefs.currency ?? trip?.currency ?? 'USD',
    travelers: prefs.travelers ?? trip?.travelers ?? 1,
    interests: prefs.interests ?? [],
    travel_style: prefs.travel_style ?? 'balanced',
    accommodation: prefs.accommodation ?? 'mid-range',
    transportation: prefs.transportation ?? 'mixed',
    notes: prefs.notes ?? '',
  }
}

export default function TripForm({
  initialValues,
  onSubmit,
  submitting = false,
  submitLabel = 'Generate itinerary',
  error = null,
}) {
  const [values, setValues] = useState(() => initialValues ?? emptyFormValues())
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})

  const minStart = useMemo(() => todayISO(), [])

  const setField = (name, value) => {
    setValues((prev) => {
      const next = { ...prev, [name]: value }
      // Keep the end date consistent when the start date moves past it.
      if (name === 'start_date' && next.end_date && next.end_date < next.start_date) {
        next.end_date = next.start_date
      }
      return next
    })
    if (touched[name]) {
      // Re-validate against the values as they will be after this change.
      setErrors((prevErrors) => {
        const merged = { ...values, [name]: value }
        return { ...prevErrors, ...validatePreferences(merged) }
      })
    }
  }

  const toggleInterest = (interest) => {
    // Use a functional update so two clicks inside the same React batch both
    // apply, instead of the second one overwriting the first from a stale
    // closure.
    setValues((prev) => {
      const selected = prev.interests.includes(interest)
      const next = selected
        ? prev.interests.filter((item) => item !== interest)
        : [...prev.interests, interest]
      return { ...prev, interests: next }
    })
  }

  const handleBlur = (name) => {
    setTouched((prev) => ({ ...prev, [name]: true }))
    setErrors(validatePreferences(values))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    const validationErrors = validatePreferences(values)
    setErrors(validationErrors)
    setTouched(
      Object.keys(values).reduce((acc, key) => ({ ...acc, [key]: true }), {}),
    )
    if (Object.keys(validationErrors).length > 0) {
      const firstField = Object.keys(validationErrors)[0]
      document.getElementById(`field-${firstField}`)?.focus()
      return
    }
    onSubmit?.(buildRequestPayload(values), values)
  }

  const fieldError = (name) => (touched[name] && errors[name] ? errors[name] : null)

  return (
    <form className="trip-form" onSubmit={handleSubmit} noValidate>
      {error && (
        <div className="alert alert--error" role="alert">
          <Info className="alert__icon" aria-hidden="true" />
          <div className="alert__body">
            <p className="alert__message">{error}</p>
          </div>
        </div>
      )}

      <fieldset className="form-section">
        <legend className="form-section__legend">
          <Sparkles aria-hidden="true" />
          Where and when
        </legend>

        <div className="form-grid">
          <div className="form-field form-field--wide">
            <label htmlFor="field-destination">Destination</label>
            <input
              id="field-destination"
              type="text"
              name="destination"
              value={values.destination}
              onChange={(e) => setField('destination', e.target.value)}
              onBlur={() => handleBlur('destination')}
              placeholder="e.g. Lisbon, Portugal"
              aria-invalid={Boolean(fieldError('destination'))}
              aria-describedby={fieldError('destination') ? 'error-destination' : undefined}
            />
            {fieldError('destination') && (
              <p className="form-error" id="error-destination">
                {fieldError('destination')}
              </p>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="field-start_date">Start date</label>
            <input
              id="field-start_date"
              type="date"
              name="start_date"
              min={minStart}
              value={values.start_date}
              onChange={(e) => setField('start_date', e.target.value)}
              onBlur={() => handleBlur('start_date')}
              aria-invalid={Boolean(fieldError('start_date'))}
              aria-describedby={fieldError('start_date') ? 'error-start_date' : undefined}
            />
            {fieldError('start_date') && (
              <p className="form-error" id="error-start_date">
                {fieldError('start_date')}
              </p>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="field-end_date">End date</label>
            <input
              id="field-end_date"
              type="date"
              name="end_date"
              min={values.start_date || minStart}
              value={values.end_date}
              onChange={(e) => setField('end_date', e.target.value)}
              onBlur={() => handleBlur('end_date')}
              aria-invalid={Boolean(fieldError('end_date'))}
              aria-describedby={fieldError('end_date') ? 'error-end_date' : undefined}
            />
            {fieldError('end_date') && (
              <p className="form-error" id="error-end_date">
                {fieldError('end_date')}
              </p>
            )}
          </div>
        </div>
      </fieldset>

      <fieldset className="form-section">
        <legend className="form-section__legend">
          <Wallet aria-hidden="true" />
          Budget and party
        </legend>

        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="field-budget">Total budget</label>
            <input
              id="field-budget"
              type="number"
              name="budget"
              min="1"
              step="1"
              inputMode="decimal"
              value={values.budget}
              onChange={(e) => setField('budget', e.target.value)}
              onBlur={() => handleBlur('budget')}
              placeholder="900"
              aria-invalid={Boolean(fieldError('budget'))}
              aria-describedby={fieldError('budget') ? 'error-budget' : 'hint-budget'}
            />
            {fieldError('budget') ? (
              <p className="form-error" id="error-budget">
                {fieldError('budget')}
              </p>
            ) : (
              <p className="form-hint" id="hint-budget">
                For the whole party, including accommodation and transport.
              </p>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="field-currency">Currency</label>
            <select
              id="field-currency"
              name="currency"
              value={values.currency}
              onChange={(e) => setField('currency', e.target.value)}
              onBlur={() => handleBlur('currency')}
              aria-invalid={Boolean(fieldError('currency'))}
            >
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="field-travelers">Number of travellers</label>
            <input
              id="field-travelers"
              type="number"
              name="travelers"
              min="1"
              max="20"
              step="1"
              inputMode="numeric"
              value={values.travelers}
              onChange={(e) => setField('travelers', e.target.value)}
              onBlur={() => handleBlur('travelers')}
              aria-invalid={Boolean(fieldError('travelers'))}
              aria-describedby={fieldError('travelers') ? 'error-travelers' : undefined}
            />
            {fieldError('travelers') && (
              <p className="form-error" id="error-travelers">
                {fieldError('travelers')}
              </p>
            )}
          </div>
        </div>
      </fieldset>

      <fieldset className="form-section">
        <legend className="form-section__legend">
          <Users aria-hidden="true" />
          Interests
        </legend>
        <p className="form-section__hint">
          Pick everything that matters to you - the more you choose, the more
          tailored the plan.
        </p>
        <div className="chip-grid" role="group" aria-label="Interests">
          {INTERESTS.map((interest) => {
            const selected = values.interests.includes(interest)
            return (
              <button
                type="button"
                key={interest}
                className={`chip${selected ? ' chip--active' : ''}`}
                aria-pressed={selected}
                onClick={() => toggleInterest(interest)}
              >
                {interest.replace(/-/g, ' ')}
              </button>
            )
          })}
        </div>
      </fieldset>

      <fieldset className="form-section">
        <legend className="form-section__legend">
          <CalendarDays aria-hidden="true" />
          Travel style and comfort
        </legend>

        <div className="form-grid">
          <div className="form-field form-field--wide">
            <label htmlFor="field-travel_style">Travel style / pace</label>
            <select
              id="field-travel_style"
              name="travel_style"
              value={values.travel_style}
              onChange={(e) => setField('travel_style', e.target.value)}
              onBlur={() => handleBlur('travel_style')}
              aria-invalid={Boolean(fieldError('travel_style'))}
            >
              {TRAVEL_STYLES.map((style) => (
                <option key={style.value} value={style.value}>
                  {style.label} - {style.hint}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="field-accommodation">Accommodation</label>
            <select
              id="field-accommodation"
              name="accommodation"
              value={values.accommodation}
              onChange={(e) => setField('accommodation', e.target.value)}
              onBlur={() => handleBlur('accommodation')}
              aria-invalid={Boolean(fieldError('accommodation'))}
            >
              {ACCOMMODATION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="field-transportation">Transportation</label>
            <select
              id="field-transportation"
              name="transportation"
              value={values.transportation}
              onChange={(e) => setField('transportation', e.target.value)}
              onBlur={() => handleBlur('transportation')}
              aria-invalid={Boolean(fieldError('transportation'))}
            >
              {TRANSPORTATION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field form-field--wide">
            <label htmlFor="field-notes">Anything else? (optional)</label>
            <textarea
              id="field-notes"
              name="notes"
              rows={3}
              value={values.notes}
              onChange={(e) => setField('notes', e.target.value)}
              placeholder="e.g. travelling with a toddler, one traveller has a shellfish allergy"
              maxLength={1000}
            />
          </div>
        </div>
      </fieldset>

      <div className="trip-form__actions">
        <button type="submit" className="btn btn--primary btn--lg" disabled={submitting}>
          {submitting ? (
            <>
              <span className="spinner spinner--sm" aria-hidden="true" />
              Building your itinerary...
            </>
          ) : (
            <>
              <Sparkles aria-hidden="true" />
              {submitLabel}
            </>
          )}
        </button>
        <p className="trip-form__note">
          It takes a few seconds. You can edit and regenerate at any time.
        </p>
      </div>
    </form>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Save,
  RefreshCw,
  Pencil,
  Printer,
  Share2,
  MapPin,
  CalendarDays,
  Users,
  Wallet,
  Info,
  Lightbulb,
  Check,
} from 'lucide-react'
import ItineraryDay from '../components/ItineraryDay.jsx'
import BudgetSummary from '../components/BudgetSummary.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { api } from '../services/api.js'

const PENDING_KEY = 'wanderly:pending-itinerary'

function formatDate(value) {
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export default function Itinerary() {
  const { tripId } = useParams()
  const navigate = useNavigate()

  const [state, setState] = useState({
    loading: true,
    error: null,
    preferences: null,
    itinerary: null,
    trip: null,
  })
  const [actionState, setActionState] = useState({ saving: false, regenerating: false })
  const [notice, setNotice] = useState(null)
  const [actionError, setActionError] = useState(null)

  const isNew = tripId === 'new'

  const load = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))

    try {
      if (isNew) {
        const raw = sessionStorage.getItem(PENDING_KEY)
        if (!raw) {
          setState({
            loading: false,
            error: 'That itinerary is no longer available. Please create a new trip.',
            preferences: null,
            itinerary: null,
            trip: null,
          })
          return
        }
        const parsed = JSON.parse(raw)
        setState({
          loading: false,
          error: null,
          preferences: parsed.preferences,
          itinerary: parsed.itinerary,
          trip: null,
        })
        return
      }

      const trip = await api.getTrip(tripId)
      setState({
        loading: false,
        error: null,
        preferences: trip.preferences,
        itinerary: trip.itinerary,
        trip,
      })
    } catch (err) {
      setState({
        loading: false,
        error: err.userMessage ?? err.message ?? 'Could not load the itinerary.',
        preferences: null,
        itinerary: null,
        trip: null,
      })
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId])

  const handleSave = async () => {
    setActionState((prev) => ({ ...prev, saving: true }))
    setActionError(null)
    setNotice(null)
    try {
      const saved = await api.saveTrip(state.preferences, state.itinerary)
      sessionStorage.removeItem(PENDING_KEY)
      setState((prev) => ({ ...prev, trip: saved }))
      setNotice('Trip saved. You can reopen it from My Trips.')
      navigate(`/itinerary/${saved.id}`, { replace: true })
    } catch (err) {
      setActionError(err.userMessage ?? err.message ?? 'Could not save the trip.')
    } finally {
      setActionState((prev) => ({ ...prev, saving: false }))
    }
  }

  const handleRegenerate = async () => {
    setActionState((prev) => ({ ...prev, regenerating: true }))
    setActionError(null)
    setNotice(null)
    try {
      const response = await api.generateItinerary(state.preferences)
      setState((prev) => ({ ...prev, itinerary: response.itinerary }))
      if (state.trip?.id) {
        await api.updateTrip(state.trip.id, { itinerary: response.itinerary })
        setNotice('Itinerary regenerated and your saved trip was updated.')
      } else {
        sessionStorage.setItem(
          PENDING_KEY,
          JSON.stringify({
            preferences: state.preferences,
            itinerary: response.itinerary,
          }),
        )
        setNotice('A fresh itinerary was generated.')
      }
    } catch (err) {
      setActionError(err.userMessage ?? err.message ?? 'Could not regenerate the itinerary.')
    } finally {
      setActionState((prev) => ({ ...prev, regenerating: false }))
    }
  }

  const handleShare = async () => {
    setActionError(null)
    try {
      const url = window.location.href
      if (navigator.share) {
        await navigator.share({ title: state.itinerary?.title || 'My itinerary', url })
        return
      }
      await navigator.clipboard.writeText(url)
      setNotice('Link copied to your clipboard.')
    } catch (err) {
      if (err?.name !== 'AbortError') {
        setActionError('Could not share this itinerary.')
      }
    }
  }

  const handlePrint = () => {
    window.print()
  }

  if (state.loading) {
    return (
      <section className="section">
        <div className="container">
          <LoadingSpinner label="Loading your itinerary..." />
        </div>
      </section>
    )
  }

  if (state.error) {
    return (
      <section className="section">
        <div className="container container--narrow">
          <ErrorMessage error={state.error} onRetry={load} title="Could not load the itinerary" />
          <Link to="/create" className="btn btn--primary">
            Create a new trip
          </Link>
        </div>
      </section>
    )
  }

  const { itinerary, preferences } = state
  if (!itinerary) return null

  const currency = itinerary.currency || preferences?.currency || 'USD'

  return (
    <section className="section">
      <div className="container">
        <button type="button" className="link-back" onClick={() => navigate(-1)}>
          <ArrowLeft aria-hidden="true" />
          Back
        </button>

        <header className="itinerary-header">
          <div>
            <h1 className="itinerary-header__title">{itinerary.title}</h1>
            {itinerary.summary && (
              <p className="itinerary-header__summary">{itinerary.summary}</p>
            )}
          </div>

          <div className="itinerary-actions no-print">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleSave}
              disabled={actionState.saving || Boolean(state.trip?.id)}
            >
              {state.trip?.id ? (
                <>
                  <Check aria-hidden="true" />
                  Saved
                </>
              ) : (
                <>
                  <Save aria-hidden="true" />
                  {actionState.saving ? 'Saving...' : 'Save trip'}
                </>
              )}
            </button>

            <button
              type="button"
              className="btn btn--secondary"
              onClick={handleRegenerate}
              disabled={actionState.regenerating}
            >
              <RefreshCw aria-hidden="true" />
              {actionState.regenerating ? 'Regenerating...' : 'Regenerate'}
            </button>

            <Link
              to="/create"
              state={{ editFrom: state.preferences }}
              className="btn btn--ghost"
            >
              <Pencil aria-hidden="true" />
              Edit preferences
            </Link>

            <button type="button" className="btn btn--ghost" onClick={handlePrint}>
              <Printer aria-hidden="true" />
              Print / PDF
            </button>

            <button type="button" className="btn btn--ghost" onClick={handleShare}>
              <Share2 aria-hidden="true" />
              Share
            </button>
          </div>
        </header>

        {notice && (
          <div className="alert alert--success" role="status">
            <Check className="alert__icon" aria-hidden="true" />
            <div className="alert__body">
              <p className="alert__message">{notice}</p>
            </div>
          </div>
        )}

        {actionError && (
          <ErrorMessage error={actionError} title="Action failed" />
        )}

        <div className="itinerary-overview">
          <div className="overview-item">
            <MapPin aria-hidden="true" />
            <div>
              <span className="overview-item__label">Destination</span>
              <span className="overview-item__value">
                {itinerary.destination || preferences?.destination}
              </span>
            </div>
          </div>
          <div className="overview-item">
            <CalendarDays aria-hidden="true" />
            <div>
              <span className="overview-item__label">Dates</span>
              <span className="overview-item__value">
                {formatDate(itinerary.start_date)} - {formatDate(itinerary.end_date)}
              </span>
            </div>
          </div>
          <div className="overview-item">
            <Users aria-hidden="true" />
            <div>
              <span className="overview-item__label">Duration</span>
              <span className="overview-item__value">
                {itinerary.duration_days} day{itinerary.duration_days === 1 ? '' : 's'} &middot;{' '}
                {itinerary.travelers} traveller{itinerary.travelers === 1 ? '' : 's'}
              </span>
            </div>
          </div>
          <div className="overview-item">
            <Wallet aria-hidden="true" />
            <div>
              <span className="overview-item__label">Estimated cost</span>
              <span className="overview-item__value">
                {Number(itinerary.budget?.total ?? 0).toLocaleString()} {currency}
              </span>
            </div>
          </div>
        </div>

        <BudgetSummary budget={itinerary.budget} travelers={itinerary.travelers} />

        {Array.isArray(itinerary.travel_tips) && itinerary.travel_tips.length > 0 && (
          <section className="tips">
            <h2 className="tips__title">
              <Lightbulb aria-hidden="true" />
              Travel tips
            </h2>
            <ul className="tips__list">
              {itinerary.travel_tips.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="days">
          <h2 className="section__title">Your day-by-day plan</h2>
          {itinerary.days.map((day) => (
            <ItineraryDay key={day.day_number} day={day} />
          ))}
        </section>

        {Array.isArray(itinerary.packing_list) && itinerary.packing_list.length > 0 && (
          <section className="tips">
            <h2 className="tips__title">Packing list</h2>
            <ul className="tips__list tips__list--chips">
              {itinerary.packing_list.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        <div className="disclaimer no-print">
          <Info aria-hidden="true" />
          <p>
            {itinerary.disclaimer ||
              'All costs, opening hours, transport schedules and availability are estimates and must be verified before travel.'}
          </p>
        </div>
      </div>
    </section>
  )
}

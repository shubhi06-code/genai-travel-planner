import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  MapPin,
  CalendarDays,
  Users,
  Wallet,
  Trash2,
  Copy,
  Pencil,
  Eye,
  Plus,
  Check,
  AlertTriangle,
} from 'lucide-react'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { api } from '../services/api.js'

function formatDate(value) {
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

const STATUS_LABELS = {
  upcoming: 'Upcoming',
  ongoing: 'Ongoing',
  past: 'Past',
}

export default function MyTrips() {
  const [state, setState] = useState({ loading: true, error: null, trips: [] })
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [notice, setNotice] = useState(null)
  const [actionError, setActionError] = useState(null)

  const load = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const response = await api.listTrips()
      setState({ loading: false, error: null, trips: response.trips ?? [] })
    } catch (err) {
      setState({
        loading: false,
        error: err.userMessage ?? err.message ?? 'Could not load your trips.',
        trips: [],
      })
    }
  }

  useEffect(() => {
    load()
  }, [])

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setActionError(null)
    try {
      await api.deleteTrip(deleteTarget.id)
      setState((prev) => ({
        ...prev,
        trips: prev.trips.filter((trip) => trip.id !== deleteTarget.id),
      }))
      setNotice(`Deleted "${deleteTarget.title || deleteTarget.destination}".`)
      setDeleteTarget(null)
    } catch (err) {
      setActionError(err.userMessage ?? err.message ?? 'Could not delete the trip.')
    } finally {
      setDeleting(false)
    }
  }

  const duplicate = async (trip) => {
    setActionError(null)
    try {
      await api.duplicateTrip(trip.id)
      setNotice(`Duplicated "${trip.title || trip.destination}".`)
      await load()
    } catch (err) {
      setActionError(err.userMessage ?? err.message ?? 'Could not duplicate the trip.')
    }
  }

  return (
    <section className="section">
      <div className="container">
        <header className="page-header page-header--row">
          <div>
            <h1 className="page-header__title">My trips</h1>
            <p className="page-header__lead">
              Every itinerary you have saved, ready to reopen, edit or share.
            </p>
          </div>
          <Link to="/create" className="btn btn--primary">
            <Plus aria-hidden="true" />
            New trip
          </Link>
        </header>

        {notice && (
          <div className="alert alert--success" role="status">
            <Check className="alert__icon" aria-hidden="true" />
            <div className="alert__body">
              <p className="alert__message">{notice}</p>
            </div>
          </div>
        )}

        {actionError && <ErrorMessage error={actionError} title="Action failed" />}

        {state.loading && (
          <LoadingSpinner label="Loading your trips..." />
        )}

        {!state.loading && state.error && (
          <ErrorMessage error={state.error} onRetry={load} title="Could not load your trips" />
        )}

        {!state.loading && !state.error && state.trips.length === 0 && (
          <div className="empty-state">
            <span className="empty-state__icon" aria-hidden="true">
              <MapPin />
            </span>
            <h2 className="empty-state__title">No trips yet</h2>
            <p className="empty-state__body">
              Create your first itinerary and it will appear here. Tell us where
              you want to go and we will build the plan for you.
            </p>
            <Link to="/create" className="btn btn--primary">
              <Plus aria-hidden="true" />
              Plan your first trip
            </Link>
          </div>
        )}

        {!state.loading && !state.error && state.trips.length > 0 && (
          <div className="trip-grid">
            {state.trips.map((trip) => (
              <article className="trip-card" key={trip.id}>
                <div className="trip-card__head">
                  <h2 className="trip-card__title">
                    {trip.title || trip.destination}
                  </h2>
                  <span
                    className={`badge badge--${trip.status || 'upcoming'}`}
                  >
                    {STATUS_LABELS[trip.status] || trip.status}
                  </span>
                </div>

                <p className="trip-card__destination">
                  <MapPin aria-hidden="true" />
                  {trip.destination}
                </p>

                <dl className="trip-card__meta">
                  <div>
                    <dt>
                      <CalendarDays aria-hidden="true" /> Dates
                    </dt>
                    <dd>
                      {formatDate(trip.start_date)} - {formatDate(trip.end_date)}
                    </dd>
                  </div>
                  <div>
                    <dt>
                      <Users aria-hidden="true" /> Travellers
                    </dt>
                    <dd>{trip.travelers}</dd>
                  </div>
                  <div>
                    <dt>
                      <Wallet aria-hidden="true" /> Estimated
                    </dt>
                    <dd>
                      {Number(trip.total_estimated_cost ?? 0).toLocaleString()} {trip.currency}
                    </dd>
                  </div>
                </dl>

                <div className="trip-card__actions">
                  <Link to={`/itinerary/${trip.id}`} className="btn btn--primary btn--sm">
                    <Eye aria-hidden="true" />
                    Open
                  </Link>
                  <Link to="/create" className="btn btn--ghost btn--sm">
                    <Pencil aria-hidden="true" />
                    Edit
                  </Link>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => duplicate(trip)}
                  >
                    <Copy aria-hidden="true" />
                    Duplicate
                  </button>
                  <button
                    type="button"
                    className="btn btn--danger-ghost btn--sm"
                    onClick={() => setDeleteTarget(trip)}
                  >
                    <Trash2 aria-hidden="true" />
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      {deleteTarget && (
        <div className="modal-backdrop" role="presentation" onClick={() => setDeleteTarget(null)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-title"
            onClick={(event) => event.stopPropagation()}
          >
            <span className="modal__icon" aria-hidden="true">
              <AlertTriangle />
            </span>
            <h2 className="modal__title" id="delete-title">
              Delete this trip?
            </h2>
            <p className="modal__body">
              "{deleteTarget.title || deleteTarget.destination}" will be removed
              permanently. This cannot be undone.
            </p>
            <div className="modal__actions">
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn--danger"
                onClick={confirmDelete}
                disabled={deleting}
              >
                <Trash2 aria-hidden="true" />
                {deleting ? 'Deleting...' : 'Delete trip'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

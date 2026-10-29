import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TripForm from '../components/TripForm.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { api } from '../services/api.js'

export default function CreateTrip() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (payload) => {
    setSubmitting(true)
    setError(null)
    try {
      const response = await api.generateItinerary(payload)
      // Keep the generated plan in session storage so the results page can
      // render it immediately without a second round trip.
      sessionStorage.setItem(
        'wanderly:pending-itinerary',
        JSON.stringify({
          preferences: payload,
          itinerary: response.itinerary,
        }),
      )
      navigate('/itinerary/new')
    } catch (err) {
      setError(err.userMessage ?? err.message ?? 'Could not generate the itinerary.')
      setSubmitting(false)
    }
  }

  return (
    <section className="section">
      <div className="container container--narrow">
        <header className="page-header">
          <h1 className="page-header__title">Plan your trip</h1>
          <p className="page-header__lead">
            A few details are all we need. The more you tell us about your
            budget, pace and interests, the more tailored the plan will be.
          </p>
        </header>

        {error && <ErrorMessage error={error} title="Could not build your itinerary" />}

        <TripForm onSubmit={handleSubmit} submitting={submitting} />
      </div>
    </section>
  )
}

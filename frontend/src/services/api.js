/**
 * API client for the Travel Itinerary Planner backend.
 *
 * The frontend NEVER talks to Gemini or Supabase directly - every request
 * goes through the Flask API. Secrets stay on the server.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(
  /\/+$/,
  '',
)

const TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT || 60000)

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'unknown', details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  /** Map a backend error into a message that is safe to show to the user. */
  get userMessage() {
    if (this.code === 'validation_error' && Array.isArray(this.details)) {
      const first = this.details[0]
      if (first?.message) {
        const field = first.field ? `${first.field}: ` : ''
        return `${field}${first.message}`
      }
    }
    return this.message
  }
}

/** Perform a request with a timeout and JSON parsing. */
async function request(path, { method = 'GET', body, signal } = {}) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)

  if (signal) {
    signal.addEventListener('abort', () => controller.abort(), { once: true })
  }

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (error) {
    clearTimeout(timeoutId)
    if (error.name === 'AbortError') {
      throw new ApiError(
        'The request timed out. The server may be slow or unreachable - please try again.',
        { code: 'timeout' },
      )
    }
    throw new ApiError(
      'Could not reach the backend. Make sure the API is running on ' + BASE_URL,
      { code: 'network_error' },
    )
  } finally {
    clearTimeout(timeoutId)
  }

  const text = await response.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const error = payload?.error
    throw new ApiError(
      error?.message || `The server returned an error (HTTP ${response.status}).`,
      {
        status: response.status,
        code: error?.code || 'http_error',
        details: error?.details ?? null,
      },
    )
  }

  if (payload === null) {
    throw new ApiError('The server returned a response that could not be parsed.', {
      status: response.status,
      code: 'invalid_response',
    })
  }

  return payload
}

/** Validate a preferences payload against the backend rules before sending. */
export function validatePreferences(values) {
  const errors = {}

  const destination = (values.destination || '').trim()
  if (!destination) {
    errors.destination = 'Enter a destination.'
  } else if (destination.length < 2) {
    errors.destination = 'Destination must be at least 2 characters.'
  }

  if (!values.start_date) {
    errors.start_date = 'Choose a start date.'
  } else if (new Date(`${values.start_date}T00:00:00`) < startOfToday()) {
    errors.start_date = 'The start date cannot be in the past.'
  }

  if (!values.end_date) {
    errors.end_date = 'Choose an end date.'
  } else if (values.start_date && values.end_date < values.start_date) {
    errors.end_date = 'The end date must be the same as or later than the start date.'
  }

  if (values.start_date && values.end_date && values.end_date >= values.start_date) {
    const days = daysBetween(values.start_date, values.end_date)
    if (days > MAX_TRIP_DAYS) {
      errors.end_date = `Trips can be at most ${MAX_TRIP_DAYS} days long.`
    }
  }

  const budget = Number(values.budget)
  if (values.budget === '' || values.budget === null || values.budget === undefined) {
    errors.budget = 'Enter a budget.'
  } else if (Number.isNaN(budget)) {
    errors.budget = 'Budget must be a number.'
  } else if (budget <= 0) {
    errors.budget = 'Budget must be greater than zero.'
  }

  const travelers = Number(values.travelers)
  if (values.travelers === '' || values.travelers === null || values.travelers === undefined) {
    errors.travelers = 'Enter the number of travellers.'
  } else if (!Number.isInteger(travelers) || travelers < 1) {
    errors.travelers = 'Traveller count must be a whole number of at least 1.'
  } else if (travelers > MAX_TRAVELERS) {
    errors.travelers = `At most ${MAX_TRAVELERS} travellers are supported.`
  }

  if (!values.travel_style) {
    errors.travel_style = 'Choose a travel style.'
  }
  if (!values.accommodation) {
    errors.accommodation = 'Choose an accommodation preference.'
  }
  if (!values.transportation) {
    errors.transportation = 'Choose a transportation preference.'
  }
  if (!values.currency) {
    errors.currency = 'Choose a currency.'
  }

  return errors
}

export const MAX_TRIP_DAYS = 14
export const MAX_TRAVELERS = 20

function startOfToday() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

function daysBetween(start, end) {
  const a = new Date(`${start}T00:00:00`)
  const b = new Date(`${end}T00:00:00`)
  return Math.round((b - a) / 86400000) + 1
}

/** Shape the form values into the exact JSON the backend expects. */
export function buildRequestPayload(values) {
  return {
    destination: values.destination.trim(),
    start_date: values.start_date,
    end_date: values.end_date,
    budget: Number(values.budget),
    currency: values.currency,
    travelers: Number(values.travelers),
    interests: values.interests || [],
    travel_style: values.travel_style,
    accommodation: values.accommodation,
    transportation: values.transportation,
    ...(values.notes?.trim() ? { notes: values.notes.trim() } : {}),
  }
}

export const api = {
  baseUrl: BASE_URL,

  health: () => request('/health'),

  meta: () => request('/api/meta'),

  generateItinerary: (values, options = {}) =>
    request('/api/generate-itinerary', {
      method: 'POST',
      body: buildRequestPayload(values),
      ...options,
    }),

  listTrips: () => request('/api/trips'),

  getTrip: (tripId) => request(`/api/trips/${encodeURIComponent(tripId)}`),

  saveTrip: (preferences, itinerary, extra = {}) =>
    request('/api/trips', {
      method: 'POST',
      body: {
        preferences: buildRequestPayload(preferences),
        itinerary,
        ...extra,
      },
    }),

  updateTrip: (tripId, patch) =>
    request(`/api/trips/${encodeURIComponent(tripId)}`, {
      method: 'PUT',
      body: patch,
    }),

  deleteTrip: (tripId) =>
    request(`/api/trips/${encodeURIComponent(tripId)}`, { method: 'DELETE' }),

  duplicateTrip: (tripId) =>
    request(`/api/trips/${encodeURIComponent(tripId)}/duplicate`, { method: 'POST' }),
}

export default api

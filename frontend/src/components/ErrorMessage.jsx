import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function ErrorMessage({ error, onRetry, title = 'Something went wrong' }) {
  if (!error) return null

  const message =
    typeof error === 'string'
      ? error
      : (error.userMessage ?? error.message ?? 'An unexpected error occurred.')

  return (
    <div className="alert alert--error" role="alert">
      <AlertTriangle className="alert__icon" aria-hidden="true" />
      <div className="alert__body">
        <h3 className="alert__title">{title}</h3>
        <p className="alert__message">{message}</p>
        {onRetry && (
          <button type="button" className="btn btn--secondary btn--sm" onClick={onRetry}>
            <RefreshCw aria-hidden="true" />
            Try again
          </button>
        )}
      </div>
    </div>
  )
}

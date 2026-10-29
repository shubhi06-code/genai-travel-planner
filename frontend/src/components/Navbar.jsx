import { useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Compass, Menu, X } from 'lucide-react'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/create', label: 'Plan a Trip' },
  { to: '/trips', label: 'My Trips' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const location = useLocation()

  const close = () => setOpen(false)

  return (
    <header className="navbar">
      <div className="navbar__inner container">
        <Link to="/" className="navbar__brand" onClick={close}>
          <Compass className="navbar__logo" aria-hidden="true" />
          <span>
            <span className="navbar__title">Wanderly</span>
            <span className="navbar__subtitle">Travel Itinerary Planner</span>
          </span>
        </Link>

        <button
          type="button"
          className="navbar__toggle"
          aria-expanded={open}
          aria-controls="primary-navigation"
          aria-label={open ? 'Close navigation menu' : 'Open navigation menu'}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>

        <nav
          id="primary-navigation"
          className={`navbar__nav${open ? ' navbar__nav--open' : ''}`}
          aria-label="Primary"
        >
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={close}
              className={({ isActive }) =>
                `navbar__link${isActive ? ' navbar__link--active' : ''}`
              }
            >
              {link.label}
            </NavLink>
          ))}
          <Link
            to="/create"
            className={`btn btn--primary navbar__cta${
              location.pathname === '/create' ? ' navbar__cta--active' : ''
            }`}
            onClick={close}
          >
            Plan My Trip
          </Link>
        </nav>
      </div>
    </header>
  )
}

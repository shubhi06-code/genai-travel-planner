import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <div className="footer__brand">
          <div className="footer__brandline">
            <Compass aria-hidden="true" />
            <strong>Wanderly</strong>
          </div>
          <p className="footer__tagline">
            Personalized, AI-assisted travel itineraries so you can spend less time
            planning and more time travelling.
          </p>
        </div>

        <nav className="footer__links" aria-label="Footer">
          <div className="footer__column">
            <h3>About</h3>
            <Link to="/">How it works</Link>
            <Link to="/create">Create a trip</Link>
            <Link to="/trips">My trips</Link>
          </div>
          <div className="footer__column">
            <h3>Contact</h3>
            <a href="mailto:hello@wanderly.example">hello@wanderly.example</a>
            <span>Support available 09:00 - 18:00</span>
          </div>
          <div className="footer__column">
            <h3>Legal</h3>
            <a href="#privacy">Privacy Policy</a>
            <a href="#terms">Terms of Use</a>
          </div>
        </nav>
      </div>

      <div className="container footer__bottom">
        <p>
          &copy; {new Date().getFullYear()} Wanderly. Costs, opening hours and
          transport times are estimates - always verify before you travel.
        </p>
      </div>
    </footer>
  )
}

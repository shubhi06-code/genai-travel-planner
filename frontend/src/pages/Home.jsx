import { Link } from 'react-router-dom'
import {
  Sparkles,
  Clock,
  Wallet,
  Route,
  MapPin,
  Utensils,
  BedDouble,
  CalendarCheck,
  ArrowRight,
} from 'lucide-react'

const FEATURES = [
  {
    icon: Sparkles,
    title: 'AI-written for you',
    body: 'Every plan is generated from your budget, pace and interests - not a generic city guide.',
  },
  {
    icon: Clock,
    title: 'Saves hours of research',
    body: 'Attractions, dining, stays and transfers arranged in one day-by-day schedule.',
  },
  {
    icon: Wallet,
    title: 'Budget you can see',
    body: 'A full cost breakdown per category, per person, and a warning before you overspend.',
  },
  {
    icon: Route,
    title: 'Logical routing',
    body: 'Nearby sights are grouped together so you spend your time exploring, not travelling.',
  },
]

const POPULAR = [
  {
    city: 'Lisbon, Portugal',
    blurb: 'Tiled streets, pastéis de nata and Atlantic light.',
    days: '3 days',
    budget: 'from 450 EUR',
  },
  {
    city: 'Kyoto, Japan',
    blurb: 'Temples, tea houses and quiet temple gardens.',
    days: '5 days',
    budget: 'from 900 EUR',
  },
  {
    city: 'Rome, Italy',
    blurb: 'Ancient ruins, long lunches and golden-hour piazzas.',
    days: '4 days',
    budget: 'from 700 EUR',
  },
]

const STEPS = [
  { step: '01', title: 'Tell us about your trip', body: 'Destination, dates, budget, travellers and what you love doing.' },
  { step: '02', title: 'Get a day-by-day plan', body: 'AI writes the schedule, the suggestions and the cost breakdown.' },
  { step: '03', title: 'Tweak and save', body: 'Edit, regenerate, save and reopen your plan whenever you need it.' },
]

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="container hero__inner">
          <div className="hero__content">
            <span className="hero__badge">
              <Sparkles aria-hidden="true" />
              AI-powered trip planning
            </span>
            <h1 className="hero__title">
              Stop planning the trip.
              <br />
              <span className="hero__title-accent">Start living it.</span>
            </h1>
            <p className="hero__lead">
              Tell us where, when and how you like to travel. We build a
              personalised day-by-day itinerary with attractions, dining,
              accommodation and transport - matched to your budget.
            </p>
            <div className="hero__actions">
              <Link to="/create" className="btn btn--primary btn--lg">
                Plan My Trip
                <ArrowRight aria-hidden="true" />
              </Link>
              <Link to="/trips" className="btn btn--ghost btn--lg">
                View my trips
              </Link>
            </div>
            <ul className="hero__stats">
              <li>
                <strong>Under 60s</strong>
                <span>to a full plan</span>
              </li>
              <li>
                <strong>Day-by-day</strong>
                <span>schedules</span>
              </li>
              <li>
                <strong>Live</strong>
                <span>cost estimates</span>
              </li>
            </ul>
          </div>

          <div className="hero__visual" aria-hidden="true">
            <div className="hero__card">
              <div className="hero__card-top">
                <MapPin />
                <span>Lisbon, Portugal</span>
              </div>
              <div className="hero__card-day">
                <span className="hero__badge-day">Day 1</span>
                <strong>Alfama and the riverfront</strong>
              </div>
              <ul className="hero__card-list">
                <li><span>09:30</span> Old town food walk</li>
                <li><span>12:30</span> Lunch at a local tasca</li>
                <li><span>15:00</span> Miradouro viewpoint</li>
              </ul>
              <div className="hero__card-footer">
                <Wallet />
                <span>Est. 120 EUR / person</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <h2 className="section__title">Why travellers use Wanderly</h2>
          <p className="section__lead">
            Planning fatigue is real. These four things take the bulk of the
            work out of your trip.
          </p>
          <div className="feature-grid">
            {FEATURES.map((feature) => (
              <article className="feature" key={feature.title}>
                <span className="feature__icon">
                  <feature.icon aria-hidden="true" />
                </span>
                <h3 className="feature__title">{feature.title}</h3>
                <p className="feature__body">{feature.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section section--muted">
        <div className="container">
          <h2 className="section__title">How it works</h2>
          <div className="steps">
            {STEPS.map((item) => (
              <div className="step" key={item.step}>
                <span className="step__number">{item.step}</span>
                <h3 className="step__title">{item.title}</h3>
                <p className="step__body">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <h2 className="section__title">Popular destinations</h2>
          <p className="section__lead">
            A few places travellers plan most. Pick one to start, or build your
            own from scratch.
          </p>
          <div className="destination-grid">
            {POPULAR.map((place) => (
              <article className="destination" key={place.city}>
                <div className="destination__body">
                  <h3 className="destination__city">{place.city}</h3>
                  <p className="destination__blurb">{place.blurb}</p>
                  <div className="destination__meta">
                    <span><CalendarCheck aria-hidden="true" /> {place.days}</span>
                    <span><Wallet aria-hidden="true" /> {place.budget}</span>
                  </div>
                  <Link to="/create" className="btn btn--secondary btn--sm">
                    Plan a trip here
                    <ArrowRight aria-hidden="true" />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section section--muted">
        <div className="container feature-detail">
          <div className="feature-detail__icon">
            <BedDouble aria-hidden="true" />
          </div>
          <div>
            <h2 className="section__title">Built for solo travellers, couples and groups</h2>
            <p className="section__lead">
              A weekend getaway for one, a relaxed anniversary for two, or a
              shared holiday for six. The pace, budget split and suggestions
              adapt to the size of your party.
            </p>
            <ul className="check-list">
              <li><Utensils aria-hidden="true" /> Dining suggestions per day, with break stops</li>
              <li><BedDouble aria-hidden="true" /> Accommodation matched to your comfort tier</li>
              <li><Route aria-hidden="true" /> Transport options that suit your budget</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="cta">
        <div className="container cta__inner">
          <h2>Ready to plan your next trip?</h2>
          <p>It takes less than a minute to get a complete first draft.</p>
          <Link to="/create" className="btn btn--primary btn--lg">
            Plan My Trip
            <ArrowRight aria-hidden="true" />
          </Link>
        </div>
      </section>
    </>
  )
}

import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Footer from './components/Footer.jsx'
import Home from './pages/Home.jsx'
import CreateTrip from './pages/CreateTrip.jsx'
import Itinerary from './pages/Itinerary.jsx'
import MyTrips from './pages/MyTrips.jsx'

export default function App() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <Navbar />
      <main id="main-content" className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/create" element={<CreateTrip />} />
          <Route path="/itinerary/:tripId" element={<Itinerary />} />
          <Route path="/trips" element={<MyTrips />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}

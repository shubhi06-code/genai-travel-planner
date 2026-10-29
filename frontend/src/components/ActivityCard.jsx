import {
  Clock,
  MapPin,
  Wallet,
  Lightbulb,
  Car,
  Utensils,
  BedDouble,
  Camera,
  Landmark,
  ShoppingBag,
  Coffee,
} from 'lucide-react'

const CATEGORY_ICONS = {
  attraction: Camera,
  food: Utensils,
  accommodation: BedDouble,
  transport: Car,
  leisure: Coffee,
  shopping: ShoppingBag,
  other: Landmark,
}

export default function ActivityCard({ activity }) {
  if (!activity) return null

  const Icon = CATEGORY_ICONS[activity.category] || Landmark
  const hasCost = Number(activity.estimated_cost) > 0

  return (
    <li className={`activity activity--${activity.category || 'other'}`}>
      <div className="activity__icon" aria-hidden="true">
        <Icon />
      </div>

      <div className="activity__body">
        <div className="activity__head">
          <h4 className="activity__name">{activity.name}</h4>
          {hasCost && (
            <span className="activity__cost">
              <Wallet aria-hidden="true" />
              {activity.estimated_cost} est.
            </span>
          )}
        </div>

        {(activity.time || activity.duration) && (
          <p className="activity__meta">
            {activity.time && (
              <span>
                <Clock aria-hidden="true" />
                {activity.time}
              </span>
            )}
            {activity.duration && (
              <span>
                <Clock aria-hidden="true" />
                {activity.duration}
              </span>
            )}
            {activity.location && (
              <span>
                <MapPin aria-hidden="true" />
                {activity.location}
              </span>
            )}
          </p>
        )}

        {activity.description && (
          <p className="activity__description">{activity.description}</p>
        )}

        {activity.transport_note && (
          <p className="activity__note activity__note--transport">
            <Car aria-hidden="true" />
            {activity.transport_note}
          </p>
        )}

        {activity.tip && (
          <p className="activity__note activity__note--tip">
            <Lightbulb aria-hidden="true" />
            {activity.tip}
          </p>
        )}

        {activity.cost_note && <p className="activity__note">{activity.cost_note}</p>}
      </div>
    </li>
  )
}

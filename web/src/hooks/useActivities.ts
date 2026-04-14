import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Activity } from '../types'

export function useActivities(limit = 40) {
  const [activities, setActivities] = useState<Activity[]>([])

  useEffect(() => {
    api.getActivities(limit)
      .then(r => setActivities(r.activities))
      .catch(() => { /* Strava not configured or unavailable */ })
  }, [limit])

  return activities
}

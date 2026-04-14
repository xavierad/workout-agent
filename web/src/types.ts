export interface Activity {
  id: number
  name: string
  sport_type: string
  date: string              // "YYYY-MM-DD"
  distance_km: number | null
  moving_time_min: number | null
  elevation_m: number | null
  avg_speed_kmh: number | null
  avg_heartrate: number | null
  avg_watts: number | null
  suffer_score: number | null
}

export interface Plan {
  objective: string
  plan: string
  updated_at: string
  pending_plan?: string
  pending_updated_at?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolsUsed?: string[]
  isStreaming?: boolean
}

export type SSEEvent =
  | { type: 'plan_adapted'; message: string }
  | { type: 'plan_accepted' }
  | { type: 'plan_updated' }

export type WSMessage =
  | { type: 'token'; content: string }
  | { type: 'tool_start'; name: string }
  | { type: 'tool_end'; name: string }
  | { type: 'done'; tools_used: string[] }

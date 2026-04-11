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

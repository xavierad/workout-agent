import type { Plan } from '../types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export interface AdaptResult {
  status: 'adapted' | 'no_changes' | 'no_new_activity'
  message?: string
  pending_plan?: string
}

export const api = {
  getPlan: () => request<Plan>('/api/plan'),
  acceptPlan: () => request<Plan>('/api/plan/accept', { method: 'POST' }),
  rejectPlan: () => request<void>('/api/plan/reject', { method: 'POST' }),
  triggerAdapt: () => request<AdaptResult>('/api/plan/adapt', { method: 'POST' }),
}

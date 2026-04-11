import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import type { Plan, SSEEvent } from '../types'

export function usePlan() {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notification, setNotification] = useState<string | null>(null)
  const [infoMessage, setInfoMessage] = useState<string | null>(null)
  const [isAdapting, setIsAdapting] = useState(false)

  // Use a ref so refresh() never becomes stale due to notification changes
  const notificationRef = useRef(notification)
  useEffect(() => { notificationRef.current = notification }, [notification])

  const refresh = useCallback(async () => {
    try {
      const data = await api.getPlan()
      setPlan(data)
      if (data.pending_plan && !notificationRef.current) {
        setNotification('Plan adapted — review and accept changes.')
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('404') || msg.includes('No plan')) {
        setPlan(null)
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, []) // stable — no stale deps

  const accept = useCallback(async () => {
    const updated = await api.acceptPlan()
    setPlan(updated)
    setNotification(null)
  }, [])

  const reject = useCallback(async () => {
    await api.rejectPlan()
    setPlan(prev => {
      if (!prev) return prev
      const next = { ...prev }
      delete next.pending_plan
      delete next.pending_updated_at
      return next
    })
    setNotification(null)
  }, [])

  const triggerAdapt = useCallback(async () => {
    setIsAdapting(true)
    try {
      const result = await api.triggerAdapt()
      if (result.status === 'adapted') {
        await refresh()
        // notification set by refresh() when it sees pending_plan
      } else {
        // no_new_activity or no_changes — surface the LLM's message as a transient info note
        setInfoMessage(result.message ?? 'Plan is up to date.')
      }
    } finally {
      setIsAdapting(false)
    }
  }, [refresh])

  useEffect(() => { refresh() }, [refresh])

  // SSE — stable subscription (refresh is now stable)
  useEffect(() => {
    const es = new EventSource('/api/events')
    es.onmessage = (e: MessageEvent) => {
      try {
        const event = JSON.parse(e.data as string) as SSEEvent
        if (event.type === 'plan_adapted') {
          refresh()
          setNotification(event.message)
        } else if (event.type === 'plan_accepted' || event.type === 'plan_updated') {
          refresh()
          setNotification(null)
        }
      } catch {
        // ignore parse errors
      }
    }
    return () => es.close()
  }, [refresh])

  return { plan, loading, error, notification, infoMessage, setInfoMessage, isAdapting, refresh, accept, reject, triggerAdapt }
}

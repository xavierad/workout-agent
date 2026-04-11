import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChatMessage, WSMessage } from '../types'

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isThinking, setIsThinking] = useState(false)
  const [activeTools, setActiveTools] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const currentToolsRef = useRef<string[]>([])
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/api/ws/chat`)

    ws.onmessage = (e: MessageEvent) => {
      const msg = JSON.parse(e.data as string) as WSMessage

      switch (msg.type) {
        case 'token':
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last?.isStreaming && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + msg.content },
              ]
            }
            return [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: msg.content,
                isStreaming: true,
              },
            ]
          })
          break

        case 'tool_start':
          currentToolsRef.current = [...currentToolsRef.current, msg.name]
          setActiveTools([...currentToolsRef.current])
          break

        case 'tool_end':
          setActiveTools(prev => prev.filter(t => t !== msg.name))
          break

        case 'done':
          setIsThinking(false)
          setActiveTools([])
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last?.isStreaming) {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  isStreaming: false,
                  toolsUsed: msg.tools_used,
                },
              ]
            }
            return prev
          })
          currentToolsRef.current = []
          break
      }
    }

    ws.onclose = () => {
      // Auto-reconnect after 2s if not intentionally closed
      reconnectRef.current = setTimeout(() => connect(), 2000)
    }

    wsRef.current = ws
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setIsThinking(true)
    setMessages(prev => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: text },
    ])
    wsRef.current.send(JSON.stringify({ message: text }))
  }, [])

  return { messages, isThinking, activeTools, sendMessage }
}

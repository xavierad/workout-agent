import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Wrench } from 'lucide-react'
import { clsx } from 'clsx'
import type { ChatMessage } from '../../types'

interface ChatProps {
  messages: ChatMessage[]
  isThinking: boolean
  activeTools: string[]
  onSend: (message: string) => void
}

export function Chat({ messages, isThinking, activeTools, onSend }: ChatProps) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isThinking) return
    onSend(text)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-grow textarea
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
  }

  return (
    <div className="flex flex-col h-full bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-zinc-800">
        <span className="text-sm font-semibold text-zinc-100">Coach</span>
        <span className="ml-2 text-xs text-zinc-500">Ask about your plan, zones, sessions…</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="text-sm text-zinc-600 text-center pt-8">
            Ask me anything about your training.
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Tool activity indicator */}
        {activeTools.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <Wrench className="w-3 h-3 animate-pulse text-brand-500" />
            <span>{activeTools.join(', ')}</span>
          </div>
        )}

        {/* Empty thinking (before first token) */}
        {isThinking && activeTools.length === 0 && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex gap-1 pl-1">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 px-4 py-3 border-t border-zinc-800">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Message your coach…"
            disabled={isThinking}
            className="
              flex-1 resize-none rounded-xl px-3 py-2.5 text-sm
              bg-zinc-800 border border-zinc-700 text-zinc-100
              placeholder:text-zinc-500
              focus:outline-none focus:border-brand-500
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors
            "
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isThinking}
            className="
              shrink-0 p-2.5 rounded-xl
              bg-brand-500 text-white
              hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed
              transition-colors
            "
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="mt-1.5 text-xs text-zinc-600">Enter to send · Shift+Enter for newline</p>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={clsx('flex flex-col gap-1', isUser && 'items-end')}>
      <div
        className={clsx(
          'rounded-2xl px-3.5 py-2.5 text-sm max-w-[90%]',
          isUser
            ? 'bg-brand-500 text-white rounded-br-sm'
            : 'bg-zinc-800 text-zinc-100 rounded-bl-sm',
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div
            className={clsx(
              'prose prose-sm prose-invert max-w-none',
              'prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-headings:my-2',
              'prose-pre:bg-zinc-900 prose-code:text-brand-400',
              message.isStreaming && 'typing-cursor',
            )}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>

      {/* Tools used tag */}
      {!isUser && message.toolsUsed && message.toolsUsed.length > 0 && (
        <div className="flex items-center gap-1 text-xs text-zinc-600 pl-1">
          <Wrench className="w-3 h-3" />
          {message.toolsUsed.join(', ')}
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Header } from './components/Header'
import { PendingBanner } from './components/PendingBanner'
import { PlanView } from './components/plan/PlanView'
import { PlanDiff } from './components/plan/PlanDiff'
import { Chat } from './components/chat/Chat'
import { usePlan } from './hooks/usePlan'
import { useChat } from './hooks/useChat'
import { useDarkMode } from './hooks/useDarkMode'
import { useActivities } from './hooks/useActivities'
import { ClipboardList, Info, X } from 'lucide-react'

export default function App() {
  const { plan, loading, error, notification, infoMessage, setInfoMessage, isAdapting, accept, reject, triggerAdapt } = usePlan()
  const { messages, isThinking, activeTools, sendMessage, clearHistory } = useChat()
  const { preference, cycle } = useDarkMode()
  const activities = useActivities()
  const [selectedWeek, setSelectedWeek] = useState(0)
  const [viewMode, setViewMode] = useState<'plan' | 'diff'>('plan')

  // Reset to week 1 whenever a new plan is loaded or updated
  useEffect(() => { setSelectedWeek(0) }, [plan?.updated_at])

  const toggleDiff = () =>
    setViewMode(v => (v === 'diff' ? 'plan' : 'diff'))

  const handleAccept = async () => {
    await accept()
    setViewMode('plan')
  }

  const handleReject = async () => {
    await reject()
    setViewMode('plan')
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header plan={plan} isAdapting={isAdapting} onAdapt={triggerAdapt} darkMode={preference} onToggleDark={cycle} />

      {notification && plan?.pending_plan && (
        <PendingBanner
          message={notification}
          viewMode={viewMode}
          onToggleDiff={toggleDiff}
          onAccept={handleAccept}
          onReject={handleReject}
        />
      )}

      {infoMessage && (
        <div className="flex items-center gap-3 px-6 py-2 bg-blue-50 dark:bg-blue-950/40 border-b border-blue-200 dark:border-blue-800 text-sm">
          <Info className="w-4 h-4 text-blue-500 dark:text-blue-400 shrink-0" />
          <span className="text-blue-700 dark:text-blue-300 flex-1">{infoMessage}</span>
          <button
            onClick={() => setInfoMessage(null)}
            className="p-0.5 rounded hover:bg-blue-100 dark:hover:bg-blue-900 text-blue-400 hover:text-blue-600 dark:hover:text-blue-300 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Plan / Diff panel */}
        <main className="flex-1 overflow-hidden border-r border-zinc-200">
          {loading ? (
            <div className="flex items-center justify-center h-full text-zinc-400 text-sm">
              Loading plan…
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-400 text-sm">
              Error: {error}
            </div>
          ) : !plan ? (
            <EmptyState />
          ) : viewMode === 'diff' && plan.pending_plan ? (
            <PlanDiff plan={plan} />
          ) : (
            <PlanView
              plan={plan}
              selectedWeek={selectedWeek}
              onWeekChange={setSelectedWeek}
              activities={activities}
            />
          )}
        </main>

        {/* Chat panel */}
        <aside className="w-[400px] shrink-0 overflow-hidden">
          <Chat
            messages={messages}
            isThinking={isThinking}
            activeTools={activeTools}
            onSend={sendMessage}
            onClear={clearHistory}
          />
        </aside>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-8">
      <div className="w-14 h-14 rounded-2xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
        <ClipboardList className="w-7 h-7 text-zinc-400" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">No plan yet</h2>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400 max-w-xs">
          Use the chat to describe your goal, or run{' '}
          <code className="font-mono text-xs bg-zinc-100 dark:bg-zinc-800 px-1 py-0.5 rounded">
            just plan objective="…"
          </code>
          {' '}to create your first plan.
        </p>
      </div>
    </div>
  )
}

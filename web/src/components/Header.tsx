import { Activity, RefreshCw, Zap } from 'lucide-react'
import type { Plan } from '../types'

interface HeaderProps {
  plan: Plan | null
  isAdapting: boolean
  onAdapt: () => void
}

export function Header({ plan, isAdapting, onAdapt }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-zinc-200 bg-white">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-brand-500" />
          <span className="font-bold text-zinc-900 text-lg tracking-tight">Workout Coach</span>
        </div>
        {plan?.objective && (
          <>
            <span className="text-zinc-300">·</span>
            <span className="text-sm text-zinc-500 truncate max-w-xs">{plan.objective}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-2">
        {plan && (
          <button
            onClick={onAdapt}
            disabled={isAdapting}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isAdapting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Activity className="w-4 h-4" />
            )}
            {isAdapting ? 'Adapting…' : 'Adapt Plan'}
          </button>
        )}
      </div>
    </header>
  )
}

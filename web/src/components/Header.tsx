import { Activity, RefreshCw, Dumbbell, Sun, Moon, Monitor } from 'lucide-react'
import type { Plan } from '../types'
import type { ThemePref } from '../hooks/useDarkMode'

interface HeaderProps {
  plan: Plan | null
  isAdapting: boolean
  onAdapt: () => void
  darkMode: ThemePref
  onToggleDark: () => void
}

const THEME_ICON = {
  system: Monitor,
  light: Sun,
  dark: Moon,
}

const THEME_LABEL = {
  system: 'Theme: system',
  light: 'Theme: light',
  dark: 'Theme: dark',
}

export function Header({ plan, isAdapting, onAdapt, darkMode, onToggleDark }: HeaderProps) {
  const ThemeIcon = THEME_ICON[darkMode]

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          {/* Logo mark */}
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shadow-sm">
            <Dumbbell className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-zinc-900 dark:text-zinc-100 text-lg tracking-tight">
            Workout Coach
          </span>
        </div>
        {plan?.objective && (
          <>
            <span className="text-zinc-300 dark:text-zinc-600">·</span>
            <span className="text-sm text-zinc-500 dark:text-zinc-400 truncate max-w-xs">
              {plan.objective}
            </span>
          </>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Theme cycle button */}
        <button
          onClick={onToggleDark}
          title={THEME_LABEL[darkMode]}
          className="p-2 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        >
          <ThemeIcon className="w-4 h-4" />
        </button>

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

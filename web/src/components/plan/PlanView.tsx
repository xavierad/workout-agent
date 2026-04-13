import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronLeft, ChevronRight, Bike, Footprints, Waves, Dumbbell, Moon } from 'lucide-react'
import { clsx } from 'clsx'
import type { Plan } from '../../types'
import { parsePlan, DAYS, DAY_SHORT, type WorkoutType, type DayWorkout, type ParsedWeek } from '../../lib/planParser'

// ── Workout type colours / icons ─────────────────────────────────────────────

const TYPE_STYLE: Record<WorkoutType, { bg: string; border: string; text: string; dot: string }> = {
  run:      { bg: 'bg-blue-50 dark:bg-blue-950/50',     border: 'border-blue-200 dark:border-blue-800',   text: 'text-blue-800 dark:text-blue-300',    dot: 'bg-blue-400' },
  bike:     { bg: 'bg-orange-50 dark:bg-orange-950/50', border: 'border-orange-200 dark:border-orange-800', text: 'text-orange-800 dark:text-orange-300', dot: 'bg-brand-400' },
  swim:     { bg: 'bg-cyan-50 dark:bg-cyan-950/50',     border: 'border-cyan-200 dark:border-cyan-800',   text: 'text-cyan-800 dark:text-cyan-300',    dot: 'bg-cyan-400' },
  strength: { bg: 'bg-purple-50 dark:bg-purple-950/50', border: 'border-purple-200 dark:border-purple-800', text: 'text-purple-800 dark:text-purple-300', dot: 'bg-purple-400' },
  rest:     { bg: 'bg-zinc-50 dark:bg-zinc-800',        border: 'border-zinc-200 dark:border-zinc-700',   text: 'text-zinc-400 dark:text-zinc-500',    dot: 'bg-zinc-300' },
  other:    { bg: 'bg-green-50 dark:bg-green-950/50',   border: 'border-green-200 dark:border-green-800',  text: 'text-green-800 dark:text-green-300',  dot: 'bg-green-400' },
}

function WorkoutIcon({ type, className }: { type: WorkoutType; className?: string }) {
  const cls = clsx('w-3.5 h-3.5 shrink-0', className)
  switch (type) {
    case 'run':      return <Footprints className={cls} />
    case 'bike':     return <Bike className={cls} />
    case 'swim':     return <Waves className={cls} />
    case 'strength': return <Dumbbell className={cls} />
    case 'rest':     return <Moon className={cls} />
    default:         return null
  }
}

// ── Calendar grid ─────────────────────────────────────────────────────────────

interface WeekCalendarProps {
  week: ParsedWeek
}

function WeekCalendar({ week }: WeekCalendarProps) {
  const [expanded, setExpanded] = useState<string | null>(null)

  // Index days by canonical name for O(1) lookup
  const byDay = Object.fromEntries(week.days.map(d => [d.day, d]))

  return (
    <div className="flex flex-col gap-4">
      {/* Summary / rationale */}
      {week.summary && (
        <div className="prose prose-sm prose-zinc dark:prose-invert max-w-none px-1 text-zinc-500 dark:text-zinc-400">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{week.summary}</ReactMarkdown>
        </div>
      )}

      {/* 7-column grid */}
      <div className="grid grid-cols-7 gap-2">
        {DAYS.map((day, di) => {
          const workout = byDay[day]
          const style = TYPE_STYLE[workout?.type ?? 'rest']
          const isExpanded = expanded === day

          return (
            <div key={day} className="flex flex-col gap-1">
              {/* Day header */}
              <div className="text-center">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
                  {DAY_SHORT[di]}
                </span>
              </div>

              {/* Workout card */}
              <button
                onClick={() => setExpanded(isExpanded ? null : day)}
                disabled={!workout}
                className={clsx(
                  'flex flex-col gap-1.5 rounded-xl border p-2.5 text-left transition-all',
                  'min-h-[80px] w-full',
                  workout ? [style.bg, style.border, 'hover:shadow-sm cursor-pointer'] : 'bg-zinc-50 dark:bg-zinc-800 border-zinc-100 dark:border-zinc-700 cursor-default',
                  isExpanded && 'ring-2 ring-brand-400 ring-offset-1 dark:ring-offset-zinc-900',
                )}
              >
                {workout ? (
                  <>
                    <div className="flex items-center gap-1.5">
                      <WorkoutIcon type={workout.type} className={style.text} />
                      <span className={clsx('text-xs font-semibold leading-tight', style.text)}>
                        {workout.title}
                      </span>
                    </div>
                    {/* Compact preview — first meaningful detail line */}
                    {!isExpanded && (
                      <p className="text-[11px] text-zinc-400 leading-snug line-clamp-3">
                        {workout.details
                          .split('\n')
                          .filter(l => l.trim() && !l.trim().startsWith('#'))
                          .slice(0, 3)
                          .join(' · ')
                          .replace(/\*+/g, '')}
                      </p>
                    )}
                  </>
                ) : (
                  <span className="text-xs text-zinc-300 dark:text-zinc-600 font-medium">Rest</span>
                )}
              </button>

              {/* Expanded detail popover */}
              {isExpanded && workout && (
                <div
                  className={clsx(
                    'rounded-xl border p-3 text-xs shadow-lg z-10',
                    style.bg, style.border,
                  )}
                >
                  <div
                    className="prose prose-xs dark:prose-invert max-w-none"
                    style={{ fontSize: '11px', lineHeight: '1.5' }}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{workout.details}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface PlanViewProps {
  plan: Plan
  selectedWeek: number
  onWeekChange: (n: number) => void
}

export function PlanView({ plan, selectedWeek, onWeekChange }: PlanViewProps) {
  const weeks = parsePlan(plan.plan)
  const safeWeek = Math.min(selectedWeek, weeks.length - 1)
  const current = weeks[safeWeek]

  // If parsing produced no day cards at all the content isn't a structured plan —
  // render raw Markdown instead of an empty calendar grid.
  const totalDays = weeks.reduce((n, w) => n + w.days.length, 0)
  if (totalDays === 0) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div className="flex-1 overflow-y-auto px-6 py-5 scrollbar-thin">
          <div className="prose prose-sm prose-zinc dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{plan.plan}</ReactMarkdown>
          </div>
        </div>
        <div className="shrink-0 px-6 py-2 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-400 dark:text-zinc-500">
          Last updated: {plan.updated_at ? new Date(plan.updated_at).toLocaleString() : '—'}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Week navigation tabs */}
      {weeks.length > 0 && (
        <div className="flex items-center gap-1 px-4 py-2 border-b border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-900 shrink-0 overflow-x-auto scrollbar-thin">
          <button
            onClick={() => onWeekChange(Math.max(0, safeWeek - 1))}
            disabled={safeWeek === 0}
            className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-4 h-4 text-zinc-500" />
          </button>

          {weeks.map((w, i) => (
            <button
              key={i}
              onClick={() => onWeekChange(i)}
              className={clsx(
                'px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-colors',
                safeWeek === i
                  ? 'bg-brand-500 text-white'
                  : 'text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800',
              )}
            >
              {w.title.replace(/^Week\s+/i, 'W')}
            </button>
          ))}

          <button
            onClick={() => onWeekChange(Math.min(weeks.length - 1, safeWeek + 1))}
            disabled={safeWeek === weeks.length - 1}
            className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="w-4 h-4 text-zinc-500" />
          </button>
        </div>
      )}

      {/* Calendar */}
      <div className="flex-1 overflow-y-auto px-6 py-5 scrollbar-thin">
        <div className="mb-3">
          <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-100">{current.title}</h2>
        </div>
        <WeekCalendar week={current} />
      </div>

      {/* Footer */}
      <div className="shrink-0 px-6 py-2 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-400 dark:text-zinc-500">
        {weeks.length > 1 && <span className="mr-3">Week {safeWeek + 1} of {weeks.length}</span>}
        Last updated: {plan.updated_at ? new Date(plan.updated_at).toLocaleString() : '—'}
      </div>
    </div>
  )
}

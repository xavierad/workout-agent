import { diffLines } from 'diff'
import type { Plan } from '../../types'

interface PlanDiffProps {
  plan: Plan
}

export function PlanDiff({ plan }: PlanDiffProps) {
  const original = plan.plan
  const modified = plan.pending_plan ?? ''
  const changes = diffLines(original, modified)

  const stats = changes.reduce(
    (acc, c) => {
      const count = c.value.split('\n').filter(Boolean).length
      if (c.added) acc.added += count
      if (c.removed) acc.removed += count
      return acc
    },
    { added: 0, removed: 0 },
  )

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-6 px-6 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-sm font-medium">
        <span className="text-zinc-500 dark:text-zinc-400">Comparing current → proposed</span>
        <span className="text-green-600 dark:text-green-400">+{stats.added} lines added</span>
        <span className="text-red-500 dark:text-red-400">−{stats.removed} lines removed</span>
        {plan.pending_updated_at && (
          <span className="ml-auto text-xs text-zinc-400 font-normal">
            Proposed {new Date(plan.pending_updated_at).toLocaleString()}
          </span>
        )}
      </div>

      {/* Diff body */}
      <div className="flex-1 overflow-y-auto font-mono text-xs leading-5 scrollbar-thin">
        {changes.map((change, ci) => {
          const lines = change.value.split('\n')
          // trailing empty string from split on trailing newline
          const rows = lines[lines.length - 1] === '' ? lines.slice(0, -1) : lines

          return rows.map((line, li) => (
            <div
              key={`${ci}-${li}`}
              className={`flex items-start px-4 py-px ${
                change.added
                  ? 'bg-green-50 dark:bg-green-950/50 border-l-4 border-green-400 dark:border-green-700'
                  : change.removed
                    ? 'bg-red-50 dark:bg-red-950/50 border-l-4 border-red-400 dark:border-red-700'
                    : 'border-l-4 border-transparent'
              }`}
            >
              <span
                className={`shrink-0 w-5 select-none ${
                  change.added
                    ? 'text-green-600 dark:text-green-400'
                    : change.removed
                      ? 'text-red-500 dark:text-red-400'
                      : 'text-zinc-300 dark:text-zinc-600'
                }`}
              >
                {change.added ? '+' : change.removed ? '−' : ' '}
              </span>
              <span
                className={`break-all whitespace-pre-wrap ${
                  change.added
                    ? 'text-green-900 dark:text-green-300'
                    : change.removed
                      ? 'text-red-800 dark:text-red-400 line-through opacity-70'
                      : 'text-zinc-500 dark:text-zinc-400'
                }`}
              >
                {line || '\u00a0'}
              </span>
            </div>
          ))
        })}
      </div>
    </div>
  )
}

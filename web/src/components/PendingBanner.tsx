import { Check, Diff, X } from 'lucide-react'

interface PendingBannerProps {
  message: string
  viewMode: 'plan' | 'diff'
  onToggleDiff: () => void
  onAccept: () => void
  onReject: () => void
}

export function PendingBanner({ message, viewMode, onToggleDiff, onAccept, onReject }: PendingBannerProps) {
  return (
    <div className="flex items-center gap-3 px-6 py-2.5 bg-amber-50 border-b border-amber-200 text-sm">
      <span className="text-amber-600 font-medium flex-1">{message}</span>
      <button
        onClick={onToggleDiff}
        className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
          viewMode === 'diff'
            ? 'bg-amber-200 text-amber-800'
            : 'bg-white border border-amber-200 text-amber-700 hover:bg-amber-100'
        }`}
      >
        <Diff className="w-3.5 h-3.5" />
        {viewMode === 'diff' ? 'Hide diff' : 'View diff'}
      </button>
      <button
        onClick={onAccept}
        className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
      >
        <Check className="w-3.5 h-3.5" />
        Accept
      </button>
      <button
        onClick={onReject}
        className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
        Discard
      </button>
    </div>
  )
}

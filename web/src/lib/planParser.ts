// ── Types ─────────────────────────────────────────────────────────────────────

export const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] as const
export const DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

export type WorkoutType = 'run' | 'bike' | 'swim' | 'strength' | 'rest' | 'other'

export interface DayWorkout {
  day: string
  title: string
  details: string
  type: WorkoutType
}

export interface ParsedWeek {
  title: string
  summary: string
  days: DayWorkout[]
}

// ── Inference ─────────────────────────────────────────────────────────────────

export function inferWorkoutType(text: string): WorkoutType {
  const t = text.toLowerCase()
  if (/rest|recovery|off|deload/.test(t)) return 'rest'
  if (/run|jog|tempo|interval|easy run|long run|5k|10k|marathon/.test(t)) return 'run'
  if (/bike|cycl|ride|power|ftp|zwift|gran fondo|climbing/.test(t)) return 'bike'
  if (/swim|pool|open water/.test(t)) return 'swim'
  if (/strength|gym|lift|weights|core|yoga|stretch/.test(t)) return 'strength'
  return 'other'
}

// ── Week content parser ───────────────────────────────────────────────────────

function parseWeekDays(weekContent: string): { summary: string; days: DayWorkout[] } {
  const lines = weekContent.split('\n')
  // Match:  ### Monday  |  **Monday**  |  * Monday:  |  - Monday:  |  Monday:
  const dayPattern = new RegExp(
    `^#{1,4}\\s*(${DAYS.join('|')})\\b` +
    `|^\\*\\*(${DAYS.join('|')})\\b` +
    `|^[*\\-]\\s*(${DAYS.join('|')})\\s*:` +
    `|^(${DAYS.join('|')})\\s*:`,
    'i',
  )

  const dayStarts: { index: number; day: string }[] = []
  lines.forEach((line, i) => {
    const m = line.match(dayPattern)
    if (m) {
      const day = (m[1] ?? m[2] ?? m[3] ?? m[4]).trim()
      dayStarts.push({ index: i, day })
    }
  })

  const summaryEnd = dayStarts.length > 0 ? dayStarts[0].index : lines.length
  const summary = lines.slice(0, summaryEnd).join('\n').trim()

  if (dayStarts.length === 0) return { summary, days: [] }

  const days: DayWorkout[] = dayStarts.map(({ index, day }, i) => {
    const end = i + 1 < dayStarts.length ? dayStarts[i + 1].index : lines.length
    // For bullet-style lines the content is on the same line after the day name
    const headerLine = lines[index]
    const inlineSuffix = headerLine
      .replace(new RegExp(`^[*\\-]?\\s*\\*{0,2}${day}\\*{0,2}\\s*:?\\s*`, 'i'), '')
      .trim()
    const bodyLines = lines.slice(index + 1, end).join('\n').trim()
    const body = inlineSuffix
      ? inlineSuffix + (bodyLines ? '\n' + bodyLines : '')
      : bodyLines
    const titleLine = body.split('\n').find(l => l.trim()) ?? ''
    const title = titleLine.replace(/^[#*\-\s]+/, '').replace(/\*+/g, '').trim() || day
    const canonical = DAYS.find(d => d.toLowerCase() === day.toLowerCase()) ?? day
    return { day: canonical, title, details: body, type: inferWorkoutType(`${day} ${body}`) }
  })

  return { summary, days }
}

// ── Top-level entry point ─────────────────────────────────────────────────────

export function parsePlan(markdown: string): ParsedWeek[] {
  const lines = markdown.split('\n')
  const weekStarts: { index: number; title: string }[] = []

  lines.forEach((line, i) => {
    // Match: ## Week 1  |  ## Week of April 13th  |  # Week 1: Base Block  etc.
    if (/^#{1,3}\s+week\b/i.test(line.trim())) {
      weekStarts.push({ index: i, title: line.replace(/^#+\s*/, '').trim() })
    }
  })

  if (weekStarts.length === 0) {
    const { summary, days } = parseWeekDays(markdown)
    return [{ title: 'Plan', summary, days }]
  }

  return weekStarts.map(({ index, title }, i) => {
    const end = i + 1 < weekStarts.length ? weekStarts[i + 1].index : lines.length
    const content = lines.slice(index + 1, end).join('\n')
    const { summary, days } = parseWeekDays(content)
    return { title, summary, days }
  })
}

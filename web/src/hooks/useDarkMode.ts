import { useEffect, useState } from 'react'

export type ThemePref = 'system' | 'light' | 'dark'

function applyTheme(pref: ThemePref) {
  const isDark =
    pref === 'dark' ||
    (pref === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', isDark)
}

export function useDarkMode() {
  const [preference, setPreference] = useState<ThemePref>(() => {
    return (localStorage.getItem('theme') as ThemePref) ?? 'system'
  })

  // Apply class whenever preference changes
  useEffect(() => {
    applyTheme(preference)
  }, [preference])

  // Track system-level changes when in 'system' mode
  useEffect(() => {
    if (preference !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme('system')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [preference])

  // Cycle: system → light → dark → system
  const cycle = () => {
    const next: ThemePref =
      preference === 'system' ? 'light' : preference === 'light' ? 'dark' : 'system'
    if (next === 'system') {
      localStorage.removeItem('theme')
    } else {
      localStorage.setItem('theme', next)
    }
    setPreference(next)
  }

  return { preference, cycle }
}

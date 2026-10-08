export type Season = 'spring' | 'summer' | 'autumn' | 'winter'

export interface SeasonalInfo {
  currentSeason: Season
  nextSeason: Season
  seasonName: string
  nextSeasonName: string
  icon: string
  nextIcon: string
  daysUntilNext: number
  hoursUntilNext: number
  countdownText: string
  badgeText: string
  nextDate: Date
  accentColor: string
  accentLight: string
  bgGlowClass: string
}

export function getSeasonalInfo(date: Date = new Date()): SeasonalInfo {
  const year = date.getFullYear()

  // Astronomical season transitions in Northern Hemisphere
  const springStart = new Date(year, 2, 20, 0, 0, 0) // March 20
  const summerStart = new Date(year, 5, 21, 0, 0, 0) // June 21
  const autumnStart = new Date(year, 8, 22, 0, 0, 0) // September 22
  const winterStart = new Date(year, 11, 21, 0, 0, 0) // December 21

  let currentSeason: Season
  let nextSeason: Season
  let seasonName: string
  let nextSeasonName: string
  let icon: string
  let nextIcon: string
  let nextDate: Date
  let accentColor: string
  let accentLight: string
  let bgGlowClass: string

  const time = date.getTime()

  if (time >= springStart.getTime() && time < summerStart.getTime()) {
    currentSeason = 'spring'
    nextSeason = 'summer'
    seasonName = 'Spring'
    nextSeasonName = 'Summer'
    icon = '🌸'
    nextIcon = '☀️'
    nextDate = summerStart
    accentColor = '#10b981'
    accentLight = '#6ee7b7'
    bgGlowClass = 'from-emerald-500/10 to-teal-500/10'
  } else if (time >= summerStart.getTime() && time < autumnStart.getTime()) {
    currentSeason = 'summer'
    nextSeason = 'autumn'
    seasonName = 'Summer'
    nextSeasonName = 'Autumn'
    icon = '☀️'
    nextIcon = '🍂'
    nextDate = autumnStart
    accentColor = '#06b6d4'
    accentLight = '#67e8f9'
    bgGlowClass = 'from-cyan-500/10 to-amber-500/10'
  } else if (time >= autumnStart.getTime() && time < winterStart.getTime()) {
    currentSeason = 'autumn'
    nextSeason = 'winter'
    seasonName = 'Autumn'
    nextSeasonName = 'Winter'
    icon = '🍂'
    nextIcon = '❄️'
    nextDate = winterStart
    accentColor = '#f97316'
    accentLight = '#fdba74'
    bgGlowClass = 'from-amber-600/15 to-orange-500/10'
  } else {
    currentSeason = 'winter'
    nextSeason = 'spring'
    seasonName = 'Winter'
    nextSeasonName = 'Spring'
    icon = '❄️'
    nextIcon = '🌸'
    nextDate = time >= winterStart.getTime() ? new Date(year + 1, 2, 20, 0, 0, 0) : springStart
    accentColor = '#38bdf8'
    accentLight = '#bae6fd'
    bgGlowClass = 'from-sky-500/15 to-indigo-500/10'
  }

  const diffMs = Math.max(0, nextDate.getTime() - date.getTime())
  const daysUntilNext = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
  const hoursUntilNext = Math.ceil(diffMs / (1000 * 60 * 60))
  const countdownText = `${daysUntilNext}d until ${nextSeasonName}`
  const badgeText = `${icon} ${seasonName} • ${countdownText}`

  return {
    currentSeason,
    nextSeason,
    seasonName,
    nextSeasonName,
    icon,
    nextIcon,
    daysUntilNext,
    hoursUntilNext,
    countdownText,
    badgeText,
    nextDate,
    accentColor,
    accentLight,
    bgGlowClass,
  }
}

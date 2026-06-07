import type { PortfolioSnapshot } from './types.ts'

export interface ChartDataPoint {
  timestamp: string
  [agentName: string]: number | string
}

function toDateKey(iso: string): string {
  const d = new Date(iso)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

function formatDateLabel(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric' })
}

/**
 * For each calendar day in `snapshots`, take the latest snapshot per agent and
 * pivot rows by day. Returns `[]` when the input is empty — callers can skip
 * rendering instead of asserting a non-empty Map.
 */
export function pivotLatestDailySnapshotsByDay(snapshots: PortfolioSnapshot[]): ChartDataPoint[] {
  if (snapshots.length === 0) return []

  const daily = new Map<string, Map<string, { iso: string; value: number }>>()

  for (const s of snapshots) {
    const dk = toDateKey(s.timestamp)
    if (!daily.has(dk)) daily.set(dk, new Map())
    daily.get(dk)!.set(s.agentName, {
      iso: s.timestamp,
      value: Math.round(s.totalValue * 100) / 100,
    })
  }

  return Array.from(daily.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .flatMap(([, agents]) => {
      const first = agents.values().next().value
      if (!first) return []
      const row: ChartDataPoint = { timestamp: formatDateLabel(first.iso) }
      for (const [name, { value }] of agents) {
        row[name] = value
      }
      return [row]
    })
}

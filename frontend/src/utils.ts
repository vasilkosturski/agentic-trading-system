import type { MantineColor } from '@mantine/core'
import type { RunStatus, TradeDecision } from './types.ts'

export function statusColor(status: RunStatus | string): MantineColor {
  switch (status) {
    case 'COMPLETED':
      return 'green'
    case 'IN_PROGRESS':
      return 'yellow'
    case 'FAILED':
      return 'red'
    default:
      return 'gray'
  }
}

export function decisionColor(decision: TradeDecision | null): MantineColor {
  switch (decision) {
    case 'BUY':
      return 'green'
    case 'SELL':
      return 'red'
    case 'HOLD':
      return 'gray'
    default:
      return 'gray'
  }
}

export function formatTimestamp(ts: string | null): string {
  if (!ts) return '\u2014'
  return new Date(ts).toLocaleString()
}

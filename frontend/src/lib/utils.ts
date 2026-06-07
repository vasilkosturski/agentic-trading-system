import type { MantineColor } from '@mantine/core'
import { format } from 'date-fns'
import type { RunStatus, TradeDecision } from './types.ts'

export function formatCurrency(value: number | null): string {
  if (value == null) return '--'
  return `$${new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)}`
}

export function formatPercent(value: number | null): string {
  if (value == null) return '--'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

export function pnlColor(value: number | null): string {
  if (value == null) return 'dimmed'
  return value >= 0 ? 'teal' : 'red'
}

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

export function decisionColor(decision: TradeDecision | string | null): MantineColor {
  switch (decision) {
    case 'BUY':
      return 'green'
    case 'SELL':
      return 'red'
    case 'SHORT':
      return 'orange'
    case 'HOLD':
      return 'gray'
    default:
      // Unknown wire-shape values (e.g., backend introduces a new transaction
      // type) fall back to a neutral pill instead of crashing the badge.
      return 'gray'
  }
}

export function formatTimestamp(ts: string | null): string {
  if (!ts) return '\u2014'
  // Use a fixed pattern so the rendered string is identical across hosts and
  // does not drift with the user's locale settings (the previous
  // toLocaleString() output broke snapshot comparisons and made CI logs
  // hard to grep).
  return format(new Date(ts), 'yyyy-MM-dd HH:mm')
}

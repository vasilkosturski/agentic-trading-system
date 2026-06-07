import { describe, it, expect } from 'vitest'
import { formatDuration } from './runDetailFormat'
import { formatTimestamp } from '@/lib/utils'

describe('formatDuration', () => {
  it('formats a completed run as seconds with one decimal', () => {
    const startedAt = '2025-01-01T00:00:00.000Z'
    const completedAt = '2025-01-01T00:00:02.500Z'

    const formatted = formatDuration(startedAt, completedAt)

    expect(formatted).toBe('2.5s')
  })

  it('returns "In progress" when completedAt is null', () => {
    expect(formatDuration('2025-01-01T00:00:00.000Z', null)).toBe('In progress')
  })
})

describe('formatTimestamp', () => {
  it('returns the em-dash placeholder when timestamp is null', () => {
    expect(formatTimestamp(null)).toBe('—')
  })

  it('renders a deterministic yyyy-MM-dd HH:mm pattern (no locale drift)', () => {
    // Output is host-local, so use a regex rather than asserting a specific
    // wall-clock value. The point is the *shape* — no commas, no AM/PM, no
    // "Jan 1, 2025, 5:30 PM" locale output.
    const formatted = formatTimestamp('2025-01-01T17:30:00Z')
    expect(formatted).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
  })
})

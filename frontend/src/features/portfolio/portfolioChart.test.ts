import { describe, it, expect } from 'vitest'
import { pivotLatestDailySnapshotsByDay } from './portfolioChart'
import type { PortfolioSnapshot } from '@/lib/types'

describe('pivotLatestDailySnapshotsByDay', () => {
  it('returns [] for an empty snapshot list (no non-null assertion blow-up)', () => {
    expect(pivotLatestDailySnapshotsByDay([])).toEqual([])
  })

  it('pivots one snapshot per agent per day into a single row keyed by day label', () => {
    const snapshots: PortfolioSnapshot[] = [
      {
        agentName: 'Warren',
        timestamp: '2025-03-15T10:00:00Z',
        totalValue: 10000,
        cashBalance: null,
        holdingsValue: null,
        totalPnl: null,
        totalReturnPercent: null,
      },
      {
        agentName: 'Ben',
        timestamp: '2025-03-15T12:00:00Z',
        totalValue: 9000,
        cashBalance: null,
        holdingsValue: null,
        totalPnl: null,
        totalReturnPercent: null,
      },
    ]

    const out = pivotLatestDailySnapshotsByDay(snapshots)
    expect(out).toHaveLength(1)
    expect(out[0]['Warren']).toBe(10000)
    expect(out[0]['Ben']).toBe(9000)
  })

  it('keeps only the latest snapshot for the agent on a given day', () => {
    const snapshots: PortfolioSnapshot[] = [
      {
        agentName: 'Warren',
        timestamp: '2025-03-15T10:00:00Z',
        totalValue: 10000,
        cashBalance: null,
        holdingsValue: null,
        totalPnl: null,
        totalReturnPercent: null,
      },
      {
        agentName: 'Warren',
        timestamp: '2025-03-15T18:00:00Z',
        totalValue: 11000,
        cashBalance: null,
        holdingsValue: null,
        totalPnl: null,
        totalReturnPercent: null,
      },
    ]

    const out = pivotLatestDailySnapshotsByDay(snapshots)
    expect(out).toHaveLength(1)
    expect(out[0]['Warren']).toBe(11000)
  })

  it('orders rows chronologically by day key', () => {
    const snapshots: PortfolioSnapshot[] = [
      {
        agentName: 'Warren',
        timestamp: '2025-03-17T10:00:00Z',
        totalValue: 12000,
        cashBalance: null,
        holdingsValue: null,
        totalPnl: null,
        totalReturnPercent: null,
      },
      {
        agentName: 'Warren',
        timestamp: '2025-03-15T10:00:00Z',
        totalValue: 10000,
        cashBalance: null,
        holdingsValue: null,
        totalPnl: null,
        totalReturnPercent: null,
      },
    ]

    const out = pivotLatestDailySnapshotsByDay(snapshots)
    expect(out).toHaveLength(2)
    expect(out[0]['Warren']).toBe(10000)
    expect(out[1]['Warren']).toBe(12000)
  })
})

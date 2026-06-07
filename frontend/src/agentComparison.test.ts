import { describe, it, expect } from 'vitest'
import { latestPerAgent } from './agentComparison'
import type { PortfolioSnapshot, Agent } from './types'

const baseSnap = (overrides: Partial<PortfolioSnapshot>): PortfolioSnapshot => ({
  agentName: 'Warren',
  timestamp: '2025-01-01T00:00:00Z',
  totalValue: 10000,
  cashBalance: 5000,
  holdingsValue: 5000,
  totalPnl: 0,
  totalReturnPercent: 0,
  ...overrides,
})

describe('latestPerAgent', () => {
  it('returns empty when no snapshots match a known agent', () => {
    expect(latestPerAgent([], [])).toEqual([])
  })

  it('keeps the most recent snapshot per agent', () => {
    const snapshots: PortfolioSnapshot[] = [
      baseSnap({ agentName: 'Warren', timestamp: '2025-01-01T00:00:00Z', totalValue: 1 }),
      baseSnap({ agentName: 'Warren', timestamp: '2025-01-02T00:00:00Z', totalValue: 2 }),
    ]
    const out = latestPerAgent(snapshots, [])
    expect(out).toHaveLength(1)
    expect(out[0].totalValue).toBe(2)
  })

  it('joins Agent metadata (id, style, systemPrompt) when names match', () => {
    const snapshots = [baseSnap({ agentName: 'Warren' })]
    const agents: Agent[] = [
      { id: 7, name: 'Warren', style: 'Value', systemPrompt: 'be Buffett' },
    ]
    const out = latestPerAgent(snapshots, agents)
    expect(out[0].id).toBe(7)
    expect(out[0].style).toBe('Value')
    expect(out[0].systemPrompt).toBe('be Buffett')
  })

  it('orders results by AGENT_ORDER (Warren, Ray, George, Cathie) and skips agents not in the snapshot list', () => {
    const snapshots: PortfolioSnapshot[] = [
      baseSnap({ agentName: 'Cathie' }),
      baseSnap({ agentName: 'Warren' }),
    ]
    const out = latestPerAgent(snapshots, [])
    expect(out.map((a) => a.name)).toEqual(['Warren', 'Cathie'])
  })

  it('returns id=null when no Agent metadata is supplied', () => {
    const snapshots = [baseSnap({ agentName: 'Warren' })]
    const out = latestPerAgent(snapshots, [])
    expect(out[0].id).toBeNull()
  })
})
